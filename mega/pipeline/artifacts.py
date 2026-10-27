"""Central registry for pipeline outputs and browser data paths."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


PROTECTED_OUTPUT_FILES = ("attributes.md", "individual_position_formulas.txt")

GENERATED_DOC_PAGES = frozenset({
    "docs/playoff_race.html",
    "docs/playoff_race_table.html",
    "docs/team_scenarios.html",
    "docs/power_rankings_roster.html",
    "docs/week18_simulator.html",
})

GENERATED_BROWSER_DATA = frozenset({
    "MEGA_teams.csv",
    "MEGA_users.csv",
    "mega_elo.csv",
    "current_elo.csv",
    "playoff_probabilities.json",
    "data_manifest.json",
})

# Producer ownership is deliberately explicit. The two season-dependent SoS
# exports and roster CSV family are added as patterns below.
TASK_OUTPUTS: dict[str, tuple[str, ...]] = {
    "stints": ("output/player_team_stints.csv",),
    "team_stats": ("output/team_aggregated_stats.csv",),
    "usage": ("output/team_player_usage.csv",),
    "rankings_stats": ("output/team_rankings_stats.csv",),
    "trade_verify": ("output/traded_players_report.csv",),
    "sos_elo": (
        "output/sos/season{season}_elo.csv",
        "output/sos/season{season}_elo.json",
        "output/schedules/season{season}/all_schedules.json",
    ),
    "sos_rankings": ("output/ranked_sos_by_conference.csv",),
    "scenarios": ("output/team_scenarios.json", "output/playoff_probabilities.json"),
    "playoff_table": ("docs/playoff_race_table.html",),
    "playoff_html": ("docs/playoff_race.html",),
    "scenario_html": ("docs/team_scenarios.html",),
    "week18_simulator": ("docs/week18_simulator.html",),
    "draft_race": ("output/draft_race/draft_race_report.md",),
    "roster_rankings": ("output/power_rankings_roster.csv", "docs/power_rankings_roster.html"),
    "publish_browser_data": (
        "docs/data/MEGA_teams.csv",
        "docs/data/MEGA_users.csv",
        "docs/data/mega_elo.csv",
        "docs/data/current_elo.csv",
        "docs/data/playoff_probabilities.json",
        "docs/data/season{season}_elo.csv",
        "docs/data/schedules_season{season}.json",
        "docs/data/ranked_sos_by_conference_season{season}.csv",
        "docs/data/data_manifest.json",
    ),
    "index": ("index.html",),
}


@dataclass(frozen=True)
class BrowserDataArtifact:
    """A browser data key and its repository source/published relative URL."""

    source_path: str
    url: str

    def resolved(self, display_season: int) -> tuple[str, str]:
        return (
            self.source_path.format(season=display_season),
            self.url.format(season=display_season),
        )


# URL strings are relative to docs/data/data_manifest.json. Files under the
# repository root or output/ are reached with ../../; copied browser files are
# siblings of the manifest.
BROWSER_DATA: dict[str, BrowserDataArtifact] = {
    "teams": BrowserDataArtifact("MEGA_teams.csv", "../../MEGA_teams.csv"),
    "players": BrowserDataArtifact("MEGA_players.csv", "../../MEGA_players.csv"),
    "games": BrowserDataArtifact("MEGA_games.csv", "../../MEGA_games.csv"),
    "team_stats": BrowserDataArtifact("output/team_aggregated_stats.csv", "../../output/team_aggregated_stats.csv"),
    "player_usage": BrowserDataArtifact("output/team_player_usage.csv", "../../output/team_player_usage.csv"),
    "rankings_stats": BrowserDataArtifact("output/team_rankings_stats.csv", "../../output/team_rankings_stats.csv"),
    "stints": BrowserDataArtifact("output/player_team_stints.csv", "../../output/player_team_stints.csv"),
    "trades": BrowserDataArtifact("output/traded_players_report.csv", "../../output/traded_players_report.csv"),
    "roster_rankings": BrowserDataArtifact("output/power_rankings_roster.csv", "../../output/power_rankings_roster.csv"),
    "rankings_sos": BrowserDataArtifact("output/ranked_sos_by_conference.csv", "../../output/ranked_sos_by_conference.csv"),
    "elo": BrowserDataArtifact("docs/data/current_elo.csv", "current_elo.csv"),
    "elo_sos": BrowserDataArtifact("docs/data/season{season}_elo.csv", "season{season}_elo.csv"),
    "schedules": BrowserDataArtifact("docs/data/schedules_season{season}.json", "schedules_season{season}.json"),
    "playoffs": BrowserDataArtifact("docs/data/playoff_probabilities.json", "playoff_probabilities.json"),
}

_DYNAMIC_OWNED_PATHS = (
    re.compile(r"output/sos/season\d+_elo\.(?:csv|json)\Z"),
    re.compile(r"output/schedules/season\d+/all_schedules\.json\Z"),
    re.compile(r"output/team_rosters/[^/]+\.csv\Z"),
    re.compile(r"docs/team_scenarios/[^/]+\.md\Z"),
    re.compile(r"docs/data/season\d+_elo\.csv\Z"),
    re.compile(r"docs/data/schedules_season\d+\.json\Z"),
    re.compile(r"docs/data/ranked_sos_by_conference_season\d+\.csv\Z"),
)

_EXPLICIT_OWNED_PATHS = frozenset({
    path
    for paths in TASK_OUTPUTS.values()
    for path in paths
    if "{season}" not in path
}) | frozenset({
    "output/build_manifest.json",
    "docs/data/build_manifest.json",
}) | frozenset(
    f"docs/data/{name}" for name in GENERATED_BROWSER_DATA
)


def task_output_paths(task_id: str, display_season: int) -> tuple[str, ...]:
    """Return concrete required outputs for one producer and display season."""
    return tuple(path.format(season=display_season) for path in TASK_OUTPUTS.get(task_id, ()))


def is_owned_artifact(relative: str | Path) -> bool:
    """Return true only for paths in the explicit generated artifact registry."""
    rel = Path(relative).as_posix()
    if rel in _EXPLICIT_OWNED_PATHS:
        return True
    return any(pattern.fullmatch(rel) for pattern in _DYNAMIC_OWNED_PATHS)


def clear_owned_artifacts(root: Path) -> None:
    """Remove generated site files from a staging copy, preserving maintained source."""
    root = Path(root)
    for relative in GENERATED_DOC_PAGES | {"index.html", "docs/data/build_manifest.json"}:
        path = root / relative
        if path.is_file():
            path.unlink()
    data_root = root / "docs" / "data"
    if data_root.is_dir():
        for path in data_root.iterdir():
            if path.is_file() and is_owned_artifact(path.relative_to(root)):
                path.unlink()
