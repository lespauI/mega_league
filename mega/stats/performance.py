"""Rebuild performance inputs from a complete, snapshot-bound game evidence set.

Raw league results are never modified. Source-stat identities and captured team
history resolve trade duplicates before the Force Win eligibility rule is applied.
"""
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path

from mega.inputs.csv import load_csv
from mega.inputs.games import flag, is_force_win
from mega.inputs.evidence_bundle import evidence_source


COUNTS = {
    "passing": dict(zip(("passTotalAtt", "passTotalComp", "passTotalYds", "passTotalTDs", "passTotalInts", "passTotalSacks"),
                         ("passAtt", "passComp", "passYds", "passTDs", "passInts", "passSacks"))),
    "rushing": dict(zip(("rushTotalAtt", "rushTotalYds", "rushTotalTDs", "rushTotalBrokenTackles", "rushTotalFum", "rushTotal20PlusYds", "rushTotalYdsAfterContact"),
                         ("rushAtt", "rushYds", "rushTDs", "rushBrokenTackles", "rushFum", "rush20PlusYds", "rushYdsAfterContact"))),
    "receiving": dict(zip(("recTotalCatches", "recTotalDrops", "recTotalYds", "recTotalTDs", "recTotalYdsAfterCatch"),
                           ("recCatches", "recDrops", "recYds", "recTDs", "recYdsAfterCatch"))),
    "defense": dict(zip(("defTotalCatchAllowed", "defTotalDeflections", "defTotalForcedFum", "defTotalFumRec", "defTotalInts", "defTotalIntReturnYds", "defTotalSacks", "defTotalSafeties", "defTotalTDs", "defTotalTackles"),
                         ("defCatchAllowed", "defDeflections", "defForcedFum", "defFumRec", "defInts", "defIntReturnYds", "defSacks", "defSafeties", "defTDs", "defTotalTackles"))),
    "kicking": dict(zip(("fGTotalAtt", "fGTotal50PlusAtt", "fGTotal50PlusMade", "fGTotalMade", "kickoffTotalAtt", "kickoffTotalTBs", "xPTotalAtt", "xPTotalMade"),
                         ("fGAtt", "fG50PlusAtt", "fG50PlusMade", "fGMade", "kickoffAtt", "kickoffTBs", "xPAtt", "xPMade"))),
    "punting": dict(zip(("puntsTotalBlocked", "puntsTotalIn20", "puntTotalTBs", "puntTotalNetYds", "puntTotalAtt", "puntTotalYds"),
                         ("puntsBlocked", "puntsIn20", "puntTBs", "puntNetYds", "puntAtt", "puntYds"))),
}
MAXIMA = {"passing": {"passTotalLongest": "passLongest"}, "rushing": {"rushTotalLongest": "rushLongest"},
          "receiving": {"recTotalLongest": "recLongest"}, "kicking": {"fGTotalLongest": "fGLongest"},
          "punting": {"puntTotalLongest": "puntLongest"}}
