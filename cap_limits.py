"""
Standalone cap-limit-breach checker for Alleyn CC.

Finds players who have played enough games for higher teams (1s, 2s, 3s...)
that they are no longer eligible ("cup-tied") to play for a lower team, and
prints a message grouped by the lowest team each capped player can still
play for.

This file has no dependency on the `playcric` package - every helper it
needs is copied in below. It only depends on `requests`, `pandas`, and
`numpy`.
"""

import math
from datetime import datetime

import numpy as np
import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_KEY = "YOUR_API_KEY"
SITE_ID = 672
SEASON = 2026
CAP_LIMIT = 8

TEAM_NAME_TO_IDS_LOOKUP = {
    '1s': 59723, '2s': 59724, '3s': 241803,
    '4s': 267647, '5s': 394397, 'Barbarians': 279276,
    'Badgers': 268144, 'Honey Badgers': 368707, 'Friendly': 320697,
}
TEAM_IDS = list(TEAM_NAME_TO_IDS_LOOKUP.values())
TEAM_IDS_TO_NAMES_LOOKUP = {v: k for k, v in TEAM_NAME_TO_IDS_LOOKUP.items()}

MATCHES_URL = 'http://play-cricket.com/api/v2/matches.json?&site_id={site_id}&season={season}&api_token={api_key}'
MATCH_DETAIL_URL = 'http://play-cricket.com/api/v2/match_detail.json?&match_id={match_id}&api_token={api_key}'

NEUTRAL_RESULTS = ['C', 'A', 'D', 'CON', 'T']
RESULTS_SWAPPER = {'L': 'W', 'W': 'L'}

STANDARD_BATTING_COLS = [
    'position', 'batsman_name', 'batsman_id', 'how_out', 'fielder_name',
    'fielder_id', 'bowler_name', 'bowler_id', 'runs', 'fours', 'sixes',
    'balls', 'team_name', 'team_id', 'opposition_name', 'opposition_id',
    'innings', 'match_id',
]
STANDARD_BOWLING_COLS = [
    'bowler_name', 'bowler_id', 'overs', 'maidens', 'runs', 'wides',
    'wickets', 'no_balls', 'team_name', 'team_id', 'opposition_name',
    'opposition_id', 'innings', 'match_id', 'balls',
]

GROUPBY_AGGS = ['_sum', '_max', '_nunique', '_mean']


# ---------------------------------------------------------------------------
# Module-level aggregation helpers used in groupby calls.
# ---------------------------------------------------------------------------

def _count_five_fers(x):
    return (x >= 5).sum()


def _count_fifties(x):
    return x[(x >= 50) & (x < 100)].count()


def _count_hundreds(x):
    return x[x >= 100].count()


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def normalise_id(value):
    if value in (None, ''):
        return None
    return int(value)


def convert_team_ids_to_ints(team_ids):
    if team_ids is None:
        return []
    return [int(i) for i in team_ids]


def make_api_request(url):
    req = requests.get(url)
    if req.status_code != 200:
        raise Exception(f'ERROR ({req.status_code}): {req.reason}')
    return req.json()


def add_team_name_id_and_innings(
    df, team_name, team_id, opposition_name, opposition_id,
    innings_number, match_id,
):
    df['team_name'] = team_name
    df['team_id'] = team_id
    df['opposition_name'] = opposition_name
    df['opposition_id'] = opposition_id
    df['innings'] = innings_number
    df['match_id'] = match_id
    return df


def clean_column_names(x):
    if x[1] == '':
        return x[0]
    return x[0] + '_' + x[1]


def get_initials_surname(name):
    if not name.replace(' ', ''):
        return None
    parts = name.split(' ')
    if len(parts) == 1:
        return parts[0]
    initials = ''.join(p[0] for p in parts[:-1])
    return f'{initials} {parts[-1]}'


def count_balls(overs_string):
    parts = overs_string.split('.')
    if len(parts) == 0:
        return None
    if len(parts) == 1:
        parts += [0]

    overs = int(parts[0]) if parts[0] != '' else 0
    balls = int(parts[1]) if len(parts) > 1 and parts[1] != '' else 0
    return (overs * 6) + balls


def calculate_overs(ball_count):
    overs = math.floor(ball_count / 6)
    balls = int(ball_count - (overs * 6))
    return f'{overs}.{balls}'


def get_result_letter(data, team_ids):
    result_letter = data['result']
    applied_to = None
    if data['result_applied_to']:
        applied_to = float(data['result_applied_to'])
    if result_letter in NEUTRAL_RESULTS:
        return result_letter
    if applied_to not in team_ids:
        return RESULTS_SWAPPER.get(result_letter)
    return result_letter


