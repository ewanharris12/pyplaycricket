from playcric.playcricket import pc
from playcric import config
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import math


class acc(pc):
    def __init__(self, api_key, site_id, club_names: list = [], team_name_to_ids_lookup: list = []):
        """
        Initialize the Alleyn class.

        Args:
            api_key (str): The API key for accessing the Play-Cricket API.
            site_id (str): The ID of the Play-Cricket site.
            club_names (list, optional): A list of club names. Defaults to an empty list.
            team_name_to_ids_lookup (list, optional): A list of team name to team ID mappings. Defaults to an empty list.
        """
        super().__init__(api_key, site_id)
        self.logger = logging.getLogger('pyplaycricket.alleyn')
        self.api_key = api_key
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

    def get_innings_scores(self, match_ids: list = []):
        """
        Retrieves the team names and innings scores for the given match IDs.

        Args:
            match_ids (list): A list of match IDs.

        Returns:
            tuple: A tuple containing the team names and innings scores as strings.
        """
        team_names = []
        innings_scores = []

        for match_id in match_ids:
            data = self._make_api_request(
                config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))
            data = data['match_details'][0]
            if data['result']:
                for innings in data['innings']:
                    team = innings['team_batting_name']
                    if self.team_ids_to_names_lookup.get(int(innings['team_batting_id'])) == 'Barbarians':
                        team = 'Brixton Barbarians'
                    team = self._clean_team_name(team)

                    team_names.append(team.strip())

                    total_runs = innings['runs']
                    if innings['wickets'] == '10':
                        wickets = ''
                    else:
                        wickets = '-' + innings['wickets']
                    score_string = f'{total_runs}{wickets}'
                    innings_scores.append(score_string)

        team_names = '\n'.join(team_names)
        innings_scores = '\n'.join(innings_scores)

        return team_names, innings_scores

    def get_individual_performances_for_graphic(self, match_ids: list = []):
        """
        Retrieves individual performances for a given list of match IDs and returns a summary string.

        Args:
            match_ids (list): A list of match IDs for which individual performances are to be retrieved.

        Returns:
            str: A summary string containing the top batting and bowling performances for each match ID.
        """
        stats_summary = ''
        for match_id in match_ids:
            print(match_id)
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

                bowln = bowln.head(3)

                bowling_names = [i.upper()
                                 for i in bowln['initial_name'].tolist()]
                bowling_stats = bowln['stat'].tolist()

                bowling_names, bowling_stats = self._make_sure_number_of_players_is_consistent(
                    bowling_names, bowling_stats)

                stats_summary = self._add_to_stats_string(
                    stats_summary, bowling_names, bowling_stats)

        return stats_summary

    def _add_to_stats_string(self, stats_summary: str, names_list: list, stats_list: list):
        """
        Adds the names and stats to the given stats_summary string.

        Args:
            stats_summary (str): The current stats summary string.
            names_list (list): A list of names to be added to the stats summary.
            stats_list (list): A list of stats to be added to the stats summary.

        Returns:
            str: The updated stats summary string.
        """
        stats_summary += '\n'.join(names_list)
        stats_summary += '\n'
        stats_summary += '\n'.join(stats_list)
        stats_summary += '\n'
        return stats_summary

    def _make_sure_number_of_players_is_consistent(self, names_list: list, stats_list: list):
        """
        Ensures that the number of players is consistent by adding empty values to the lists if necessary.

        Args:
            names_list (list): A list of player names.
            stats_list (list): A list of player stats.

        Returns:
            tuple: A tuple containing the updated names_list and stats_list.
        """
        for i in range(0, 3):
            if len(names_list) < 3:
                names_list.append(' ')
                stats_list.append(' ')
        return names_list, stats_list

    def get_result_description_and_margin(self, match_ids: list, team_ids: list):
        """
        Retrieves the result description and margin for a list of match IDs and team IDs.

        Args:
            match_ids (list): A list of match IDs.
            team_ids (list): A list of team IDs.

        Returns:
            str: A string containing the result description and margin for each match.

        """
        all_result_strings = ''
        for match_id in match_ids:
            # print(match_id)
            self.logger.info(f'Match ID: {match_id}')
            data = self._make_api_request(
                config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))
            data = data['match_details'][0]
            if int(data['home_team_id']) in team_ids:
                team_name = data['home_team_name']
            else:
                team_name = data['away_team_name']
            result_letter = self._get_result_letter(
                data=data, team_ids=team_ids)

            result_string = team_name + ' ' + \
                config.RESULTS_TEXT.get(result_letter)
            if result_letter == 'D':
                result_string = 'Match drawn'
            elif result_letter in config.NEUTRAL_RESULTS:
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
        """
        Orders the matches for the graphics.

        Args:
            matches (pd.DataFrame): The DataFrame containing the matches data.

        Returns:
            pd.DataFrame: The DataFrame with matches ordered by match date and club team name.
        """
        matches['club_team_name'] = np.where(matches['home_team_id'].isin(self.team_ids), matches['home_team_id'].apply(
            lambda x: self.team_ids_to_names_lookup.get(int(x))), matches['away_team_id'].apply(lambda x: self.team_ids_to_names_lookup.get(int(x))))
        matches.sort_values(['match_date', 'club_team_name'],
                            ascending=True, inplace=True)

        return matches

    def get_weekend_matches(self, matches: pd.DataFrame, saturday: datetime):
        """
        Retrieves the matches that are scheduled for a given weekend.

        Args:
            matches (pd.DataFrame): The DataFrame containing all the matches.
            saturday (datetime): The date of the Saturday of the weekend.

        Returns:
            pd.DataFrame: The DataFrame containing the matches scheduled for the weekend.
        """
        matches = matches.loc[matches['match_date'].isin(
            [saturday, saturday+timedelta(days=1)])].copy()

        matches = self.order_matches_for_the_graphics(matches=matches)

        return matches

    def get_season_opposition_list(self, matches: pd.DataFrame):
        """
        Returns a formatted string containing the list of opposition teams for the season.

        Args:
            matches (pd.DataFrame): A DataFrame containing the match data.

        Returns:
            str: A formatted string containing the list of opposition teams.
        """
        teams_list = []
        for index, row in matches.iterrows():
            teams_list.append(row['home_club_name'])
            teams_list.append(row['away_club_name'])
        teams_list = [self._clean_team_name(i)
                      for i in teams_list if i not in self.team_names]
        teams_list = '\n'.join(teams_list)
        return teams_list

    def get_cutout_off_league_table(self, league_table: pd.DataFrame, n_teams: int = 3):
        """
        Returns a string representation of a cutout from the league table, centered around a specific team.

        Args:
            league_table (pd.DataFrame): The league table as a pandas DataFrame.
            n_teams (int, optional): The number of teams to include in the cutout. Defaults to 3.

        Returns:
            str: A string representation of the cutout from the league table.

        Raises:
            AssertionError: If n_teams is not an odd number.
            AssertionError: If there are not enough teams in the league table.
            Exception: If none of the teams in self.team_names are found in the league table.

        """
        assert (n_teams % 2 == 1, "Please choose an odd number for n_teams")
        assert (len(league_table) > n_teams, "Not enough teams in the league")

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
            league_table = league_table.iloc[max(
                [team_index - buffer, 0]):min([team_index+buffer+1, len(league_table)+1])]

        league_table['TEAM'] = league_table['TEAM'].apply(
            lambda x: self._clean_team_name(x))

        league_table_string = []
        for _, row in league_table.iterrows():
            league_table_string += [row['POSITION'], row['TEAM'],
                                    str(row['W']), str(row['D']), str(row['L']), str(row['PTS'])]
        league_table_string = '\n'.join(league_table_string)

        return league_table_string

    def get_season_stats_totals(self, match_ids: list, team_ids: list = [], for_graphics: bool = False, n_players: int = 10):
        """
        Calculate the season statistics totals for batting, bowling, and fielding.

        Args:
            match_ids (list): List of match IDs to consider for calculating the statistics.
            team_ids (list, optional): List of team IDs to filter the statistics. Defaults to an empty list.
            for_graphics (bool, optional): Flag indicating whether the statistics are for graphics. Defaults to False.
            n_players (int, optional): Number of top players to include in the statistics. Defaults to 10.

        Returns:
            tuple: A tuple containing the calculated statistics for batting, bowling, and fielding.

        """
        if not team_ids:
            team_ids = self.team_ids

        batting, bowling, fielding = self._get_individual_stats_from_all_games(
            match_ids, team_ids, stat_string=False)

        batting = batting.loc[batting['how_out'] != 'did not bat']
        batting = batting.groupby(['initial_name', 'batsman_name'  # , 'batsman_id'
                                   ], as_index=False).agg(
            {'runs': 'sum', 'fours': 'sum', 'sixes': 'sum', 'balls': 'sum', 'not_out': 'sum', 'match_id': pd.Series.nunique})
        batting['innings_to_count'] = batting['match_id']-batting['not_out']
        batting['average'] = batting.apply(
            lambda row: self._calculate_batting_average(row=row), axis=1)
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

    def _extract_string_for_graphic(self, df):
        """
        Extracts a string representation of the DataFrame for graphic display.

        Args:
            df (pandas.DataFrame): The DataFrame to extract the string representation from.

        Returns:
            str: The string representation of the DataFrame for graphic display.
        """
        string_for_graphic = ''
        for index, row in df.iterrows():
            for col in df.columns:
                string_for_graphic += str(row[col]) + '\n'
        return string_for_graphic

    def get_best_individual_performances(self, match_ids: list, team_ids: list = [], n_players=5, for_graphics: bool = False):
        """
        Retrieves the best individual performances in terms of batting and bowling for the given match and team IDs.

        Args:
            match_ids (list): List of match IDs to consider.
            team_ids (list, optional): List of team IDs to consider. If not provided, all team IDs will be considered.
            n_players (int, optional): Number of top players to retrieve. Defaults to 5.
            for_graphics (bool, optional): Flag indicating whether the results are intended for graphics. Defaults to False.

        Returns:
            tuple: A tuple containing two pandas DataFrames - `batting` and `bowling`. 
                   The `batting` DataFrame contains the best individual batting performances, 
                   while the `bowling` DataFrame contains the best individual bowling performances.
        """
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
        """
        Adds a 'title' column to the given DataFrame based on the 'initial_name' and 'opposition_name' columns.

        Args:
            df (pandas.DataFrame): The DataFrame containing the 'initial_name' and 'opposition_name' columns.

        Returns:
            pandas.DataFrame: The DataFrame with the 'title' column added.
        """
        df['title'] = df['initial_name'] + ' vs ' + df['opposition_name'].apply(
            lambda x: self._clean_team_name(x))
        return df

    def _get_individual_stats_from_all_games(self, match_ids, team_ids, stat_string):
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

        batting.reset_index(inplace=True, drop=True)
        fielding.reset_index(inplace=True, drop=True)
        bowling.reset_index(inplace=True, drop=True)

        return batting, bowling, fielding

    def get_all_players_involved(self, match_ids: list, team_ids: list = []):
        """
        Retrieves all players involved in the specified matches and teams.

        Args:
            match_ids (list): A list of match IDs.
            team_ids (list, optional): A list of team IDs. If not provided, it uses the default team IDs.

        Returns:
            pandas.DataFrame: A DataFrame containing the details of all players involved.
        """
        if not team_ids:
            team_ids = self.team_ids
        players = []
        for match_id in match_ids:
            players.append(self.get_players_used_in_match(match_id=match_id))
        players = pd.concat(players)
        players = players.loc[players['team_id'].isin(team_ids)]

        players = players.drop_duplicates(subset=['player_name', 'player_id'])
        players.reset_index(inplace=True, drop=True)
        return players
