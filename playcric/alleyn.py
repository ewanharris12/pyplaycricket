from playcric.playcricket import pc
from playcric import config
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging


class acc(pc):
    def __init__(self, api_key, site_id, club_names: list = [], team_name_to_ids_lookup: list = []):
        super().__init__(api_key, site_id)
        self.api_key = api_key
        logging.info(f'Setting site_id as {site_id}')
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

    def get_innings_scores(self, match_ids: list = []):
        n = 1
        all_match_summary_strings = ''
        for match_id in match_ids:
            data = self._make_api_request(
                config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))
            data = data['match_details'][0]
            if data['result']:
                teams = []
                score_strings = []
                for innings in data['innings']:
                    team = innings['team_batting_name']
                    if self.team_ids_to_names_lookup.get(int(innings['team_batting_id'])) == 'Barbarians':
                        team = 'Brixton Barbarians'
                    team = self._clean_team_name(team)

                    teams.append(team.strip())

                    total_runs = innings['runs']
                    if innings['wickets'] == '10':
                        wickets = 'ao'
                    else:
                        wickets = '-'+innings['wickets']
                    score_string = f'{total_runs}{wickets}'
                    score_strings.append(score_string)

                if n % 2 == 0:
                    logging.info('score_team_team_score')
                    match_summary_string = f'{score_strings[0]}\n{teams[0]}\n{teams[1]}\n{score_strings[1]}\n'
                else:
                    logging.info('team_score_score_team')
                    match_summary_string = f'{teams[0]}\n{score_strings[0]}\n{score_strings[1]}\n{teams[1]}\n'

                all_match_summary_strings += match_summary_string
                n += 1

        return all_match_summary_strings

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

    def get_individual_performances_for_graphic(self, match_ids: list = []):
        stats_summary = ''
        for match_id in match_ids:
            bat, bowl = self.get_individual_stats(
                match_id=match_id, stat_string=True)
            for innings in [1, 2]:
                batn = bat.loc[bat['innings'] == innings]
                batn = batn.loc[batn['how_out'] != 'did not bat']
                batn.sort_values(['runs', 'balls', 'not_out', 'position'], ascending=[
                                 False, True, False, True], inplace=True)
                batn = batn.head(3)

                batting_names = [i.upper()
                                 for i in batn['initial_name'].tolist()]
                batting_stats = batn['stat'].tolist()

                batting_names, batting_stats = self._make_sure_number_of_players_is_consistent(
                    batting_names, batting_stats)

                stats_summary = self._add_to_stats_string(
                    stats_summary, batting_names, batting_stats)

                bowln = bowl.loc[bowl['innings'] == innings]
                bowln = bowln.loc[bowln['wickets'] > 0]
                bowln.sort_values(['wickets', 'runs', 'overs'], ascending=[
                                  False, True, False], inplace=True)

                bowling_names = [i.upper()
                                 for i in bowln['initial_name'].tolist()]
                bowling_stats = bowln['stat'].tolist()

                bowling_names, bowling_stats = self._make_sure_number_of_players_is_consistent(
                    bowling_names, bowling_stats)

                stats_summary = self._add_to_stats_string(
                    stats_summary, bowling_names, bowling_stats)

        return stats_summary

    def _add_to_stats_string(self, stats_summary: str, names_list: list, stats_list: list):
        stats_summary += '\n'.join(names_list)
        stats_summary += '\n'
        stats_summary += '\n'.join(stats_list)
        stats_summary += '\n'
        return stats_summary

    def _make_sure_number_of_players_is_consistent(self, names_list: list, stats_list: list):
        for i in range(0, 3):
            if len(names_list) < 3:
                names_list.append(' ')
                stats_list.append(' ')
        return names_list, stats_list

    def get_result_description_and_margin(self, match_ids: list, team_ids: list):
        all_result_strings = ''
        for match_id in match_ids:
            # print(match_id)
            logging.info(f'Match ID: {match_id}')
            data = self._make_api_request(
                config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))
            data = data['match_details'][0]
            result_letter = self._get_result_letter(
                data=data, team_ids=team_ids)

            result_string = config.RESULTS_TEXT.get(result_letter)
            if result_letter in config.NEUTRAL_RESULTS:
                pass
            elif data['batted_first'] == data['result_applied_to']:
                n_runs = int(data['innings'][0]['runs']) - \
                    int(data['innings'][1]['runs'])
                result_string += f' {n_runs} runs'

            else:
                n_wickets = 10 - int(data['innings'][1]['wickets'])
                result_string += f' {n_wickets} wickets'

            result_string += '\n'
            # print(result_string)
            all_result_strings += result_string
        return all_result_strings

    def order_matches_for_the_graphics(self, matches: pd.DataFrame):
        matches['club_team_name'] = np.where(matches['home_team_id'].isin(self.team_ids), matches['home_team_id'].apply(
            lambda x: self.team_ids_to_names_lookup.get(int(x))), matches['away_team_id'].apply(lambda x: self.team_ids_to_names_lookup.get(int(x))))
        matches.sort_values(['match_date', 'club_team_name'],
                            ascending=True, inplace=True)

        return matches

    def get_weekend_matches(self, matches: pd.DataFrame, saturday: datetime):
        matches = matches.loc[matches['match_date'].isin(
            [saturday, saturday+timedelta(days=1)])].copy()

        matches = self.order_matches_for_the_graphics(matches=matches)

        return matches

    def get_season_opposition_list(self, matches: pd.DataFrame):
        teams_list = []
        for index, row in matches.iterrows():
            teams_list.append(row['home_club_name'])
            teams_list.append(row['away_club_name'])
        teams_list = [self._clean_team_name(i)
                      for i in teams_list if i not in self.team_names]
        teams_list = '\n'.join(teams_list)
        return teams_list

    def get_cutout_off_league_table(self, league_table: pd.DataFrame, n_teams: int = 3):
        assert (n_teams % 2 == 1, "Please choose an odd number for n_teams")
        assert (len(league_table) > n_teams,
                "Not enough teams in the league")

        team_index = 1000
        for team in self.team_names:
            try:
                ti = [i.split('-')[0].strip()
                      for i in league_table['TEAM'].tolist()].index(team)
            except:
                ti = 1000
            team_index = min([team_index, ti])

        if team_index == 1000:
            raise Exception(
                f"None of the teams ({','.join(self.team_names)}) in the league table")
        buffer = int((n_teams-1)/2)
        if team_index == 0:
            league_table = league_table.iloc[0:n_teams]
        else:
            league_table = league_table.iloc[max([team_index -
                                             buffer, 0]):min([team_index+buffer+1, len(league_table)+1])]

        league_table['TEAM'] = league_table['TEAM'].apply(
            lambda x: self._clean_team_name(x))

        league_table_string = []
        for index, row in league_table.iterrows():
            league_table_string += [row['POSITION'], row['TEAM'],
                                    str(row['W']), str(row['D']), str(row['L']), str(row['PTS'])]
        league_table_string = '\n'.join(league_table_string)

        # pyperclip.copy(league_table_string)

        return league_table_string

    def get_season_stats_totals(self, match_ids: list, team_ids: list = [], for_graphics: bool = False, n_players: int = 10):
        if not team_ids:
            team_ids = self.team_ids

        batting, bowling, fielding = self._get_individual_stats_from_all_games(
            match_ids, team_ids, stat_string=False)

        batting = batting.loc[batting['how_out'] != 'did not bat']
        batting = batting.groupby(['initial_name', 'batsman_name'  # , 'batsman_id'
                                   ], as_index=False).agg(
            {'runs': 'sum', 'fours': 'sum', 'sixes': 'sum', 'balls': 'sum', 'not_out': 'sum', 'match_id': pd.Series.nunique})
        batting['average'] = batting['runs'] / \
            (batting['match_id']-batting['not_out'])
        batting = batting.sort_values(['runs', 'average', 'balls', 'fours', 'sixes'], ascending=[
            False, False, True, False, False]).reset_index(drop=True).reset_index().rename(columns={'index': 'rank'})
        batting['rank'] += 1

        bowling = bowling.groupby(['initial_name', 'bowler_name', 'bowler_id'], as_index=False).agg(
            {'wickets': 'sum', 'balls': 'sum', 'maidens': 'sum', 'runs': 'sum', 'match_id': pd.Series.nunique})
        bowling = bowling.sort_values(['wickets', 'runs', 'balls', 'match_id'], ascending=[
                                      False, True, True, True]).reset_index(drop=True).reset_index().rename(columns={'index': 'rank'})
        bowling['overs'] = bowling['balls'].apply(
            lambda x: self._calculate_overs(x))
        bowling['rank'] += 1

        fielding = fielding.groupby(
            ['fielder_name', 'fielder_id'], as_index=False).agg({'match_id': ['count', pd.Series.nunique]})
        fielding.columns = ['fielder_name',
                            'fielder_id', 'dismissals', 'n_games']
        fielding.sort_values(['dismissals', 'n_games'], ascending=[
            False, True], inplace=True)
        fielding = fielding.reset_index(
            drop=True).reset_index().rename(columns={'index': 'rank'})

        fielding = fielding.loc[fielding['fielder_name'] != '']

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

    def _extract_string_for_graphic(self, df):
        string_for_graphic = ''
        for index, row in df.iterrows():
            for col in df.columns:
                string_for_graphic += str(row[col]) + '\n'
        return string_for_graphic

    def get_best_individual_performances(self, match_ids: list, team_ids: list = [], n_players=5, for_graphics: bool = False):
        if not team_ids:
            team_ids = self.team_ids
        batting, bowling, fielding = self._get_individual_stats_from_all_games(
            match_ids=match_ids, team_ids=team_ids, stat_string=True)

        batting.sort_values(['runs', 'balls'], ascending=[
                            False, True], inplace=True)
        bowling.sort_values(['wickets', 'runs', 'balls'], ascending=[
                            False, True, True], inplace=True)

        if for_graphics:
            batting = self._get_individual_performance_title(
                batting)[config.INDIVIDUAL_PERFORMANCES_BATTING_COLUMNS].head(n_players)
            bowling = self._get_individual_performance_title(
                bowling)[config.INDIVIDUAL_PERFORMANCES_BOWLING_COLUMNS].head(n_players)

            batting = self._extract_string_for_graphic(batting)
            bowling = self._extract_string_for_graphic(bowling)

        return batting, bowling

    def _get_individual_performance_title(self, df):
        df['title'] = df['initial_name'] + ' vs ' + \
            df['opposition_name'].apply(
            lambda x: self._clean_team_name(x))
        return df

    def _get_individual_stats_from_all_games(self, match_ids, team_ids, stat_string):
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
        fielding = batting

        if team_ids:
            fielding = batting.loc[~batting['team_id'].isin(team_ids)]
            batting = batting.loc[batting['team_id'].isin(team_ids)]
            bowling = bowling.loc[bowling['team_id'].isin(team_ids)]

        return batting, bowling, fielding

    def get_all_players_involved(self, match_ids: list, team_ids: list = []):
        if not team_ids:
            team_ids = self.team_ids
        players = []
        for match_id in match_ids:
            players.append(self.get_players_used_in_match(match_id=match_id))
        players = pd.concat(players)
        players = players.loc[players['team_id'].isin(team_ids)]

        players = players.drop_duplicates(subset=['player_name', 'player_id'])
        return players