def standardise_bat(bat):
    if not bat.empty:
        bat['not_out'] = np.where(
            bat['how_out'].isin(['not out', 'retired not out', 'did not bat']),
            1, 0,
        )
        for col in ['runs', 'fours', 'sixes', 'balls', 'position']:
            bat[col] = bat[col].replace('', '0').astype('int')
        bat['initial_name'] = bat['batsman_name'].apply(
            lambda x: get_initials_surname(x))
    else:
        bat = pd.DataFrame(columns=STANDARD_BATTING_COLS)
    return bat


def standardise_bowl(bowl):
    if not bowl.empty:
        for col in ['runs', 'wickets', 'maidens', 'no_balls', 'wides']:
            bowl[col] = bowl[col].astype('int')
        bowl['initial_name'] = bowl['bowler_name'].apply(
            lambda x: get_initials_surname(x))
        bowl['balls'] = bowl['overs'].apply(lambda x: count_balls(x))
    else:
        bowl = pd.DataFrame(columns=STANDARD_BOWLING_COLS)
    return bowl


def extract_match_team_context(data):
    home_id = normalise_id(data['home_team_id'])
    away_id = normalise_id(data['away_team_id'])
    all_ids = [home_id, away_id]
    team_name_lookup = {
        home_id: data['home_club_name'] + ' - ' + data['home_team_name'],
        away_id: data['away_club_name'] + ' - ' + data['away_team_name'],
    }
    return {'all_ids': all_ids, 'team_name_lookup': team_name_lookup}


# ---------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------

def get_all_matches(season, team_ids=None, competition_ids=None, competition_types=None):
    if team_ids is None:
        team_ids = []
    if competition_ids is None:
        competition_ids = []
    if competition_types is None:
        competition_types = []

    team_ids = convert_team_ids_to_ints(team_ids)
    data = make_api_request(
        MATCHES_URL.format(site_id=SITE_ID, season=season, api_key=API_KEY))

    df = pd.json_normalize(data['matches'])
    if df.empty:
        return pd.DataFrame()

    for col in ['last_updated', 'match_date']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format='%d/%m/%Y')
    for col in ['competition_id']:
        df[col] = df[col].replace('', np.nan).astype('float')
    for col in ['home_team_id', 'away_team_id']:
        if col in df.columns:
            df[col] = df[col].astype('int')

    if team_ids:
        df = df.loc[
            (df['home_team_id'].isin(team_ids)) |
            (df['away_team_id'].isin(team_ids))
        ]
    if competition_ids:
        df = df.loc[df['competition_id'].isin(competition_ids)]
    if competition_types:
        df = df.loc[df['competition_type'].isin(competition_types)]

    return df


def get_result_for_my_team(match_id, team_ids=None):
    team_ids = convert_team_ids_to_ints(team_ids)
    data = make_api_request(
        MATCH_DETAIL_URL.format(match_id=match_id, api_key=API_KEY))
    data = data['match_details'][0]
    return get_result_letter(data=data, team_ids=team_ids)


# ---------------------------------------------------------------------------
# Players involved
# ---------------------------------------------------------------------------

def get_players_used_in_match(match_id):
    data = make_api_request(
        MATCH_DETAIL_URL.format(match_id=match_id, api_key=API_KEY))
    detail = data['match_details'][0]

    home_t = pd.json_normalize(detail['players'][0]['home_team'])
    home_t['team_id'] = normalise_id(detail['home_team_id'])
    home_t['club_id'] = normalise_id(detail['home_club_id'])

    away_t = pd.json_normalize(detail['players'][1]['away_team'])
    away_t['team_id'] = normalise_id(detail['away_team_id'])
    away_t['club_id'] = normalise_id(detail['away_club_id'])

    teams = pd.concat([home_t, away_t]).reset_index(drop=True)
    teams['match_id'] = match_id
    return teams


def get_all_players_involved(match_ids, team_ids=None):
    if team_ids is None:
        team_ids = []

    players = []
    for match_id in match_ids:
        try:
            players.append(get_players_used_in_match(match_id=match_id))
        except Exception as e:
            print(f'Error occurred while fetching players for match {match_id}: {e}')

    if not players:
        raise ValueError('No player data could be retrieved for the provided match IDs.')
    players = pd.concat(players)

    if team_ids:
        players = players.loc[players['team_id'].isin(team_ids)]

    players = players.drop_duplicates(
        subset=['player_name', 'player_id', 'match_id'])
    players.reset_index(inplace=True, drop=True)
    return players


