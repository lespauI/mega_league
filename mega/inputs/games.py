"""Shared Force Win eligibility, separate from official completion status."""


def flag(value):
    value = str(value).strip().lower()
    if value not in {"true", "false", "1", "0"}:
        raise ValueError(f"Invalid game flag: {value!r}")
    return value in {"true", "1"}


def is_force_win(game):
    return any([flag(game["home_fw"]), flag(game["away_fw"])])