RATES = {
    "passing": {"passAvgCompPct": ("passTotalComp", "passTotalAtt", 100),
                "passAvgYdsPerAtt": ("passTotalYds", "passTotalAtt", 1), "passAvgYdsPerGame": ("passTotalYds", "gamesPlayed", 1)},
    "rushing": {"rushAvgYdsPerAtt": ("rushTotalYds", "rushTotalAtt", 1), "rushAvgYdsPerGame": ("rushTotalYds", "gamesPlayed", 1),
                "rushAvgYdsAfterContact": ("rushTotalYdsAfterContact", "gamesPlayed", 1)},
    "receiving": {"recAvgYdsPerCatch": ("recTotalYds", "recTotalCatches", 1), "recAvgYacPerCatch": ("recTotalYdsAfterCatch", "recTotalCatches", 1),
                  "recAvgYdsPerGame": ("recTotalYds", "gamesPlayed", 1)},
    "kicking": {"fGAvgCompPct": ("fGTotalMade", "fGTotalAtt", 100), "xPAvgCompPct": ("xPTotalMade", "xPTotalAtt", 100)},
    "punting": {"puntAvgYdsPerAtt": ("puntTotalYds", "puntTotalAtt", 1), "puntAvgNetYdsPerAtt": ("puntTotalNetYds", "puntTotalAtt", 1)},
}
TEAM_YARDS = ("offPassYds", "offRushYds", "offTotalYds", "defPassYds", "defRushYds", "defTotalYds")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def numeric(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite game statistic")
    return result


def write_rows(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def aggregate(dataset, rows):
    result = {field: sum(numeric(r[source]) for r in rows) for field, source in COUNTS[dataset].items()}
    result.update({field: max((numeric(r[source]) for r in rows), default=0) for field, source in MAXIMA.get(dataset, {}).items()})
    result["gamesPlayed"] = len(rows)
    result["fantasy_points"] = sum(numeric(r["fantasy_points"]) for r in rows)
    for field, (n, d, scale) in RATES.get(dataset, {}).items():
        result[field] = result[n] / result[d] * scale if result[d] else 0
    if dataset == "receiving":
        denominator = result["recTotalCatches"] + result["recTotalDrops"]
        result["recAvgCatchPct"] = result["recTotalCatches"] / denominator * 100 if denominator else 0
    if dataset == "passing":
        att = result["passTotalAtt"]
        if att:
            components = [(result["passTotalComp"] / att - .3) * 5,
                          (result["passTotalYds"] / att - 3) * .25,
                          result["passTotalTDs"] / att * 20,
                          2.375 - result["passTotalInts"] / att * 25]
            result["passerAvgRating"] = sum(max(0, min(2.375, v)) for v in components) / 6 * 100
        else:
            result["passerAvgRating"] = 0
    return result


def history_team(source, player_id, week, teams, year):
    path = source / "histories" / f"{player_id}.json"
    data = json.loads(path.read_text())
    if data["sourceUrl"] != f"https://neonsportz.com/leagues/MEGA/players/{player_id}/history":
        raise ValueError("Wrong player-history source")
    snapshots = {}
    by_abbr = {r["abbrName"]: name for name, r in teams.items()}
    for table in data["tables"]:
        if table["headers"] != ["SEASON", "STAGE", "WEEK", "TEAM"]:
            continue
        for row in table["rows"]:
            cells = row["cells"]
            if cells[0] != str(year) or cells[1] != "Regular Season":
                continue
            links = [l["href"].rsplit("/", 1)[-1] for l in row["links"] if "/teams/" in l["href"]]
            if not links and cells[3] == 'FA':
                team = None
            elif len(links) == 1:
                team = by_abbr[links[0]]
            else:
                raise ValueError("Ambiguous historical team")
            index = int(cells[2].removeprefix("Week ")) - 1
            if index in snapshots and snapshots[index] != team:
                raise ValueError("Conflicting team-history snapshots")
            snapshots[index] = team
    if not snapshots:
        raise ValueError(f"No team history for duplicated player {player_id}")
    # The first observed team is the baseline before the first recorded change.
    chosen = max((w for w in snapshots if w <= week), default=min(snapshots))
    return snapshots[chosen]


def load_evidence(root, source, season_index):
    manifest = json.loads((source / "manifest.json").read_text())
    if manifest.get("schemaVersion") != 1 or manifest.get("csvSeasonIndex") != season_index:
        raise ValueError("Wrong performance evidence cycle")
    for name, expected in manifest["inputHashes"].items():
        if digest(root / name) != expected:
            raise ValueError(f"Performance evidence is stale for {name}; capture the new snapshot")
    if not manifest.get("evidenceHashes"):
        raise ValueError("Performance evidence inventory is empty")
    for name, expected in manifest["evidenceHashes"].items():
        if digest(source / name) != expected:
            raise ValueError(f"Performance evidence hash mismatch: {name}")
    games = {g["id"]: g for g in load_csv(root / "MEGA_games.csv")
             if g["seasonIndex"] == str(season_index) and g["stageIndex"] == "1" and not flag(g["is_superseded"])}
    teams = {t["displayName"]: t for t in load_csv(root / "MEGA_teams.csv") if t["seasonIndex"] == str(season_index)}
    captures, all_rows, categories = {}, {}, defaultdict(list)
    for game_id, game in games.items():
        if game["status"] not in {"2", "3", "4"}:
            continue
        relative = f"games/{game_id}.json"
        if relative not in manifest["evidenceHashes"]:
            raise ValueError(f"Missing completed-game evidence: {game_id}")
        capture = json.loads((source / relative).read_text())
        for name in ("homeScore", "awayScore", "weekIndex", "gameId", "stageIndex", "seasonIndex", "status"):
            if str(capture["game"][name]) != game[name]:
                raise ValueError(f"Stale captured {name}: {game_id}")
        if str(capture["game"]["pk"]) != game_id or capture["sourceUrl"] != f"https://neonsportz.com/leagues/MEGA/games/{game_id}":
            raise ValueError("Captured game identity differs")
        for name in ("home_fw", "away_fw", "is_superseded"):
            if flag(capture["game"][name]) != flag(game[name]):
                raise ValueError(f"Stale captured {name}: {game_id}")
        captures[game_id] = capture
        for side, obj in capture["sides"].items():
            if obj["team"] != game[side + "Team"]:
                raise ValueError("Captured game side differs")
            stat = obj["teamStats"]
            if str(stat["game"]) != game_id or int(stat["weekIndex"]) != int(game["weekIndex"]):
                raise ValueError("Team statistic belongs to another game")
            for row_id, row in obj["players"].items():
                if row_id in all_rows or str(row["game"]) != game_id or row["team"] != obj["team"]:
                    raise ValueError("Duplicate or incorrectly attributed player-stat row")
                if row.get("game_is_superseded") or int(row["seasonIndex"]) != season_index or row["stageIndex"] != 1:
                    raise ValueError("Player statistic is outside the active regular season")
                all_rows[row_id] = row
            for dataset in COUNTS:
                ids = obj["categories"][dataset]
                if len(ids) != len(set(ids)) or any(i not in obj["players"] for i in ids):
                    raise ValueError("Invalid player category inventory")
                for row_id in ids:
                    categories[dataset].append(row_id)
    return manifest, games, teams, captures, all_rows, categories


def resolve_stat_identities(rows, source, teams, manifest):
    grouped = defaultdict(list)
    for row_id, row in rows.items():
        grouped[(row["playerId"], row["statId"])].append(row_id)
    discarded, corrections = set(), []
    source_fields = set(v for mapping in COUNTS.values() for v in mapping.values())
    source_fields.update(v for mapping in MAXIMA.values() for v in mapping.values())
    for (player_id, stat_id), ids in grouped.items():
        if len(ids) == 1:
            continue
        sample = rows[ids[0]]
        if any(rows[i]["weekIndex"] != sample["weekIndex"] or any(rows[i].get(f) != sample.get(f) for f in source_fields) for i in ids):
            raise ValueError(f"Source-stat identity has conflicting values: {player_id}/{stat_id}")
        relative = f"histories/{player_id}.json"
        if relative not in manifest["evidenceHashes"]:
            raise ValueError(f"Missing historical-team evidence for {player_id}")
        team = history_team(source, player_id, sample["weekIndex"], teams, manifest["calendarYear"])
        retained = [i for i in ids if rows[i]["team"] == team]
        if len(retained) != 1:
            raise ValueError(f"Ambiguous original team for {player_id}/{stat_id}")
        for row_id in ids:
            if row_id != retained[0]:
                discarded.add(row_id)
                corrections.append({"playerId": player_id, "statId": stat_id,
                                    "retainedRow": retained[0], "retainedTeam": team,
                                    "discardedRow": row_id, "discardedTeam": rows[row_id]["team"],
                                    "weekIndex": sample["weekIndex"]})
    return discarded, corrections


def rank_teams(teams, games, captures, through_week):
    rows = []
    for name, raw in teams.items():
        row = dict(raw)
        for field in (*TEAM_YARDS, "totalWins", "totalLosses", "totalTies", "homeWins", "homeLosses", "homeTies",
                      "awayWins", "awayLosses", "awayTies", "ptsFor", "ptsAgainst", "netPts", "tODiff"):
            row[field] = 0
        included, excluded, streak = 0, 0, 0
        for g in sorted(games.values(), key=lambda g: int(g["weekIndex"])):
            if g["id"] not in captures or int(g["weekIndex"]) > through_week or name not in (g["homeTeam"], g["awayTeam"]):
                continue
            if is_force_win(g):
                excluded += 1
                continue
            side, other = ("home", "away") if name == g["homeTeam"] else ("away", "home")
            scored, allowed = int(g[side + "Score"]), int(g[other + "Score"])
            outcome = 1 if scored > allowed else -1 if scored < allowed else 0
            suffix = "Wins" if outcome == 1 else "Losses" if outcome == -1 else "Ties"
            row["total" + suffix] += 1
            row[side + suffix] += 1
            row["ptsFor"] += scored
            row["ptsAgainst"] += allowed
            stat = captures[g["id"]]["sides"][side]["teamStats"]
            for field in TEAM_YARDS:
                row[field] += numeric(stat[field])
            row["tODiff"] += numeric(stat["tODiff"])
            streak = streak + outcome if outcome and (streak * outcome > 0) else outcome
            included += 1
        row.update(performanceGames=included, excludedGames=excluded, winLossStreak=streak,
                   winPct=(row["totalWins"] + .5 * row["totalTies"]) / included if included else None,
                   netPts=row["ptsFor"] - row["ptsAgainst"],
                   performanceScope="Force Win games excluded; official standings are separate")
        rows.append(row)
    for field, descending in (("offPassYds", True), ("offRushYds", True), ("offTotalYds", True),
                              ("defPassYds", False), ("defRushYds", False), ("defTotalYds", False),
                              ("ptsFor", True), ("ptsAgainst", False)):
        eligible = [r for r in rows if r["performanceGames"]]
        values = sorted({r[field] / r["performanceGames"] for r in eligible}, reverse=descending)
        for r in rows:
            r[field + "Rank"] = values.index(r[field] / r["performanceGames"]) + 1 if r["performanceGames"] else None
    played = [r for r in rows if r["performanceGames"]]
    for field, sign in (("ptsFor", 1), ("ptsAgainst", -1)):
        vals = [r[field] / r["performanceGames"] for r in played]
        mean = sum(vals) / len(vals) if vals else 0
        sd = (sum((x - mean) ** 2 for x in vals) / len(vals)) ** .5 if vals else 0
        for r in rows:
            r[field + "Z"] = sign * ((r[field] / r["performanceGames"] - mean) / sd if sd else 0) if r["performanceGames"] else None
    scores = sorted({r["ptsForZ"] + r["ptsAgainstZ"] for r in played}, reverse=True)
    for r in rows:
        r["rank"] = scores.index(r["ptsForZ"] + r["ptsAgainstZ"]) + 1 if r["performanceGames"] else None
        # No exported historical rank may leak into analytical strength.
        r["prevRank"] = r["rank"]
    return rows


def build_performance(root, season_index=0):
    root = Path(root)
    source = evidence_source(root)
    manifest, games, teams, captures, player_rows, categories = load_evidence(root, source, season_index)
    discarded, corrections = resolve_stat_identities(player_rows, source, teams, manifest)
    source_notes = []
    for game_id, capture in captures.items():
        for side in capture['sides'].values():
            def total(dataset, field):
                return sum(numeric(player_rows[i][field]) for i in side['categories'][dataset] if i not in discarded)
            for label, player_total, reference in (
                ('player_rushing_vs_team_rushing', total('rushing', 'rushYds'), numeric(side['teamStats']['offRushYds'])),
                ('receiving_vs_player_passing', total('receiving', 'recYds'), total('passing', 'passYds')),
            ):
                if player_total != reference:
                    source_notes.append(dict(gameId=game_id, team=side['team'], comparison=label,
                                             playerTotal=player_total, referenceTotal=reference,
                                             treatment='preserve_independently_reconciled_source_totals'))
    # Team inputs have different yardage conventions from player inputs. Validate
    # each against its own source instead of scaling one to fit the other.
    for name, team in teams.items():
        for field in TEAM_YARDS:
            baseline = sum(numeric(side['teamStats'][field]) for game in captures.values()
                           for side in game['sides'].values() if side['team'] == name)
            if baseline != numeric(team[field]):
                raise ValueError(f'Team season yardage does not reconcile: {name}/{field}')
    result = root / "output" / "performance"
    inputs = root / ".cache" / "performance" / "inputs"
    unavailable = []
    for dataset in COUNTS:
        original = load_csv(root / f"MEGA_{dataset}.csv")
        naive, eligible = defaultdict(list), defaultdict(list)
        for row_id in categories[dataset]:
            r = player_rows[row_id]
            key = r["team"], r["playerId"]
            naive[key].append(r)
            if row_id not in discarded and not is_force_win(games[str(r["game"])]):
                eligible[key].append(r)
        if set(naive) != {(r["team__displayName"], r["player__rosterId"]) for r in original}:
            raise ValueError(f"Season player inventory does not reconcile: {dataset}")
        output = []
        for raw in original:
            key = raw["team__displayName"], raw["player__rosterId"]
            baseline = aggregate(dataset, naive[key])
            for field in [*COUNTS[dataset], *MAXIMA.get(dataset, {}), "gamesPlayed"]:
                if not math.isclose(baseline[field], numeric(raw[field]), abs_tol=.005, rel_tol=0):
                    raise ValueError(f"Season totals do not reconcile: {dataset}/{key}/{field}: {baseline[field]} != {raw[field]}")
            if not eligible[key]:
                continue
            adjusted = aggregate(dataset, eligible[key])
            row = {field: raw[field] if field.startswith(("team__", "player__")) else adjusted.get(field) for field in raw}
            for field in raw:
                if not field.startswith(("team__", "player__")) and field not in adjusted:
                    unavailable.append({"dataset": dataset, "team": key[0], "playerId": key[1], "field": field, "reason": "unsupported_source_field"})
            if dataset == "passing" and not math.isclose(baseline["passerAvgRating"], numeric(raw["passerAvgRating"]), abs_tol=.02):
                row["passerAvgRating"] = None
                unavailable.append({"dataset": dataset, "team": key[0], "playerId": key[1], "field": "passerAvgRating", "reason": "export_formula_does_not_reconcile"})
            output.append(row)
        write_rows(inputs / f"MEGA_{dataset}.csv", output, list(original[0]))
    max_week = max(int(g["weekIndex"]) for g in games.values() if g["id"] in captures)
    history, final = [], None
    for week in range(max_week + 1):
        final = rank_teams(teams, games, captures, week)
        for r in final:
            history.append({"team": r["displayName"], "seasonIndex": season_index, "stageIndex": 1, "weekIndex": week,
                            **{k: r[k] for k in ("rank", "prevRank", "ptsForRank", "ptsAgainstRank",
                                "offPassYdsRank", "offRushYdsRank", "offTotalYdsRank", "defPassYdsRank", "defRushYdsRank", "defTotalYdsRank")}})
    write_rows(inputs / "MEGA_teams.csv", final)
    write_rows(inputs / "MEGA_rankings.csv", history)
    # A browser-safe public performance view; the per-player input files stay internal.
    write_rows(result / "teams.csv", final)
    performance_games = [g for g in games.values() if not is_force_win(g)]
    write_rows(result / "games.csv", performance_games, list(next(iter(games.values()))))
    final_manifest = {"schemaVersion": 1, "complete": True, "csvSeasonIndex": season_index,
                      "policy": json.loads((root / "spec" / "performance_policy.json").read_text()),
                      "policyHash": digest(root / "spec" / "performance_policy.json"),
                      "evidenceManifestHash": digest(source / "manifest.json"),
                      "inputHashes": manifest["inputHashes"], "evidenceHashes": manifest["evidenceHashes"],
                      "completedGames": len(captures), "excludedGames": sum(is_force_win(games[i]) for i in captures),
                      "tradeCorrections": corrections, "unavailableFields": unavailable,
                      "sourceReconciliationNotes": source_notes,
                      "outputHashes": {p.relative_to(root).as_posix(): digest(p) for p in sorted([*inputs.glob("*.csv"), result / "teams.csv", result / "games.csv"])}}
    (result / "manifest.json").write_text(json.dumps(final_manifest, indent=2) + "\n")
    return final_manifest
