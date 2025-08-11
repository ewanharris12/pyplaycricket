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
        """
        Adds team name, team id, opposition name, opposition id, innings number, and match id to the given DataFrame.

        Parameters:
        - df: The DataFrame to which the information will be added.
        - team_name: The name of the team.
        - team_id: The ID of the team.
        - opposition_name: The name of the opposition team.
        - opposition_id: The ID of the opposition team.
        - innings_n: The number of the innings.
        - match_id: The ID of the match.

        Returns:
        - The modified DataFrame with the added information.
        """
        df['team_name'] = team_name
        df['team_id'] = team_id
        df['opposition_name'] = opposition_name
        df['opposition_id'] = opposition_id
        df['innings'] = innings_n
        df['match_id'] = match_id

        return df

    def _write_bowling_string(self, row):
        """
        Generates a bowling string based on the number of wickets and runs.

        Parameters:
        - row: A dictionary containing the number of wickets and runs.

        Returns:
        - bowling_string: A string representing the bowling figures in the format "wickets-runs".
        """
        bowling_string = f'{row["wickets"]}-{row["runs"]}'
        return bowling_string

    def _write_batting_string(self, row):
        """
        Generates a string representation of a batting score.

        Args:
            row (dict): A dictionary containing the batting score information.

        Returns:
            str: The string representation of the batting score.

        """
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
        """
        Get the initials and surname from a given name.

        Args:
            name (str): The name from which to extract the initials and surname.

        Returns:
            str: The full name consisting of the initials and surname.
        """
        if not name.replace(' ', ''):
            return None
        name = name.split(' ')
        initials = ''.join([i[0] for i in name[:-1]])
        if len(name) == 1:
            return name[0]
        else:
            surname = name[-1]
            full_name = f'{initials} {surname}'
            return full_name

    def _standardise_bowl(self, bowl):
        """
        Standardizes the bowling data in the given DataFrame.

        Args:
            bowl (DataFrame): The DataFrame containing the bowling data.

        Returns:
            DataFrame: The standardized bowling data.

        Raises:
            None

        """
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
        # bowl['bowler_id'] = bowl['bowler_id'].astype('int')
        return bowl

    def _standardise_bat(self, bat):
        """
        Standardizes the batting data by performing the following operations:
        1. Sets the 'not_out' column to 1 if the 'how_out' column value is 'not out' or 'retired not out', otherwise sets it to 0.
        2. Replaces empty values in the 'runs', 'fours', 'sixes', 'balls', and 'position' columns with '0' and converts them to integers.
        3. Adds a new column 'initial_name' which contains the initials and surname of each batsman's name.

        Parameters:
        - bat: A pandas DataFrame containing the batting data.

        Returns:
        - bat: The standardized batting data as a pandas DataFrame.
        """
        if not bat.empty:
            bat['not_out'] = np.where(bat['how_out'].isin(
                ['not out', 'retired not out', 'did not bat']), 1, 0)
            for col in ['runs', 'fours', 'sixes', 'balls', 'position']:
                bat[col] = bat[col].replace('', '0').astype('int')
            bat['initial_name'] = bat['batsman_name'].apply(
                lambda x: self._get_initials_surname(x))
        else:
            self.logger.info('No batting')
            bat = pd.DataFrame(columns=config.STANDARD_BATTING_COLS)
        # bat['batsman_id'] = bat['batsman_id'].astype('int')
        return bat

    def _get_result_letter(self, data, team_ids):
        """
        Get the result letter based on the provided data and team IDs.

        Parameters:
        - data: A dictionary containing the data.
        - team_ids: A list of team IDs.

        Returns:
        - result_letter: The result letter based on the provided data and team IDs.
        """

        result_letter = data['result']
        applied_to = None
        if data['result_applied_to']:
            applied_to = float(data['result_applied_to'])
        if result_letter in config.NEUTRAL_RESULTS:
            return result_letter

        if applied_to not in team_ids:
            return config.RESULTS_SWAPPER.get(result_letter)
        return result_letter

    def _clean_league_table(self, df, simple):
        """
        Cleans the league table dataframe by converting column names to uppercase,
        converting certain columns to integer type, and performing calculations
        to derive additional columns.

        Parameters:
        - df (pandas.DataFrame): The league table dataframe to be cleaned.
        - simple (bool): Flag indicating whether to perform simple cleaning or not.
        - key (str): The key used to determine the cleaning process.

        Returns:
        - df (pandas.DataFrame): The cleaned league table dataframe.
        """
        df.columns = [i.upper() for i in df.columns]
        wins = config.LEAGUE_TABLE_WIN_TYPES
        draws = config.LEAGUE_TABLE_DRAW_TYPES
        losses = config.LEAGUE_TABLE_LOSS_TYPES

        # if 'W - Total wins' in key:
        #     wins.remove('W')

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

            df = df[['POSITION', 'TEAM', 'wins', 'draws', 'losses', 'PTS']]
            df.rename(columns={'wins': 'W', 'draws': 'D',
                      'losses': 'L'}, inplace=True)
        return df

    def _make_api_request(self, url):
        """
        Makes an API request to the specified URL.

        Args:
            url (str): The URL to make the request to.

        Returns:
            dict: The JSON response from the API.

        Raises:
            Exception: If the request fails with a non-200 status code.

        """

        self.logger.info(f'Making request to: {url}')
        req = requests.get(url)
        self.logger.info(f'Req response: {req.status_code}')
        if req.status_code != 200:
            raise Exception(f'ERROR ({req.status_code}): {req.reason}')

        return req.json()

    def _convert_team_ids_to_ints(self, team_ids):
        """
        Converts a list of team IDs to integers.

        Parameters:
        - team_ids (list): A list of team IDs.

        Returns:
        - list: A list of team IDs converted to integers.
        """
        team_ids = [int(i) for i in team_ids]
        return team_ids

    def _count_balls(self, n):
        """
        Counts the total number of balls based on the given input string.

        Parameters:
        n (str): The input string representing the number of overs and balls.

        Returns:
        int: The total number of balls.

        """
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
        """
        Calculates the number of overs and balls from the given total number of balls.

        Parameters:
        - n (int): The total number of balls.

        Returns:
        - str: The calculated number of overs and balls in the format 'o.b', where 'o' is the number of overs and 'b' is the number of balls.

        Example:
        >>> _calculate_overs(25)
        '4.1'
        """

        o = math.floor(n/6)
        b = int(n - (o*6))

        return f'{o}.{b}'

    def _clean_team_name(self, team: str) -> str:
        """
        Cleans the given team name by removing unwanted characters and words.

        Args:
            team (str): The team name to be cleaned.

        Returns:
            str: The cleaned team name.
        """
        if team.split(' - ')[0] in self.team_names:
            team = team.split(' - ')[0]
        else:
            for nth_team in config.N_TEAM_SWAP:
                team = team.replace(nth_team, 's')
            for banned_word in config.TEAM_NAME_BANNED_WORDS:
                team = team.replace(banned_word, '')
        team = " ".join(team.split())
        return team

    def _calculate_batting_average(self, row):
        """
        Calculate the batting average.

        Parameters:
        - row: dict, the row containing the runs and innings information

        Returns:
        - float or None: the batting average if innings is not zero, otherwise None
        """

        runs = row['runs']
        innings = row['innings_to_count']

        if innings == 0:
            return None
        else:
            return runs/innings

    def _get_players_used_in_match(self, match_id: int, api_key: str):
        """
        Retrieves the players used in a specific match.

        Args:
            match_id (int): The ID of the match.

        Returns:
            pandas.DataFrame: A DataFrame containing the players used in the match.
        """
        data = self._make_api_request(
            config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=api_key))

        home_t = pd.json_normalize(
            data['match_details'][0]['players'][0]['home_team'])
        home_t['team_id'] = int(data['match_details'][0]['home_team_id']
                                ) if data['match_details'][0]['home_team_id'] not in [None, ''] else None
        home_t['club_id'] = int(data['match_details'][0]['home_club_id']
                                ) if data['match_details'][0]['home_club_id'] not in [None, ''] else None

        away_t = pd.json_normalize(
            data['match_details'][0]['players'][1]['away_team'])
        away_t['team_id'] = int(data['match_details'][0]['away_team_id']
                                ) if data['match_details'][0]['away_team_id'] not in [None, ''] else None
        away_t['club_id'] = int(data['match_details'][0]['away_club_id']
                                ) if data['match_details'][0]['away_club_id'] not in [None, ''] else None

        teams = pd.concat([home_t, away_t]).reset_index(drop=True)
        teams['match_id'] = match_id
        return teams

    def _clean_column_names(self, x):
        if x[1] == '':
            return x[0]
        else:
            return x[0] + '_' + x[1]

    def _aggregate_fielding_stats(self, fielding, fielding_groupby):
        fielding = fielding.groupby(
            fielding_groupby, as_index=False).agg({'match_id': ['count', pd.Series.nunique]})
        fielding.columns = [self._clean_column_names(
            col) for col in fielding.columns]
        fielding.rename(columns={'match_id_count': 'dismissals',
                        'match_id_nunique': 'n_games'}, inplace=True)
        fielding.sort_values(['dismissals', 'n_games'], ascending=[
            False, True], inplace=True)

        fielding.dropna(subset=['fielder_name'], inplace=True)
        fielding = fielding.loc[fielding['fielder_name'] != '']
        # fielding.reset_index(drop=True, inplace=True)
        fielding = fielding.reset_index(
            drop=True).reset_index().rename(columns={'index': 'rank'})
        fielding['rank'] += 1
        return fielding

    def _aggregate_bowling_stats(self, bowling, bowling_groupby):
        bowling = bowling.groupby(bowling_groupby, as_index=False).agg(
            {'wickets': ['sum', 'max', lambda x: x[x >= 5].count()], 'balls': 'sum', 'maidens': 'sum', 'runs': 'sum', 'match_id': pd.Series.nunique})
        bowling.columns = [self._clean_column_names(
            col) for col in bowling.columns]
        bowling.rename(columns={'wickets_sum': 'wickets', 'wickets_max': 'max_wickets',
                       'wickets_<lambda_0>': '5fers'}, inplace=True)
        for agg in config.GROUPBY_AGGS:
            bowling.columns = [col.replace(agg, '') for col in bowling.columns]
        bowling = bowling.sort_values(['wickets', 'runs', 'balls', 'match_id'], ascending=[
            False, True, True, True]).reset_index(drop=True).reset_index().rename(columns={'index': 'rank'})
        bowling['overs'] = bowling['balls'].apply(
            lambda x: self._calculate_overs(x))
        bowling['average'] = bowling['runs']/bowling['wickets']
        bowling['sr'] = bowling['balls']/bowling['wickets']
        bowling['econ'] = (bowling['runs']/bowling['balls'])*6

        bowling['rank'] += 1
        return bowling

    def _aggregate_batting_stats(self, batting, batting_groupby):
        batting = batting.loc[batting['how_out'] != 'did not bat']
        batting = batting.groupby(batting_groupby, as_index=False).agg(
            {'runs': ['sum', 'max', lambda x: x[(x >= 50) & (x < 100)].count(), lambda x: x[x >= 100].count()], 'fours': 'sum', 'sixes': 'sum', 'balls': 'sum', 'not_out': 'sum', 'match_id': pd.Series.nunique, 'position': 'mean'})
        batting.columns = [self._clean_column_names(
            col) for col in batting.columns]
        batting.rename(columns={'runs_<lambda_0>': '50s', 'runs_<lambda_1>': '100s',
                       'runs_sum': 'runs', 'runs_max': 'top_score'}, inplace=True)
        for agg in config.GROUPBY_AGGS:
            batting.columns = [col.replace(agg, '') for col in batting.columns]
        batting['innings_to_count'] = batting['match_id']-batting['not_out']
        batting['average'] = batting.apply(
            lambda row: self._calculate_batting_average(row=row), axis=1)
        batting = batting.sort_values(['runs', 'average', 'balls', 'fours', 'sixes'], ascending=[
            False, False, True, False, False]).reset_index(drop=True).reset_index().rename(columns={'index': 'rank'})

        batting['rank'] += 1
        return batting
