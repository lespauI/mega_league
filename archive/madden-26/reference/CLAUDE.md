# Agent Rules

## Game Data

Per-game player statistics (box scores) are NOT available in the CSV exports. The CSVs (`MEGA_passing.csv`, `MEGA_rushing.csv`, etc.) contain **season totals only**.

To get per-game player stats (passing, rushing, receiving, defense, kicking for a specific game):

1. Find the game `id` (not `gameId`) from `MEGA_games.csv`
2. Navigate to `https://neonsportz.com/leagues/MEGA/games/{id}`
3. Click the **Player** tab to get individual box score data
4. **Do NOT use the Team Statistics tab** — it often has empty/NaN values and is unreliable

The `gameId` field in the CSV is a different internal ID and does not work for the URL — always use the `id` field.

## Analytics Style (Russian)

- Football terms are NOT translated, they are transliterated: pocket = покет, coverage = каверадж, air raid = эйр рейд, pass rush = пас раш, bye week = бай-уик
- Player names are transliterated to Russian (e.g. Cameron Yancey = Кэмерон Йенси)
- Team names in Russian (Cowboys = Ковбои, Commanders = Коммандерс, etc.)
- Coach name mappings: Les Paul = Костя, Артём Варнава = Варнава, Иван VakiVak = Ваня, Дана Малинка = Даня, Слава = Славик, Валера Хвост = Валера, Артур ArtSt = АкадемикХ, Семен = Семён, Иван Paris = Иван
- Style: casual, narrative, flowing prose with connected sentences — not choppy bullet points
- Analytics stored in `docs/data/analytics.json`, keyed by matchup ID (e.g. `afc_wc_1`, `nfc_div_1`)
