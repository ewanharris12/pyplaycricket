import pandas as pd
import logging
import requests
import cachecontrol


from playcric import config
from playcric.utils import u


class pc(u):
    def __init__(self, api_key, site_id, club_names: list = [], team_name_to_ids_lookup: dict = {}):
        # super.__init__()
        self.api_key = api_key
        self.logger = logging.getLogger('pyplaycricket.playcricket')
        self.logger.info(f'Setting site_id as {site_id}')
        self.site_id = site_id
        self.team_names = []
        self.req_session = cachecontrol.CacheControl(requests.Session())

    def list_registered_players(self, site_id: int = None):
        """
        Retrieves a list of registered players from the specified site.

        Args:
            site_id (int, optional): The ID of the site to retrieve players from. If not provided, the default site ID will be used.

        Returns:
            pandas.DataFrame: A DataFrame containing the registered players' information.
        """
        site_id = self._set_site_id(site_id)
        data = self._make_api_request(config.PLAYERS_URL.format(
            site_id=site_id, api_key=self.api_key))

        df = pd.json_normalize(data['players'])
        return df

    # def get_all_matches_from_a_comp(self, season: int, team_ids: list = [], competition_ids: list = [], competition_types: list = [])

    def get_all_matches(self, season: int, team_ids: list = [], competition_ids: list = [], competition_types: list = [], site_id: int = None):
        """
        Retrieves all matches based on the specified filters.

        Args:
            season (int): The season for which matches should be retrieved.
            team_ids (list, optional): A list of team IDs to filter the matches. Defaults to an empty list.
            competition_ids (list, optional): A list of competition IDs to filter the matches. Defaults to an empty list.
            competition_types (list, optional): A list of competition types to filter the matches. Defaults to an empty list.
            site_id (int, optional): The site ID to retrieve matches from. Defaults to None.

        Returns:
            pandas.DataFrame: A DataFrame containing the retrieved matches data.
        """
        site_id = self._set_site_id(site_id)
        team_ids = self._convert_team_ids_to_ints(team_ids)
        data = self._make_api_request(config.MATCHES_URL.format(
            site_id=site_id, season=season, api_key=self.api_key))

        df = pd.json_normalize(data['matches'])
        if df.empty:
            return pd.DataFrame()
        for col in ['last_updated', 'match_date']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format='%d/%m/%Y')
        for col in ['home_team_id', 'away_team_id']:
            if col in df.columns:
                df[col] = df[col].astype('int')
        if team_ids:
            self.logger.info(f'Filtering to team_ids: {team_ids}')
            df = df.loc[(df['home_team_id'].isin(team_ids)) |
                        (df['away_team_id'].isin(team_ids))]
        if competition_ids:
            self.logger.info(
                f'Filtering to competition_ids: {competition_ids}')
            df = df.loc[(df['competition_id'].isin(competition_ids))]
        if competition_types:
            self.logger.info(
                f'Filtering to competition_types: {competition_types}')
            df = df.loc[(df['competition_type'].isin(competition_types))]
        return df

    def get_league_table(self, competition_id: int, simple: bool = False, clean_names: bool = True):
        """
        Retrieves the league table for a given competition ID.

        Args:
            competition_id (int): The ID of the competition.
            simple (bool, optional): Flag to indicate whether to return a simplified version of the league table. 
                                    Defaults to False.

        Returns:
            tuple: A tuple containing the league table dataframe and the key used for column names.

        """
        data = self._make_api_request(config.LEAGUE_TABLE_URL.format(
            competition_id=competition_id, api_key=self.api_key))

        df = pd.json_normalize(data['league_table'][0]['values'])
        df.rename(columns=data['league_table'][0]['headings'], inplace=True)
        key = [i.replace('&nbsp;', '')
               for i in data['league_table'][0]['key'].split(',')]
        df = self._clean_league_table(df=df, simple=simple, key=key)
        if clean_names:
            df['TEAM'] = df['TEAM'].apply(
                lambda x: self._clean_team_name(team=x))

        return df, key

    def get_match_result_string(self, match_id: int):
        """
        Retrieves the match result description for a given match ID.

        Parameters:
        - match_id (int): The ID of the match.

        Returns:
        - result_text (str): The description of the match result.
        """
        data = self._make_api_request(
            config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))

        result_text = data[0]['result_description']
        return result_text

    def get_result_for_my_team(self, match_id: int, team_ids: list = None):
        """
        Retrieves the result letter for a given match and team(s).

        Args:
            match_id (int): The ID of the match.
            team_ids (list, optional): A list of team IDs. Defaults to None.

        Returns:
            str: The result letter indicating the outcome of the match for the specified team(s).
        """
        team_ids = self._convert_team_ids_to_ints(team_ids)
        data = self._make_api_request(
            config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))
        data = data['match_details'][0]
        result_letter = self._get_result_letter(data=data, team_ids=team_ids)
        return result_letter

    def get_all_players_involved(self, match_ids: list, team_ids: list = []):
        """
        Retrieves all players involved in the specified matches and teams.

        Args:
            match_ids (list): A list of match IDs.
            team_ids (list, optional): A list of team IDs. If not provided, it uses the default team IDs.

        Returns:
            pandas.DataFrame: A DataFrame containing the details of all players involved.
        """
        players = []
        for match_id in match_ids:
            players.append(self._get_players_used_in_match(
                match_id=match_id, api_key=self.api_key))
        players = pd.concat(players)

        if team_ids:
            players = players.loc[players['team_id'].isin(team_ids)]

        players = players.drop_duplicates(
            subset=['player_name', 'player_id', 'match_id'])
        # players['player_id'] = players['player_id'].astype('int')
        players.reset_index(inplace=True, drop=True)
        return players

    def get_innings_total_scores(self, match_id: int):
        """
        Retrieves the total scores for each innings of a given match.

        Args:
            match_id (int): The ID of the match.

        Returns:
            pandas.DataFrame: A DataFrame containing the total scores for each innings.
        """
        data = self._make_api_request(
            config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))
        inn = pd.json_normalize(data['match_details'][0]['innings'])
        inn = inn.drop(
            columns=['bat', 'fow', 'bowl', 'innings_number'], errors='ignore').reset_index()
        inn['match_id'] = match_id
        inn['index'] += 1
        inn.rename(columns={'index': 'innings_number'}, inplace=True)
        inn.dropna(axis=0, how='all', inplace=True)
        return inn

    def get_match_partnerships(self, match_id: int):
        """
        Retrieves the partnerships data for a given match.

        Parameters:
        - match_id (int): The ID of the match.

        Returns:
        - partnerships (DataFrame): The partnerships data for the match.
        """
        data = self._make_api_request(
            config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))
        data = data['match_details'][0]
        all_ids = [int(data['home_team_id']), int(data['away_team_id'])]
        team_name_lookup = {int(data['home_team_id']): data['home_club_name'] + ' - ' + data['home_team_name'],
                            int(data['away_team_id']): data['away_club_name'] + ' - ' + data['away_team_name']}

        innings_n = 1
        partnerships = []
        for innings in data['innings']:
            p = pd.json_normalize(innings['fow'])
            batting_name = innings['team_batting_name']
            batting_id = int(innings['team_batting_id'])
            if batting_id == all_ids[0]:
                bowling_id = all_ids[1]
            else:
                bowling_id = all_ids[0]
            bowling_name = team_name_lookup.get(bowling_id)

            p = self._add_team_name_id_and_innings(
                p, batting_name, batting_id, bowling_name, bowling_id, innings_n, match_id)
            partnerships.append(p)
            innings_n += 1

        partnerships = pd.concat(partnerships)
        if not partnerships.empty:
            partnerships['score_added'] = partnerships['runs'].astype(
                'int') - partnerships['runs'].astype('int').shift(1).fillna(0)
        else:
            partnerships['score_added'] = None
        return partnerships

    def get_individual_stats(self, match_id: int, team_ids: list = [], stat_string: bool = False):
        data = self._make_api_request(
            config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))
        data = data['match_details'][0]
        all_ids = [int(data['home_team_id']), int(data['away_team_id'])]
        team_name_lookup = {int(data['home_team_id']): data['home_club_name'] + ' - ' + data['home_team_name'],
                            int(data['away_team_id']): data['away_club_name'] + ' - ' + data['away_team_name']}

        all_batting = []
        all_bowling = []

        innings_n = 1
        for innings in data['innings']:
            bat = pd.json_normalize(innings['bat'])
            if bat.empty:
                continue
            batting_name = innings['team_batting_name']
            batting_id = int(innings['team_batting_id'])

            if batting_id == all_ids[0]:
                bowling_id = all_ids[1]
            else:
                bowling_id = all_ids[0]
            bowling_name = team_name_lookup.get(bowling_id)

            bowl = pd.json_normalize(innings['bowl'])
            bowl = self._add_team_name_id_and_innings(
                bowl, bowling_name, bowling_id, batting_name, batting_id, innings_n, match_id)

            bat = self._add_team_name_id_and_innings(
                bat, batting_name, batting_id, bowling_name, bowling_id, innings_n, match_id)

            all_batting.append(bat)
            all_bowling.append(bowl)

            innings_n += 1

        if len(all_batting) == 0:
            return pd.DataFrame(columns=config.STANDARD_BATTING_COLS), pd.DataFrame(config.STANDARD_BOWLING_COLS)

        all_batting = self._standardise_bat(pd.concat(all_batting))
        all_bowling = self._standardise_bowl(pd.concat(all_bowling))

        if team_ids:
            all_batting = all_batting.loc[all_batting['team_id'].isin(
                team_ids)]
            all_bowling = all_bowling.loc[all_bowling['team_id'].isin(
                team_ids)]

        if stat_string:
            all_batting['stat'] = all_batting.apply(
                lambda row: self._write_batting_string(row), axis=1)
            all_bowling['stat'] = all_bowling.apply(
                lambda row: self._write_bowling_string(row), axis=1)

        # all_bowling

        return all_batting, all_bowling

    def get_stat_totals(self,  match_ids: list, team_ids: list = [], group_by_team: bool = False, for_graphics: bool = False, n_players: int = 10):
        """
        Retrieves the batting, bowling, and fielding statistics for a given set of match and team IDs.

        Args:
            match_ids (list): A list of match IDs.
            team_ids (list, optional): A list of team IDs.
            for_graphics (bool, optional): A flag indicating whether the statistics are for graphics.
            n_players (int, optional): The number of players to include in the statistics.

        Returns:
            tuple: A tuple containing the batting, bowling, and fielding statistics.

        """
        batting, bowling, fielding = self.get_individual_stats_from_all_games(
            match_ids, team_ids, stat_string=False)

        batting_groupby = ['initial_name', 'batsman_name', 'batsman_id']
        bowling_groupby = ['initial_name', 'bowler_name', 'bowler_id']
        fielding_groupby = ['fielder_name', 'fielder_id']
        if group_by_team:
            batting_groupby += ['team_id']
            bowling_groupby += ['team_id']
            fielding_groupby += ['team_id']

        batting = batting.loc[batting['how_out'] != 'did not bat']
        batting = batting.groupby(batting_groupby, as_index=False).agg(
            {'runs': 'sum', 'fours': 'sum', 'sixes': 'sum', 'balls': 'sum', 'not_out': 'sum', 'match_id': pd.Series.nunique, 'position': 'mean'})
        batting['innings_to_count'] = batting['match_id']-batting['not_out']
        batting['average'] = batting.apply(
            lambda row: self._calculate_batting_average(row=row), axis=1)
        batting = batting.sort_values(['runs', 'average', 'balls', 'fours', 'sixes'], ascending=[
            False, False, True, False, False]).reset_index(drop=True).reset_index().rename(columns={'index': 'rank'})

        batting['rank'] += 1

        bowling = bowling.groupby(bowling_groupby, as_index=False).agg(
            {'wickets': 'sum', 'balls': 'sum', 'maidens': 'sum', 'runs': 'sum', 'match_id': pd.Series.nunique})
        bowling = bowling.sort_values(['wickets', 'runs', 'balls', 'match_id'], ascending=[
            False, True, True, True]).reset_index(drop=True).reset_index().rename(columns={'index': 'rank'})
        bowling['overs'] = bowling['balls'].apply(
            lambda x: self._calculate_overs(x))
        bowling['average'] = bowling['runs']/bowling['wickets']
        bowling['sr'] = bowling['balls']/bowling['wickets']
        bowling['econ'] = (bowling['runs']/bowling['balls'])*6

        bowling['rank'] += 1

        fielding = fielding.groupby(
            fielding_groupby, as_index=False).agg({'match_id': ['count', pd.Series.nunique]})
        fielding.columns = [self._clean_column_names(
            col) for col in fielding.columns]
        fielding.rename(columns={'match_id_count': 'dismissals',
                        'match_id_nunique': 'n_games'}, inplace=True)
        fielding.sort_values(['dismissals', 'n_games'], ascending=[
            False, True], inplace=True)
        fielding = fielding.reset_index(
            drop=True).reset_index().rename(columns={'index': 'rank'})

        fielding = fielding.loc[fielding['fielder_name'] != '']
        fielding['rank'] += 1

        if for_graphics:
            batting = batting[config.STATS_TOTALS_BATTING_COLUMNS].head(
                n_players)
            bowling = bowling[config.STATS_TOTALS_BOWLING_COLUMNS].head(
                n_players)
            fielding = fielding[config.STATS_TOTALS_FIELDING_COLUMNS].head(
                n_players)

            batting = self._extract_string_for_graphic(batting)
            bowling = self._extract_string_for_graphic(bowling)
            fielding = self._extract_string_for_graphic(fielding)
        return batting, bowling, fielding

    def get_individual_stats_from_all_games(self,  match_ids: list, team_ids: list = [], stat_string: bool = False):
        """
        Retrieves individual batting, bowling, and fielding statistics from all games.

        Args:
            match_ids (list): List of match IDs.
            team_ids (list): List of team IDs.
            stat_string (str): String representing the desired statistics.

        Returns:
            tuple: A tuple containing three pandas DataFrames - batting, bowling, and fielding.
                - batting: DataFrame containing individual batting statistics.
                - bowling: DataFrame containing individual bowling statistics.
                - fielding: DataFrame containing individual fielding statistics.

        Raises:
            ValueError: If any of the match IDs fail to retrieve statistics.

        """
        batting = []
        bowling = []
        for match_id in match_ids:
            try:
                bat, bowl = self.get_individual_stats(
                    match_id=match_id, stat_string=stat_string)
            except Exception as e:
                raise ValueError(f'MATCH ID {match_id} FAILED WITH: {e}')
            batting.append(bat)
            bowling.append(bowl)

        batting = pd.concat(batting)
        bowling = pd.concat(bowling)
        bowling['wickets'] = bowling['wickets'].fillna(0).astype('int')
        fielding = batting

        if team_ids:
            fielding = batting.loc[~batting['team_id'].isin(team_ids)]
            batting = batting.loc[batting['team_id'].isin(team_ids)]
            bowling = bowling.loc[bowling['team_id'].isin(team_ids)]

        batting.sort_values(['runs', 'balls'], ascending=[
                            False, True], inplace=True)
        bowling.sort_values(['wickets', 'runs', 'balls'], ascending=[
                            False, True, True], inplace=True)

        batting.reset_index(inplace=True, drop=True)
        fielding.reset_index(inplace=True, drop=True)
        bowling.reset_index(inplace=True, drop=True)

        return batting, bowling, fielding
