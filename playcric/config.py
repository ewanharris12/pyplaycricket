"""
Generic configuration constants for the Play-Cricket API wrapper.

Club-specific constants (team IDs, banned words, etc.) live in alleyn_config.py.
"""

# --- API URL templates ---
PLAYERS_URL = 'http://play-cricket.com/api/v2/sites/{site_id}/players?&api_token={api_key}'
MATCHES_URL = 'http://play-cricket.com/api/v2/matches.json?&site_id={site_id}&season={season}&api_token={api_key}'
LEAGUE_TABLE_URL = 'http://play-cricket.com/api/v2/league_table.json?division_id={competition_id}&api_token={api_key}'
MATCH_DETAIL_URL = 'http://play-cricket.com/api/v2/match_detail.json?&match_id={match_id}&api_token={api_key}'

# --- Result codes ---
# Results that are not a win or loss and should not be swapped.
NEUTRAL_RESULTS = ['C', 'A', 'D', 'CON', 'T']
RESULTS_SWAPPER = {'L': 'W', 'W': 'L'}
RESULTS_TEXT = {
    'C': 'Match Cancelled', 'A': 'Abandoned',
    'CON': 'Match conceded', 'D': 'Drew',
    'L': 'Lost by', 'W': 'Won by', 'T': 'Tied',
}

# --- Expected DataFrame column sets ---
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

NUMBER_OF_PLAYERS_STATS_ON_GRAPHICS = 3

# --- Aggregation helpers ---
# Suffixes added by pandas groupby/agg that are stripped from column names.
GROUPBY_AGGS = ['_sum', '_max', '_nunique', '_mean']

# --- Stats display column selections ---
STATS_TOTALS_BATTING_COLUMNS = ['rank', 'batsman_name', 'match_id', 'runs']
STATS_TOTALS_BOWLING_COLUMNS = ['rank', 'bowler_name', 'overs', 'wickets']
STATS_TOTALS_FIELDING_COLUMNS = ['rank', 'fielder_name', 'dismissals']

INDIVIDUAL_PERFORMANCES_BATTING_COLUMNS = ['stat', 'title']
INDIVIDUAL_PERFORMANCES_BOWLING_COLUMNS = ['stat', 'title']

# --- League table column categories ---
LEAGUE_TABLE_WIN_TYPES = ['TW', 'LOW', 'DLW', 'W', 'WT', 'W-', 'WCN']
LEAGUE_TABLE_DRAW_TYPES = ['WD', 'LD', 'ED']
LEAGUE_TABLE_LOSS_TYPES = ['L', 'LT', 'TL', 'LOL', 'DLL']
