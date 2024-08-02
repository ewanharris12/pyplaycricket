import logging
import requests
import pandas as pd
import numpy as np
import math

from playcric import config
module_logger = logging.getLogger('pyplaycricket')


class u():
    def __init__(self):
        self.logger = logging.getLogger('pyplaycricket.utils')
        pass

    def _set_site_id(self, site_id):
        if site_id is None:
            site_id = self.site_id

        return site_id

    def _add_team_name_id_and_innings(self, df, team_name, team_id, opposition_name, opposition_id, innings_n, match_id):
        df['team_name'] = team_name
        df['team_id'] = team_id
        df['opposition_name'] = opposition_name
        df['opposition_id'] = opposition_id
        df['innings'] = innings_n
        df['match_id'] = match_id

        return df

    def _write_bowling_string(self, row):
        bowling_string = f'{row["wickets"]}-{row["runs"]}'
        return bowling_string

    def _write_batting_string(self, row):
        not_out = row['not_out'] == 1
        if not_out:
            no_string = '*'
        else:
            no_string = ''
        if row['balls'] > 0:
            run_string = f"{row['runs']}{no_string}({row['balls']})"
        else:
            run_string = f"{row['runs']}{no_string}"

        return run_string

    def _get_initials_surname(self, name):
        if not name.replace(' ', ''):
            return None
        name = name.split(' ')
        initials = ''.join([i[0] for i in name[:-1]])
        surname = name[-1]
        full_name = f'{initials} {surname}'
        return full_name

    def _standardise_bowl(self, bowl):
        if not bowl.empty:
            for col in ['runs', 'wickets', 'maidens', 'no_balls', 'wides']:
                bowl[col] = bowl[col].astype('int')
            bowl['initial_name'] = bowl['bowler_name'].apply(
                lambda x: self._get_initials_surname(x))
            bowl['balls'] = bowl['overs'].apply(
                lambda x: self._count_balls(x))
        else:
            self.logger.info('No bowling')
            bowl = pd.DataFrame(columns=config.STANDARD_BOWLING_COLS)
        return bowl

    def _standardise_bat(self, bat):
        if not bat.empty:
            bat['not_out'] = np.where(bat['how_out'].isin(
                ['not out', 'retired not out']), 1, 0)
            for col in ['runs', 'fours', 'sixes', 'balls', 'position']:
                bat[col] = bat[col].replace('', '0').astype('int')
            bat['initial_name'] = bat['batsman_name'].apply(
                lambda x: self._get_initials_surname(x))
        else:
            self.logger.info('No batting')
            bat = pd.DataFrame(columns=config.STANDARD_BATTING_COLS)
        return bat

    def _get_result_letter(self, data, team_ids):
        result_letter = data['result']
        applied_to = None
        if data['result_applied_to']:
            applied_to = float(data['result_applied_to'])
        if result_letter in config.NEUTRAL_RESULTS:
            return result_letter

        if applied_to not in team_ids:
            return config.RESULTS_SWAPPER.get(result_letter)
        return result_letter

    def _clean_league_table(self, df, simple, key):
        df.columns = [i.upper() for i in df.columns]
        wins = ['TW', 'LOW', 'DLW', 'W', 'WT', 'W-', 'WCN']
        draws = ['WD', 'LD', 'ED']
        losses = ['L', 'TL', 'LOL', 'DLL']

        if 'W - Total wins' in key:
            wins.remove('W')

        for col in wins+draws+losses:
            if col in df.columns:
                df[col] = df[col].astype('int')
            else:
                df[col] = 0
        if simple:
            # try:
            df['wins'] = df[wins].sum(
                axis=1).astype('int')
            df['draws'] = df[draws].sum(axis=1).astype('int')
            df['losses'] = df[losses].sum(
                axis=1).astype('int')

            # except Exception as e:
            #     print(f'Issue with WLD: {e}')
            #     df['wins'] = df[['W']].sum(axis=1).astype('int')
            #     # Likely to be a W/L league only so draws = 0
            #     df['draws'] = 0  # league_table[['WD','LD']].sum(axis=1)
            #     df['losses'] = df[['L']].sum(axis=1).astype('int')

            df = df[['POSITION', 'TEAM', 'wins', 'draws', 'losses', 'PTS']]
            df.rename(columns={'wins': 'W', 'draws': 'D',
                      'losses': 'L'}, inplace=True)
        return df

    def _make_api_request(self, url):
        self.logger.info(f'Making request to: {url}')
        req = requests.get(url)
        self.logger.info(f'Req response: {req.status_code}')
        if req.status_code != 200:
            raise Exception(f'ERROR ({req.status_code}): {req.reason}')

        return req.json()

    def _convert_team_ids_to_ints(self, team_ids):
        team_ids = [int(i) for i in team_ids]
        return team_ids

    def _count_balls(self, n):
        n = n.split('.')
        if len(n) == 0:
            return None
        if len(n) == 1:
            n += [0]
        for i in range(0, 2):
            if n[i] == '':
                n[i] = 0
            overs = int(n[0])
            if len(n) > 1:
                balls = int(n[1])
            else:
                balls = 0
            return (overs*6)+balls

    def _calculate_overs(self, n):
        o = math.floor(n/6)
        b = int(n - (o*6))

        return f'{o}.{b}'

    def _clean_team_name(self, team: str):
        if team.split(' - ')[0] in self.team_names:
            team = team.split(' - ')[0]
        else:
            for nth_team in config.N_TEAM_SWAP:
                team = team.replace(nth_team, 's')
            for banned_word in config.TEAM_NAME_BANNED_WORDS:
                team = team.replace(banned_word, '')
            team = team.replace('  ', ' ')
        return team

    def _calculate_batting_average(self, row):
        runs = row['runs']
        innings = row['innings_to_count']

        if innings == 0:
            return math.inf
        else:
            return runs/innings
