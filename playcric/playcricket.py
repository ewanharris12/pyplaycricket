import pandas as pd
import numpy as np
import requests
import logging


from playcric import config
from playcric.utils import u


class pc(u):
    def __init__(self, api_key, site_id):
        # super.__init__()
        self.api_key = api_key
        logging.info(f'Setting site_id as {site_id}')
        self.site_id = site_id

    def list_registered_players(self):
        data = self._make_api_request(config.PLAYERS_URL.format(
            site_id=self.site_id, api_key=self.api_key))

        df = pd.json_normalize(data['players'])
        return df

    def get_all_matches(self, season: int, team_ids: list = [], competition_ids: list = [], competition_types: list = []):
        team_ids = self._convert_team_ids_to_ints(team_ids)
        data = self._make_api_request(config.MATCHES_URL.format(
            site_id=self.site_id, season=season, api_key=self.api_key))

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
            logging.info(f'Filtering to team_ids: {team_ids}')
            df = df.loc[(df['home_team_id'].isin(team_ids)) |
                        (df['away_team_id'].isin(team_ids))]
        if competition_ids:
            logging.info(f'Filtering to competition_ids: {competition_ids}')
            df = df.loc[(df['competition_id'].isin(competition_ids))]
        if competition_types:
            logging.info(
                f'Filtering to competition_types: {competition_types}')
            df = df.loc[(df['competition_type'].isin(competition_types))]
        return df

    def get_league_table(self, competition_id: int, simple: bool = False):
        data = self._make_api_request(config.LEAGUE_TABLE_URL.format(
            competition_id=competition_id, api_key=self.api_key))

        df = pd.json_normalize(data['league_table'][0]['values'])
        df.rename(columns=data['league_table'][0]['headings'], inplace=True)
        df = self._clean_league_table(df=df, simple=simple)
        key = [i.replace('&nbsp;', '')
               for i in data['league_table'][0]['key'].split(',')]
        return df, key

    def get_match_result_string(self, match_id: int):
        data = self._make_api_request(
            config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))

        result_text = data[0]['result_description']
        return result_text

    def get_result_for_my_team(self, match_id: int, team_ids: list = None):
        team_ids = self._convert_team_ids_to_ints(team_ids)
        data = self._make_api_request(
            config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))
        data = data['match_details'][0]
        result_letter = self._get_result_letter(data=data, team_ids=team_ids)
        return result_letter

    def get_players_used_in_match(self, match_id: int):
        data = self._make_api_request(
            config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))

        home_t = pd.json_normalize(
            data['match_details'][0]['players'][0]['home_team'])
        home_t['team_id'] = int(data['match_details'][0]['home_team_id'])
        away_t = pd.json_normalize(
            data['match_details'][0]['players'][1]['away_team'])
        away_t['team_id'] = int(data['match_details'][0]['away_team_id'])

        teams = pd.concat([home_t, away_t])
        return teams

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

        return all_batting, all_bowling