# ---------------------------------------------------------------------------
# Individual stats
# ---------------------------------------------------------------------------

def get_individual_stats(match_id, team_ids=None, stat_string=False):
    if team_ids is None:
        team_ids = []

    data = make_api_request(
        MATCH_DETAIL_URL.format(match_id=match_id, api_key=API_KEY))
    data = data['match_details'][0]
    ctx = extract_match_team_context(data)
    all_ids = ctx['all_ids']
    team_name_lookup = ctx['team_name_lookup']

    all_batting = []
    all_bowling = []

    innings_number = 1
    for innings in data['innings']:
        bat = pd.json_normalize(innings['bat'])
        if bat.empty:
            continue
        batting_id = normalise_id(innings['team_batting_id'])
        batting_name = innings['team_batting_name']
        bowling_id = all_ids[1] if batting_id == all_ids[0] else all_ids[0]
        bowling_name = team_name_lookup.get(bowling_id)

        bowl = pd.json_normalize(innings['bowl'])
        if bowl.empty:
            continue

        bowl = add_team_name_id_and_innings(
            bowl, bowling_name, bowling_id, batting_name, batting_id,
            innings_number, match_id,
        )
        bat = add_team_name_id_and_innings(
            bat, batting_name, batting_id, bowling_name, bowling_id,
            innings_number, match_id,
        )
        all_batting.append(bat)
        all_bowling.append(bowl)
        innings_number += 1

    if len(all_batting) == 0:
        return (
            pd.DataFrame(columns=STANDARD_BATTING_COLS),
            pd.DataFrame(columns=STANDARD_BOWLING_COLS),
        )

    all_batting = standardise_bat(pd.concat(all_batting))
    all_bowling = standardise_bowl(pd.concat(all_bowling))

    if team_ids:
        all_batting = all_batting.loc[all_batting['team_id'].isin(team_ids)]
        all_bowling = all_bowling.loc[all_bowling['team_id'].isin(team_ids)]

    return all_batting, all_bowling


def get_individual_stats_from_all_games(match_ids, team_ids=None, stat_string=False):
    if team_ids is None:
        team_ids = []

    batting_frames = []
    bowling_frames = []
    for match_id in match_ids:
        try:
            bat, bowl = get_individual_stats(match_id=match_id, stat_string=stat_string)
        except Exception as e:
            raise ValueError(f'MATCH ID {match_id} FAILED WITH: {e}')
        batting_frames.append(bat)
        bowling_frames.append(bowl)

    batting = pd.concat(batting_frames)
    bowling = pd.concat(bowling_frames)
    bowling['wickets'] = bowling['wickets'].fillna(0).astype('int')

    if team_ids:
        fielding = batting.loc[~batting['team_id'].isin(team_ids)].copy()
        batting = batting.loc[batting['team_id'].isin(team_ids)]
        bowling = bowling.loc[bowling['team_id'].isin(team_ids)]
    else:
        fielding = batting.copy()

    batting.sort_values(['runs', 'balls'], ascending=[False, True], inplace=True)
    bowling.sort_values(
        ['wickets', 'runs', 'balls'], ascending=[False, True, True], inplace=True)

    batting.reset_index(inplace=True, drop=True)
    fielding.reset_index(inplace=True, drop=True)
    bowling.reset_index(inplace=True, drop=True)

    return batting, bowling, fielding


# ---------------------------------------------------------------------------
# Season aggregates
# ---------------------------------------------------------------------------

def aggregate_fielding_stats(fielding, fielding_groupby):
    fielding = fielding.groupby(
        fielding_groupby, as_index=False,
    ).agg({'match_id': ['count', pd.Series.nunique]})
    fielding.columns = [clean_column_names(col) for col in fielding.columns]
    fielding.rename(
        columns={'match_id_count': 'dismissals', 'match_id_nunique': 'n_games'},
        inplace=True,
    )
    fielding.sort_values(
        ['dismissals', 'n_games'], ascending=[False, True], inplace=True)
    fielding.dropna(subset=['fielder_name'], inplace=True)
    fielding = fielding.loc[fielding['fielder_name'] != '']
    fielding = (
        fielding.reset_index(drop=True)
        .reset_index()
        .rename(columns={'index': 'rank'})
    )
    fielding['rank'] += 1
    return fielding


