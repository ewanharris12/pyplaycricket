import pandas as pd
import numpy as np
import requests
import logging


from playcric import config
from playcric.utils import u
# from playcric.alleyn import acc


class pc(u):
    def __init__(self, api_key, site_id, club_names: list = [], team_name_to_ids_lookup: dict = {}):
        # super.__init__()
        self.api_key = api_key
        self.logger = logging.getLogger('pyplaycricket.playcricket')
        self.logger.info(f'Setting site_id as {site_id}')
        self.site_id = site_id
        if not club_names:
            self.team_names = config.TEAM_NAMES
        else:
            self.team_names = club_names

        if not team_name_to_ids_lookup:
            self.team_name_to_ids_lookup = config.TEAM_NAME_TO_IDS_LOOKUP
        else:
            self.team_name_to_ids_lookup = team_name_to_ids_lookup
        self.team_ids = list(self.team_name_to_ids_lookup.values())
        self.team_ids_to_names_lookup = {
            v: k for k, v in self.team_name_to_ids_lookup.items()}

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

    def get_league_table(self, competition_id: int, simple: bool = False):
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

    def get_players_used_in_match(self, match_id: int):
        """
        Retrieves the players used in a specific match.

        Args:
            match_id (int): The ID of the match.

        Returns:
            pandas.DataFrame: A DataFrame containing the players used in the match.
        """
        data = self._make_api_request(
            config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))

        home_t = pd.json_normalize(
            data['match_details'][0]['players'][0]['home_team'])
        home_t['team_id'] = int(data['match_details'][0]['home_team_id'])
        away_t = pd.json_normalize(
            data['match_details'][0]['players'][1]['away_team'])
        away_t['team_id'] = int(data['match_details'][0]['away_team_id'])

        teams = pd.concat([home_t, away_t]).reset_index(drop=True)
        return teams

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

    def get_individual_stats(self, match_id: int, team_ids: list = None, stat_string: bool = False):
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

        all_bowling

        return all_batting, all_bowling
