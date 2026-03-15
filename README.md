# pyplaycricket

**pyplaycricket** is a Python package for extracting and analyzing data programmatically from [Play-Cricket](https://play-cricket.com) sites.

---

## Table of Contents

- [Installation](#installation)
- [Access Requirements](#access-requirements)
- [Library Structure](#library-structure)
- [Quick Start](#quick-start)
- [API Reference — `pc`](#api-reference--pc)
  - [Initialization](#initialisation)
  - [list_registered_players](#list_registered_players)
  - [get_all_matches](#get_all_matches)
  - [get_league_table](#get_league_table)
  - [get_match_result_string](#get_match_result_string)
  - [get_result_for_my_team](#get_result_for_my_team)
  - [get_all_players_involved](#get_all_players_involved)
  - [get_innings_total_scores](#get_innings_total_scores)
  - [get_match_partnerships](#get_match_partnerships)
  - [get_individual_stats](#get_individual_stats)
  - [get_individual_stats_from_all_games](#get_individual_stats_from_all_games)
  - [get_stat_totals](#get_stat_totals)
- [Alleyn CC Subclass — `acc`](#alleyn-cc-subclass--acc)
- [Finding IDs](#finding-ids)
- [License](#license)

---

## Installation

```bash
pip install pyplaycricket
```

---

## Access Requirements

The Play-Cricket API requires explicit approval before use.

1. Email [play.cricket@ecb.co.uk](mailto:play.cricket@ecb.co.uk) to request access.
2. You must be a Play-Cricket admin for your club's site.
3. You will be asked to sign a fair-usage agreement on behalf of your club.

Once approved, you will receive your **site ID** and **API key**.

---

## Library Structure

| Module | Purpose |
|---|---|
| `playcric.playcricket` | Main public API class (`pc`). All generic data-retrieval methods live here. |
| `playcric.utils` | Base class (`u`). Private helper methods shared across the class hierarchy. |
| `playcric.alleyn` | Alleyn CC-specific subclass (`acc`). Formatting methods for the club's graphics pipeline. |
| `playcric.config` | Generic API constants: URL templates, result codes, column schemas. |
| `playcric.alleyn_config` | Alleyn CC-specific constants: team IDs, name-cleaning rules. |

The class hierarchy is `u → pc → acc`. External users should instantiate `pc` (or `acc` for Alleyn CC-specific features).

---

## Quick Start

```python
from playcric.playcricket import pc

playc = pc(api_key='your_api_key', site_id=your_site_id)

# All matches for the 2024 season
matches = playc.get_all_matches(season=2024)

# Only your club's first team matches
matches = playc.get_all_matches(season=2024, team_ids=[59723])

# League table for a specific division
table, key = playc.get_league_table(competition_id=117611, simple=True)
```

---

## API Reference — `pc`

### Initialization

```python
from playcric.playcricket import pc

playc = pc(
    api_key='your_api_key',          # Play-Cricket API token (required)
    site_id=12345,                    # Your club's site ID (required)
    team_names=['My CC'],             # Human-readable club name(s), used for name cleaning
    team_name_to_ids_lookup={         # Maps team names to Play-Cricket team IDs
        '1s': 59723,
        '2s': 59724,
    },
)
```

`team_names` and `team_name_to_ids_lookup` are optional but enable filtering and name-cleaning features across several methods.

---

### list_registered_players

Return all players registered at a site.

```python
players = playc.list_registered_players()
# or for a different site:
players = playc.list_registered_players(site_id=99999)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `site_id` | int | `None` | Site to query. Falls back to the instance's `site_id` if omitted. |

**Returns:** `pd.DataFrame` — one row per registered player.

---

### get_all_matches

Return all matches for a season, with optional filters.

```python
# All matches for the site in 2024
matches = playc.get_all_matches(season=2024)

# Only matches involving specific teams
matches = playc.get_all_matches(season=2024, team_ids=[59723, 59724])

# Only league matches for specific competitions
matches = playc.get_all_matches(
    season=2024,
    competition_ids=[117611],
    competition_types=['League'],
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `season` | int | required | Season year to fetch. |
| `team_ids` | list | `None` | Restrict to matches involving these Play-Cricket team IDs. |
| `competition_ids` | list | `None` | Restrict to matches in these competition IDs. |
| `competition_types` | list | `None` | Restrict to matches of these types (e.g. `['League']`, `['Cup']`). |
| `site_id` | int | `None` | Site to query. Falls back to the instance's `site_id`. |

**Returns:** `pd.DataFrame` — one row per match. Includes `match_id`, `home_team_id`, `away_team_id`, `match_date`, `competition_type`, and more.

**Example output:**

| | match_id | home_team_name | away_team_name | match_date | competition_type |
|---|---|---|---|---|---|
| 0 | 6571330 | Alleyn CC 1s | Effingham CC 1s | 2024-08-03 | League |
| 1 | 6242035 | Alleyn CC 2s | Streatham CC | 2024-08-10 | League |

---

### get_league_table

Return the league table for a division.

```python
table, key = playc.get_league_table(competition_id=117611, simple=True)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `competition_id` | int | required | Play-Cricket division/competition ID. |
| `simple` | bool | `False` | If `True`, collapse all win/draw/loss variants into single W, D, L columns. |
| `clean_names` | bool | `True` | Strip club suffixes from team names. |

**Returns:** `tuple[pd.DataFrame, list]` — the league table DataFrame and a list describing the column headings.

**Example output (`simple=True`):**

| | POSITION | TEAM | W | D | L | PTS |
|---|---|---|---|---|---|---|
| 0 | 1 | Horley CC | 8 | 2 | 1 | 219 |
| 1 | 2 | Alleyn CC | 8 | 2 | 2 | 198 |
| 2 | 3 | Egham CC | 6 | 1 | 4 | 170 |

---

### get_match_result_string

Return the raw result description text for a match.

```python
result = playc.get_match_result_string(match_id=6178722)
# e.g. "Alleyn CC - 1st XI - Won: time+toss+bowl"
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `match_id` | int | required | Play-Cricket match ID. |

**Returns:** `str`

---

### get_result_for_my_team

Return the result code (`W`, `L`, `D`, etc.) from the perspective of specified teams.

```python
result = playc.get_result_for_my_team(match_id=6178722, team_ids=[59723])
# 'W', 'L', 'D', 'T', 'A', 'C', or 'CON'
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `match_id` | int | required | Play-Cricket match ID. |
| `team_ids` | list | `None` | IDs of the teams to treat as "our" teams. |

**Returns:** `str` — one of `W` (won), `L` (lost), `D` (draw), `T` (tie), `A` (abandoned), `C` (cancelled), `CON` (conceded).

---

### get_all_players_involved

Return deduplicated player records across one or more matches.

```python
players = playc.get_all_players_involved(
    match_ids=[6178722, 6178723],
    team_ids=[59723],   # optional: restrict to one team
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `match_ids` | list | required | Match IDs to query. |
| `team_ids` | list | `None` | If provided, restrict to players from these teams. |

**Returns:** `pd.DataFrame` — one row per unique player–match combination, with `player_id`, `player_name`, `team_id`, `club_id`, and `match_id`.

---

### get_innings_total_scores

Return innings-level totals (runs, wickets, overs, etc.) for a match.

```python
innings = playc.get_innings_total_scores(match_id=6178722)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `match_id` | int | required | Play-Cricket match ID. |

**Returns:** `pd.DataFrame` — one row per innings.

**Example output:**

| | innings_number | team_batting_name | runs | wickets | overs |
|---|---|---|---|---|---|
| 0 | 1 | Effingham CC - 1st XI | 136 | 10 | 50.5 |
| 1 | 2 | Alleyn CC - 1st XI | 137 | 6 | 41.2 |

---

### get_match_partnerships

Return fall-of-wicket and partnership data for each innings of a match.

```python
partnerships = playc.get_match_partnerships(match_id=6178722)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `match_id` | int | required | Play-Cricket match ID. |

**Returns:** `pd.DataFrame` — one row per wicket, including `runs` at dismissal, `score_added` (runs added since the previous wicket, computed per-innings), `batsman_out_name`, `innings`, `team_name`, and `opposition_name`.

---

### get_individual_stats

Return batting and bowling DataFrames for a single match.

```python
batting, bowling = playc.get_individual_stats(
    match_id=6178722,
    team_ids=[59723],       # optional: restrict to one team
    stat_string=True,       # optional: add formatted 'stat' column
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `match_id` | int | required | Play-Cricket match ID. |
| `team_ids` | list | `None` | If provided, restrict to these teams' batting/bowling records. |
| `stat_string` | bool | `False` | If `True`, adds a `stat` column: `"45*(62)"` for batting, `"3-42"` for bowling. |

**Returns:** `tuple[pd.DataFrame, pd.DataFrame]` — `(batting, bowling)`.

**Batting columns:** `position`, `batsman_name`, `batsman_id`, `how_out`, `fielder_name`, `fielder_id`, `bowler_name`, `bowler_id`, `runs`, `fours`, `sixes`, `balls`, `team_name`, `team_id`, `opposition_name`, `opposition_id`, `innings`, `match_id`, `not_out`, `initial_name`.

**Bowling columns:** `bowler_name`, `bowler_id`, `overs`, `maidens`, `runs`, `wides`, `wickets`, `no_balls`, `team_name`, `team_id`, `opposition_name`, `opposition_id`, `innings`, `match_id`, `balls`, `initial_name`.

---

### get_individual_stats_from_all_games

Collect per-match batting, bowling, and fielding records across multiple matches.

```python
batting, bowling, fielding = playc.get_individual_stats_from_all_games(
    match_ids=[6178722, 6178723, 6178724],
    team_ids=[59723],
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `match_ids` | list | required | Match IDs to include. |
| `team_ids` | list | `None` | If provided, batting/bowling are filtered to these teams; fielding is filtered to the opposition (to capture catches/run-outs taken by your fielders). |
| `stat_string` | bool | `False` | Passed through to `get_individual_stats`. |

**Returns:** `tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]` — `(batting, bowling, fielding)`. Each row is one innings performance by one player.

---

### get_stat_totals

Return aggregated season totals for batting, bowling, and fielding across a set of matches.

```python
batting, bowling, fielding = playc.get_stat_totals(
    match_ids=[6178722, 6178723, 6178724],
    team_ids=[59723],
    group_by_team=False,   # set True to see stats split by team
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `match_ids` | list | required | Match IDs to aggregate over. |
| `team_ids` | list | `None` | Teams to include. |
| `group_by_team` | bool | `False` | If `True`, break stats down by team in addition to player. |
| `for_graphics` | bool | `False` | If `True`, truncate to `n_players` and serialize each DataFrame to a newline-delimited string. |
| `n_players` | int | `10` | Player count limit when `for_graphics=True`. |

**Returns:** `tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]` — aggregated `(batting, bowling, fielding)`.

**Batting aggregate columns:** `rank`, `batsman_name`, `runs`, `top_score`, `50s`, `100s`, `average`, `fours`, `sixes`, `balls`, `match_id`, `not_out`, `innings_to_count`.

**Bowling aggregate columns:** `rank`, `bowler_name`, `wickets`, `max_wickets`, `5fers`, `overs`, `maidens`, `runs`, `average`, `sr`, `econ`, `match_id`.

**Fielding aggregate columns:** `rank`, `fielder_name`, `dismissals`, `n_games`.

**Example output (batting):**

| rank | batsman_name | match_id | runs | top_score | average |
|---|---|---|---|---|---|
| 1 | M Ogden | 12 | 487 | 89 | 44.3 |
| 2 | T Eadon | 12 | 421 | 72 | 38.3 |
| 3 | E Harris | 11 | 389 | 68 | 35.4 |

---

## Alleyn CC Subclass — `acc`

The `acc` class extends `pc` with display and formatting methods for Alleyn CC's social media and graphics pipeline. It pre-loads Alleyn-specific team IDs and name-cleaning rules from `alleyn_config`.

```python
from playcric.alleyn import acc

alleyn = acc(api_key='your_api_key', site_id=your_site_id)
```

`acc` inherits all `pc` methods and adds the following:

| Method | Returns | Description |
|---|---|---|
| `get_innings_scores(match_ids)` | `tuple[str, str]` | Newline-joined team names and score strings (e.g. `"Alleyn CC\nEffingham CC"`, `"137-6\n136"`) |
| `get_result_description_and_margin(match_ids, team_ids)` | `str` | Human-readable result lines (e.g. `"1s Won by 47 runs\n"`) |
| `get_individual_performances_for_graphic(match_ids, players_to_include)` | `str` | Fixed-width newline-delimited top batting and bowling performances per innings |
| `get_best_individual_performances(match_ids, team_ids, n_players, for_graphics)` | `tuple` | Top batting and bowling performances, optionally serialized for graphics |
| `get_weekend_matches(matches, saturday)` | `pd.DataFrame` | Filter a matches DataFrame to a specific weekend |
| `get_season_opposition_list(matches)` | `str` | Newline-joined opposition team names for the season |
| `get_cutout_off_league_table(league_table, n_teams)` | `str` | Fixed-width table slice centered on the club |
| `get_alleyn_season_totals(match_ids, ...)` | `tuple` | Wrapper around `get_stat_totals` defaulting `team_ids` to Alleyn's registered teams |
| `get_all_team_players_involved(match_ids, team_ids)` | `pd.DataFrame` | Wrapper around `get_all_players_involved` defaulting to Alleyn's teams |

---

## Finding IDs

Most IDs can be found from the output of `get_all_matches`. The key columns are:

| Column | Description |
|---|---|
| `match_id` | Unique ID for a specific fixture |
| `home_team_id` / `away_team_id` | Play-Cricket team IDs (use these for `team_ids` filters) |
| `home_club_id` / `away_club_id` | Club-level IDs |
| `competition_id` | Division/cup competition ID (use for `get_league_table`) |
| `competition_type` | String type, e.g. `"League"`, `"Cup"`, `"Friendly"` |

To find the IDs for a club you don't administer, look at the bottom of their Play-Cricket site home page — the site ID is shown there.

---

## License

[MIT](https://choosealicense.com/licenses/mit)
