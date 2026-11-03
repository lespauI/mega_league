"""Seeded NFL postseason simulation using the shared match model."""


def simulate_conference_champions(fields, probability, rng):
    """Return AFC and NFC champions (the two Super Bowl participants). Fields contain seeds 1–7 in each conference.

    Seeds 2/7, 3/6 and 4/5 play Wild Card. Each following conference
    round reseeds; the best remaining seed hosts the worst. The Super
    Bowl itself is not simulated. Only seed 1 receives a bye.
    """
    if set(fields) != {'AFC', 'NFC'}:
        raise ValueError('Both conferences are required')
    teams = [team for field in fields.values() for team in field]
    if any(len(field) != 7 for field in fields.values()) or len(set(teams)) != 14:
        raise ValueError('Expected seven distinct seeds per conference')

    def play(home, away, neutral=False):
        p = probability(home, away, neutral=neutral)
        return home if rng.random() < p else away

    champions = {}
    for conference in ('AFC', 'NFC'):
        field = fields[conference]
        seeds = {team: seed for seed, team in enumerate(field)}
        alive = [field[0]] + [play(field[a], field[b]) for a, b in ((1, 6), (2, 5), (3, 4))]
        while len(alive) > 1:
            alive.sort(key=seeds.__getitem__)
            alive = [play(alive[i], alive[-1-i]) for i in range(len(alive) // 2)]
        champions[conference] = alive[0]
    return champions


def superbowl_appearance_probabilities(teams, draw_field, probability, rng, simulations=10000):
    """Count conference champions: probabilities sum to 100% per conference."""
    if simulations <= 0:
        raise ValueError('simulations must be positive')
    wins = dict.fromkeys(teams, 0)
    for _ in range(simulations):
        for team in simulate_conference_champions(draw_field(), probability, rng).values():
            wins[team] += 1
    return {team: count * 100 / simulations for team, count in wins.items()}
