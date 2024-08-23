# pyplaycricket
**pyplaycricket** is a package for extracting data programmatically from your playcricket site.

---

## Installation
**[fix link]**
Use the package manager [pip](https://pip.pypa.io/en/stable/) to install pyplaycricket.

```bash
pip install pyplaycricket
```

Or install via [Anaconda](https://docs.anaconda.com/free/anaconda/install/index.html).

```bash
conda install -c conda-forge pyplaycricket
```

---

## Access Requirements

To use the PlayCricket APIs you need to:
1. Email [play.cricket@ecb.co.uk](mailto:play.cricket@ecb.co.uk) to request access.
2. You will need to be a PlayCricket admin for your club's site.
3. You will need to share a fair usage agreement on behalf of your club.

They will confirm your site id and your API key.

---

## Library Structure

The library is split into 4 main modules. 3 are generic playcricket modules which can be used for interrogating playcricket data. The Alleyn module has been created for club specific requests.

- _playcricket_: generic methods for retrieving different data from playcricket sites.
- _utils_: internal methods called repeatedly by other modules.
- _alleyn_: specific methods for Alleyn CC analysis and social media posts.
- _config_: where URLs, team IDs and more are stored for use in playcricket, utils and alleyn.

---

## Quick start

Retrieve all playcricket matches in a given season for your club.

```python
from playcric.playcricket import pc
site_id = 'insert_your_site_id_here'
api_key = 'insert_your_api_key_here'

playc = pc(api_key=api_key, site_id=site_id)
matches = playc.get_all_matches(season=2024)
```

|    |      id | status   | published   | last_updated        | league_name                        | league_id   | competition_name      | competition_id   | competition_type   | match_type    | game_type   |   season | match_date          | match_time   | ground_name            |   ground_id |   ground_latitude |   ground_longitude | home_club_name     | home_team_name   |   home_team_id |   home_club_id | away_club_name   | away_team_name   |   away_team_id |   away_club_id | umpire_1_name   | umpire_1_id   | umpire_2_name   | umpire_2_id   | umpire_3_name   | umpire_3_id   | referee_name   | referee_id   | scorer_1_name   | scorer_1_id   | scorer_2_name   | scorer_2_id   |
|---:|--------:|:---------|:------------|:--------------------|:-----------------------------------|:------------|:----------------------|:-----------------|:-------------------|:--------------|:------------|---------:|:--------------------|:-------------|:-----------------------|------------:|------------------:|-------------------:|:-------------------|:-----------------|---------------:|---------------:|:-----------------|:-----------------|---------------:|---------------:|:----------------|:--------------|:----------------|:--------------|:----------------|:--------------|:---------------|:-------------|:----------------|:--------------|:----------------|:--------------|
|  0 | 6571330 | New      | Yes         | 2024-04-19 00:00:00 |                                    |             |                       |                  | Friendly           | Limited Overs | Standard    |     2024 | 2024-04-27 00:00:00 | 10:00        | Edward Alleyn Club     |        9352 |           51.4491 |         -0.0915547 | Alleyn CC          | Friendly XI      |         320697 |            672 | Alleyn CC        | Burbage Badgers  |         268144 |            672 |                 |               |                 |               |                 |               |                |              |                 |               |                 |               |
|  1 | 6242035 | New      | Yes         | 2024-07-31 00:00:00 | Surrey Junior Cricket Championship | 10881       | U11 Surrey County Cup | 63219            | Cup                | Limited Overs | Standard    |     2024 | 2024-05-05 00:00:00 | 09:00        | Battersea Park         |       56639 |           51.4802 |         -0.155702  | Spencer CC, Surrey | BU11 Tier1A      |         256417 |           5853 | Alleyn CC        | Under 11         |          90654 |            672 |                 |               |                 |               |                 |               |                |              |                 |               |                 |               |
|  2 | 6242558 | New      | Yes         | 2024-07-31 00:00:00 | Surrey Junior Cricket Championship | 10881       | U14 Surrey County Cup | 63217            | Cup                | Limited Overs | Standard    |     2024 | 2024-05-05 00:00:00 | 09:30        | Morden Park Main Pitch |       57159 |           51.3888 |         -0.210369  | AJ Cricket Academy | Under 14         |         257934 |          14870 | Alleyn CC        | Under 14         |          59853 |            672 |                 |               |                 |               |                 |               |                |              |                 |               |                 |               |

Retrieve a league table
```python
from playcric.playcricket import pc
site_id = 'insert_your_site_id_here'
api_key = 'insert_your_api_key_here'

playc = pc(api_key=api_key, site_id=site_id)
league_table, key = playc.get_league_table(117611, simple=True, clean_names=False)
```
|    |   POSITION | TEAM                   |   W |   D |   L |   PTS |
|---:|-----------:|:-----------------------|----:|----:|----:|------:|
|  0 |          1 | Horley CC, Surrey      |   8 |   2 |   1 |   219 |
|  1 |          2 | Alleyn CC              |   8 |   2 |   2 |   198 |
|  2 |          3 | Egham CC               |   6 |   1 |   4 |   170 |
|  3 |          4 | Cobham Avorians CC     |   6 |   1 |   5 |   166 |
|  4 |          5 | Byfleet CC             |   6 |   0 |   6 |   158 |
|  5 |          6 | Kingstonian CC, Surrey |   6 |   1 |   6 |   149 |
|  6 |          7 | Thames Ditton CC       |   5 |   1 |   4 |   147 |
|  7 |          8 | Effingham CC           |   4 |   2 |   5 |   118 |
|  8 |          9 | Old Pauline CC         |   4 |   0 |   8 |   111 |
|  9 |         10 | Churt and Hindhead CC  |   2 |   0 |  10 |    79 |

---

## What are the different IDs used in the different functions?
Most of the IDs required for filtering on leagues, competitions, teams, clubs etc can be gleaned from the get_all_matches function. By default, this will return the matches associated with your site.

If you want to return all the fixtures for another club, you will need to find this on their playcricket site, at the bottom of the home page.

## What is pyplaycricket?
In pyplaycricket, you can:

- list all registered players for a club
- get all matches for a club
- get a league table in dataframe form
- get all players involved in a fixture
- get all partnerships from a fixture
- get all individual stats from a fixture
- get all individual stats totalled over a season

I hope pyplaycricket makes it easier to return data from playcricket for a variety of different use cases.

## License

[MIT](https://choosealicense.com/licenses/mit)