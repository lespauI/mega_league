import unittest

from scripts import power_rankings_roster as prr


class NormalizeUnitScoresTests(unittest.TestCase):
    def test_zscore_normalization_monotonic_and_bounded(self) -> None:
        raw = {"A": 10.0, "B": 20.0, "C": 30.0}

        normalized = prr.normalize_unit_scores(raw, method="zscore")

        self.assertGreater(normalized["C"], normalized["B"])
        self.assertGreater(normalized["B"], normalized["A"])

        for value in normalized.values():
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 100.0)

    def test_equal_values_yield_neutral_scores(self) -> None:
        raw = {"A": 42.0, "B": 42.0}

        zscore = prr.normalize_unit_scores(raw, method="zscore")
        minmax = prr.normalize_unit_scores(raw, method="minmax")

        for mapping in (zscore, minmax):
            self.assertAlmostEqual(mapping["A"], 50.0)
            self.assertAlmostEqual(mapping["B"], 50.0)


class ComputeOverallScoreTests(unittest.TestCase):
    def test_default_weights_respected(self) -> None:
        units = {
            "off_pass": 100.0,
            "off_run": 0.0,
            "def_coverage": 0.0,
            "pass_rush": 0.0,
        }

        score = prr.compute_overall_score(units)

        expected = 100.0 * prr.DEFAULT_OVERALL_UNIT_WEIGHTS["off_pass"]
        self.assertAlmostEqual(score, expected)

    def test_custom_weights_override_defaults(self) -> None:
        units = {
            "off_pass": 50.0,
            "off_run": 100.0,
            "def_coverage": 0.0,
            "pass_rush": 0.0,
        }
        weights = {"off_pass": 0.10, "off_run": 0.90}

        score = prr.compute_overall_score(units, weights=weights)

        expected = (50.0 * 0.10 + 100.0 * 0.90) / (0.10 + 0.90)
        self.assertAlmostEqual(score, expected)


class BuildTeamMetricsRankingTests(unittest.TestCase):
    def _make_roster(
        self,
        team_abbrev: str,
        team_name: str,
        base_ovr: int,
        dev: str,
    ) -> list[dict]:
        players: list[dict] = []

        def add_player(position: str, index: int) -> None:
            players.append(
                {
                    "team_abbrev": team_abbrev,
                    "team_name": team_name,
                    "player_id": f"{team_abbrev}_{position}_{index}",
                    "player_name": f"{team_abbrev} {position}{index}",
                    "position": position,
                    "ovr": base_ovr,
                    "dev": dev,
                }
            )

        # Offense core: QB, RB, FB, 2x WR, 2x TE, 5x OL
        add_player("QB", 1)
        add_player("HB", 1)
        add_player("FB", 1)
        add_player("WR", 1)
        add_player("WR", 2)
        add_player("TE", 1)
        add_player("TE", 2)
        for index, position in enumerate(["LT", "RT", "LG", "RG", "C"], start=1):
            add_player(position, index)

        # Defense core: edge, interior DL, LBs, DBs
        add_player("LE", 1)
        add_player("RE", 1)
        add_player("DT", 1)
        add_player("DT", 2)
        add_player("MLB", 1)
        add_player("LOLB", 1)
        add_player("ROLB", 1)
        add_player("CB", 1)
        add_player("CB", 2)
        add_player("CB", 3)
        add_player("FS", 1)
        add_player("SS", 1)

        return players

    def _make_teams_index(self) -> dict:
        teams = [
            {"abbrev": "AAA", "team_name": "Alpha"},
            {"abbrev": "BBB", "team_name": "Beta"},
        ]
        return prr.build_team_index(teams)

    def test_higher_ovr_team_ranks_above_lower_ovr_team(self) -> None:
        teams_index = self._make_teams_index()

        players: list[dict] = []
        players.extend(self._make_roster("AAA", "Alpha", base_ovr=90, dev="0"))
        players.extend(self._make_roster("BBB", "Beta", base_ovr=70, dev="0"))

        metrics = prr.build_team_metrics(players, teams_index, normalization="zscore")
        by_abbrev = {row["team_abbrev"]: row for row in metrics}

        alpha = by_abbrev["AAA"]
        beta = by_abbrev["BBB"]

        self.assertGreater(alpha["overall_score"], beta["overall_score"])
        self.assertEqual(alpha["overall_rank"], 1)
        self.assertEqual(beta["overall_rank"], 2)

        for unit_rank_key in (
            "off_pass_rank",
            "off_run_rank",
            "def_cover_rank",
            "def_pass_rush_rank",
            "def_run_rank",
        ):
            self.assertLess(alpha[unit_rank_key], beta[unit_rank_key])

    def test_premium_dev_team_outranks_same_ovr_normal_dev_team(self) -> None:
        teams_index = self._make_teams_index()

        players: list[dict] = []
        players.extend(self._make_roster("AAA", "Alpha", base_ovr=90, dev="3"))
        players.extend(self._make_roster("BBB", "Beta", base_ovr=90, dev="0"))

        metrics = prr.build_team_metrics(players, teams_index, normalization="zscore")
        by_abbrev = {row["team_abbrev"]: row for row in metrics}

        alpha = by_abbrev["AAA"]
        beta = by_abbrev["BBB"]

        self.assertGreater(alpha["overall_score"], beta["overall_score"])
        self.assertEqual(alpha["overall_rank"], 1)
        self.assertEqual(beta["overall_rank"], 2)


if __name__ == "__main__":  # pragma: no cover - manual test runner
    unittest.main()

