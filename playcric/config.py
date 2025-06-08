PLAYERS_URL = 'http://play-cricket.com/api/v2/sites/{site_id}/players?&api_token={api_key}'
MATCHES_URL = 'http://play-cricket.com/api/v2/matches.json?&site_id={site_id}&season={season}&api_token={api_key}'
LEAGUE_TABLE_URL = 'http://play-cricket.com/api/v2/league_table.json?division_id={competition_id}&api_token={api_key}'
MATCH_DETAIL_URL = 'http://play-cricket.com/api/v2/match_detail.json?&match_id={match_id}&api_token={api_key}'

NEUTRAL_RESULTS = ['C', 'A', 'D', 'CON', 'T']
RESULTS_SWAPPER = {'L': 'W', 'W': 'L'}
RESULTS_TEXT = {'C': 'Match Cancelled', 'A': 'Abandoned',
                'CON': 'Match conceded', 'D': 'Drew', 'L': 'Lost by', 'W': 'Won by', 'T': 'Tied'}

STANDARD_BATTING_COLS = ['position', 'batsman_name', 'batsman_id', 'how_out', 'fielder_name',
                         'fielder_id', 'bowler_name', 'bowler_id', 'runs', 'fours', 'sixes',
                         'balls', 'team_name', 'team_id', 'opposition_name', 'opposition_id', 'innings', 'match_id']
STANDARD_BOWLING_COLS = ['bowler_name', 'bowler_id', 'overs', 'maidens', 'runs', 'wides',
                         'wickets', 'no_balls', 'team_name', 'team_id', 'opposition_name', 'opposition_id', 'innings', 'match_id', 'balls']

N_TEAM_SWAP = ['st XI', 'nd XI', 'rd XI', 'th XI']
TEAM_NAME_BANNED_WORDS = [', Surrey', 'CC - ', ' XI',
                          'Saturday', 'Sunday', 'Sat', 'Sun', ' CC', ', Kent', '(Kent)']

NUMBER_OF_PLAYERS_STATS_ON_GRAPHICS = 3

# team_dict =
TEAM_NAME_TO_IDS_LOOKUP = {'1s': 59723, '2s': 59724, '3s': 241803,
                           '4s': 267647, '5s': 87177, 'Barbarians': 279276, 'Badgers': 268144, 'Honey Badgers': 368707, 'Friendly': 320697}
# , 'Sunday XI': 325401
TEAM_NAMES = ['Brixton Barbarians', 'Alleyn CC']

STATS_TOTALS_BATTING_COLUMNS = ['rank', 'batsman_name', 'match_id', 'runs']
STATS_TOTALS_BOWLING_COLUMNS = ['rank', 'bowler_name', 'overs', 'wickets']
STATS_TOTALS_FIELDING_COLUMNS = ['rank', 'fielder_name', 'dismissals']

INDIVIDUAL_PERFORMANCES_BATTING_COLUMNS = ['stat', 'title']
INDIVIDUAL_PERFORMANCES_BOWLING_COLUMNS = ['stat', 'title']

LEAGUE_TABLE_WIN_TYPES = ['TW', 'LOW', 'DLW', 'W', 'WT', 'W-', 'WCN']
LEAGUE_TABLE_DRAW_TYPES = ['WD', 'LD', 'ED']
LEAGUE_TABLE_LOSS_TYPES = ['L', 'LT', 'TL', 'LOL', 'DLL']

GROUPBY_AGGS = ['_sum', '_max', '_nunique', '_mean']