def aggregate_bowling_stats(bowling, bowling_groupby):
    bowling = bowling.groupby(bowling_groupby, as_index=False).agg(
        {
            'wickets': ['sum', 'max', _count_five_fers],
            'balls': 'sum',
            'maidens': 'sum',
            'runs': 'sum',
            'match_id': pd.Series.nunique,
        }
    )
    bowling.columns = [clean_column_names(col) for col in bowling.columns]
    bowling.rename(
        columns={
            'wickets_sum': 'wickets',
            'wickets_max': 'max_wickets',
            'wickets__count_five_fers': '5fers',
        },
        inplace=True,
    )
    for agg in GROUPBY_AGGS:
        bowling.columns = [col.replace(agg, '') for col in bowling.columns]

    bowling = (
        bowling.sort_values(
            ['wickets', 'runs', 'balls', 'match_id'],
            ascending=[False, True, True, True],
        )
        .reset_index(drop=True)
        .reset_index()
        .rename(columns={'index': 'rank'})
    )
    bowling['overs'] = bowling['balls'].apply(lambda x: calculate_overs(x))
    bowling['average'] = bowling['runs'] / bowling['wickets'].replace(0, pd.NA)
    bowling['sr'] = bowling['balls'] / bowling['wickets'].replace(0, pd.NA)
    bowling['econ'] = (bowling['runs'] / bowling['balls'].replace(0, pd.NA)) * 6
    bowling['rank'] += 1
    return bowling


def aggregate_batting_stats(batting, batting_groupby):
    batting = batting.loc[batting['how_out'] != 'did not bat']
    batting = batting.groupby(batting_groupby, as_index=False).agg(
        {
            'runs': ['sum', 'max', _count_fifties, _count_hundreds],
            'fours': 'sum',
            'sixes': 'sum',
            'balls': 'sum',
            'not_out': 'sum',
            'match_id': pd.Series.nunique,
            'position': 'mean',
        }
    )
    batting.columns = [clean_column_names(col) for col in batting.columns]
    batting.rename(
        columns={
            'runs_sum': 'runs',
            'runs_max': 'top_score',
            'runs__count_fifties': '50s',
            'runs__count_hundreds': '100s',
        },
        inplace=True,
    )
    for agg in GROUPBY_AGGS:
        batting.columns = [col.replace(agg, '') for col in batting.columns]

    batting['innings_to_count'] = batting['match_id'] - batting['not_out']
    batting['average'] = (
        batting['runs'] / batting['innings_to_count'].replace(0, pd.NA)
    )
    batting = (
        batting.sort_values(
            ['runs', 'average', 'balls', 'fours', 'sixes'],
            ascending=[False, False, True, False, False],
        )
        .reset_index(drop=True)
        .reset_index()
        .rename(columns={'index': 'rank'})
    )
    batting['rank'] += 1
    return batting


def aggregate_stats(group_by_team, batting, bowling, fielding):
    batting_groupby = ['initial_name', 'batsman_name', 'batsman_id']
    bowling_groupby = ['initial_name', 'bowler_name', 'bowler_id']
    fielding_groupby = ['fielder_name', 'fielder_id']
    if group_by_team:
        batting_groupby += ['team_id']
        bowling_groupby += ['team_id']
        fielding_groupby += ['team_id']

    batting = aggregate_batting_stats(batting, batting_groupby)
    bowling = aggregate_bowling_stats(bowling, bowling_groupby)
    fielding = aggregate_fielding_stats(fielding, fielding_groupby)
    return batting, bowling, fielding


def get_stat_totals(match_ids, team_ids=None, group_by_team=False):
    if team_ids is None:
        team_ids = []

    batting, bowling, fielding = get_individual_stats_from_all_games(
        match_ids, team_ids, stat_string=False)

    batting, bowling, fielding = aggregate_stats(
        group_by_team, batting, bowling, fielding)

    return batting, bowling, fielding


# ---------------------------------------------------------------------------
# Cap limits
# ---------------------------------------------------------------------------

def check_cap_limit_breaches(
    players_involved_by_team, agg_batting, agg_bowling, cap_limit=10,
):
    """
    Flag players who are cup-tied out of a lower team by appearances for
    higher teams, with their batting/bowling stats for the lowest team
    they're still available for attached for context.

    Only teams named with the "<n>s" convention ('1s', '2s', ...) participate
    in the hierarchy. A player is blocked from team n once their combined
    appearances for every team numbered below n reach cap_limit. Since that
    block is monotonic, each capped player gets a single row keyed on the
    first team they're blocked from.
    """
    team_levels = players_involved_by_team.copy()
    team_levels['team_level'] = team_levels['team_name'].str.extract(r'^(\d+)s$')
    team_levels.dropna(subset=['team_level'], inplace=True)
    team_levels['team_level'] = team_levels['team_level'].astype(int)

    team_id_by_level = (
        team_levels[['team_level', 'team_name']]
        .drop_duplicates()
        .assign(team_id=lambda df: df['team_name'].map(TEAM_NAME_TO_IDS_LOOKUP))
        .set_index('team_level')['team_id']
    )

    appearances = team_levels.pivot_table(
        index=['player_id', 'player_name'], columns='team_level',
        values='count', aggfunc='sum', fill_value=0,
    )

    levels = sorted(appearances.columns)
    cumulative = appearances[levels].cumsum(axis=1).shift(axis=1, fill_value=0)

    breaches = []
    for player_id, player_name in appearances.index:
        blocked_levels = [
            level for level in levels
            if level >= 2 and cumulative.loc[(player_id, player_name), level] >= cap_limit
        ]
        if not blocked_levels:
            continue

        first_blocked_level = min(blocked_levels)
        available_level = levels[levels.index(first_blocked_level) - 1]
        breaches.append({
            'player_id': player_id,
            'player_name': player_name,
            'blocked_team': f'{first_blocked_level}s',
            'lowest_available_team': f'{available_level}s',
            'available_team_id': team_id_by_level.get(available_level),
            'appearances_in_lowest_available_team':
                appearances.loc[(player_id, player_name), available_level],
            'cumulative_appearances': cumulative.loc[(player_id, player_name), first_blocked_level],
            'cap_limit': cap_limit,
        })

    breaches = pd.DataFrame(breaches)
    if breaches.empty:
        return breaches

    batting_cols = ['batsman_id', 'team_id', 'runs', 'average', 'top_score']
    bowling_cols = ['bowler_id', 'team_id', 'wickets', 'average', 'econ']
    breaches = breaches.merge(
        agg_batting[batting_cols].rename(columns={'batsman_id': 'player_id'}),
        how='left',
        left_on=['player_id', 'available_team_id'],
        right_on=['player_id', 'team_id'],
    ).drop(columns=['team_id'])
    breaches = breaches.merge(
        agg_bowling[bowling_cols].rename(columns={'bowler_id': 'player_id'}),
        how='left',
        left_on=['player_id', 'available_team_id'],
        right_on=['player_id', 'team_id'],
        suffixes=('_batting', '_bowling'),
    ).drop(columns=['team_id'])

    return breaches.sort_values(['player_name', 'blocked_team']).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    matches = get_all_matches(SEASON, team_ids=TEAM_IDS, competition_types=['League'])
    matches = matches.loc[matches['match_date'] < datetime.today()]

    matches['result'] = matches['id'].apply(lambda x: get_result_for_my_team(x))

    players_involved = get_all_players_involved(matches['id'].tolist(), team_ids=TEAM_IDS)

    batting_agg, bowling_agg, fielding = get_stat_totals(
        matches['id'].tolist(), team_ids=TEAM_IDS, group_by_team=True)

    players_involved['team_name'] = players_involved['team_id'].apply(
        lambda x: TEAM_IDS_TO_NAMES_LOOKUP[x])

    players_involved_by_team = (
        players_involved.groupby(['team_id', 'team_name', 'player_id', 'player_name'])
        .agg({'match_id': 'count'})
        .reset_index()
        .rename(columns={'match_id': 'count'})
        .sort_values(by=['team_id', 'count'], ascending=[True, False])
    )

    batting_agg['batsman_id'] = batting_agg['batsman_id'].astype(int)
    bowling_agg['bowler_id'] = bowling_agg['bowler_id'].astype(int)

    caps = check_cap_limit_breaches(
        players_involved_by_team, batting_agg, bowling_agg, cap_limit=CAP_LIMIT)

    caps_sorted = caps.sort_values('cumulative_appearances', ascending=False)

    lines = ['*Cap Limit Breaches*']
    for team in sorted(caps_sorted['lowest_available_team'].unique(), key=lambda t: int(t.rstrip('s'))):
        lines.append(f'\n*Limited to {team}*')
        team_rows = caps_sorted.loc[caps_sorted['lowest_available_team'] == team]
        for _, row in team_rows.iterrows():
            lines.append(f"{row['player_name']} - {row['cumulative_appearances']} apps")
    caps_message = '\n'.join(lines)

    print(caps_message)
    return caps_message


if __name__ == '__main__':
    main()
