from playcric.playcricket import pc
from playcric import config, alleyn_config
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging


class acc(pc):
    """
    Alleyn Cricket Club-specific subclass of the Play-Cricket wrapper.

    Extends ``pc`` with display and formatting methods tailored to Alleyn CC's
    graphics pipeline.  Club-specific constants (team IDs, banned words, etc.)
    are loaded from ``alleyn_config``.
    """

    def __init__(
        self,
        api_key: str,
        site_id: int,
        team_names: list | None = None,
        team_name_to_ids_lookup: dict | None = None,
    ):
        """
        Initialise the Alleyn CC client.

        Args:
            api_key (str): Play-Cricket API token.
            site_id (str): Play-Cricket site ID.
            team_names (list, optional): Club team name strings.
                Defaults to ``alleyn_config.TEAM_NAMES``.
            team_name_to_ids_lookup (dict, optional): Team name → ID mapping.
                Defaults to ``alleyn_config.TEAM_NAME_TO_IDS_LOOKUP``.
        """
        if team_names is None:
            team_names = alleyn_config.TEAM_NAMES
        if team_name_to_ids_lookup is None:
            team_name_to_ids_lookup = alleyn_config.TEAM_NAME_TO_IDS_LOOKUP

        super().__init__(
            api_key=api_key, site_id=site_id,
            team_names=team_names,
            team_name_to_ids_lookup=team_name_to_ids_lookup,
        )
        self.logger = logging.getLogger('pyplaycricket.alleyn')
        # Set club-specific name-cleaning constants used by _clean_team_name in u.
        self.team_name_banned_words = alleyn_config.TEAM_NAME_BANNED_WORDS
        self.n_team_swap = alleyn_config.N_TEAM_SWAP

    # ------------------------------------------------------------------
    # Innings / scores
    # ------------------------------------------------------------------

    def get_innings_scores(self, match_ids: list | None = None):
        """
        Return team names and innings score strings for a set of matches.

        Args:
            match_ids (list, optional): Match IDs to include.

        Returns:
            tuple[str, str]: Newline-joined team names and score strings.
        """
        if match_ids is None:
            match_ids = []

        team_names = []
        innings_scores = []

        for match_id in match_ids:
            data = self._make_api_request(
                config.MATCH_DETAIL_URL.format(
                    match_id=match_id, api_key=self.api_key))
            data = data['match_details'][0]
            if data['result']:
                for innings in data['innings']:
                    team = self._clean_team_name(innings['team_batting_name'])
                    team_names.append(team.strip())

                    wickets = '' if innings['wickets'] == '10' else '-' + innings['wickets']
                    innings_scores.append(f"{innings['runs']}{wickets}")

        return '\n'.join(team_names), '\n'.join(innings_scores)

    # ------------------------------------------------------------------
    # Individual performances graphic
    # ------------------------------------------------------------------

    def get_individual_performances_for_graphic(
        self, match_ids: list | None = None, players_to_include: int = 3,
    ):
        """
        Build a fixed-width newline-delimited string of top batting and bowling
        performances per innings, suitable for the graphics pipeline.

        Args:
            match_ids (list, optional): Match IDs to process.
            players_to_include (int): Number of players to show per innings half.

        Returns:
            str: Formatted summary string.
        """
        if match_ids is None:
            match_ids = []

        stats_summary = ''
        for match_id in match_ids:
            self.logger.info(f'Processing match_id: {match_id}')
            bat, bowl = self.get_individual_stats(
                match_id=match_id, stat_string=True)

            for innings in sorted(bat['innings'].unique().tolist()):
                batn = bat.loc[bat['innings'] == innings]
                batn = batn.loc[batn['how_out'] != 'did not bat']
                batn = batn.sort_values(
                    ['runs', 'balls', 'not_out', 'position'],
                    ascending=[False, True, False, True],
                ).head(players_to_include)

                batting_names = [i.upper() for i in batn['initial_name'].tolist()]
                batting_stats = batn['stat'].tolist()
                batting_names, batting_stats = self._make_sure_number_of_players_is_consistent(
                    batting_names, batting_stats, players_to_include=players_to_include)
                stats_summary = self._add_to_stats_string(
                    stats_summary, batting_names, batting_stats)

                bowln = bowl.loc[bowl['innings'] == innings]
                bowln = bowln.loc[bowln['wickets'] > 0]
                bowln = bowln.sort_values(
                    ['wickets', 'runs', 'overs'], ascending=[False, True, False],
                ).head(players_to_include)

                bowling_names = [i.upper() for i in bowln['initial_name'].tolist()]
                bowling_stats = bowln['stat'].tolist()
                bowling_names, bowling_stats = self._make_sure_number_of_players_is_consistent(
                    bowling_names, bowling_stats, players_to_include=players_to_include)
                stats_summary = self._add_to_stats_string(
                    stats_summary, bowling_names, bowling_stats)

        return stats_summary

    def _add_to_stats_string(self, stats_summary: str, names_list: list, stats_list: list) -> str:
        """
        Append a block of names then stats to the running summary string.

        Args:
            stats_summary (str): Accumulated summary string so far.
            names_list (list): Player name strings to append.
            stats_list (list): Corresponding stat strings to append.

        Returns:
            str: Updated summary string.
        """
        stats_summary += '\n'.join(names_list) + '\n'
        stats_summary += '\n'.join(stats_list) + '\n'
        return stats_summary

    def _make_sure_number_of_players_is_consistent(
        self, names_list: list, stats_list: list, players_to_include: int,
    ) -> tuple:
        """
        Pad name and stat lists with blank entries to reach ``players_to_include``.

        Ensures downstream string formatting always receives fixed-length lists.

        Args:
            names_list (list): Player names.
            stats_list (list): Player stats.
            players_to_include (int): Target list length.

        Returns:
            tuple[list, list]: Padded ``(names_list, stats_list)``.
        """
        while len(names_list) < players_to_include:
            names_list.append(' ')
            stats_list.append(' ')
        return names_list, stats_list

    # ------------------------------------------------------------------
    # Result strings
    # ------------------------------------------------------------------

    def get_result_description_and_margin(self, match_ids: list, team_ids: list) -> str:
        """
        Build human-readable result lines for a set of matches.

        Example output: ``"1s Won by 47 runs\n"``.

        Args:
            match_ids (list): Match IDs to process.
            team_ids (list): IDs of the club's teams (used to determine perspective).

        Returns:
            str: Newline-terminated result strings concatenated together.
        """
        all_result_strings = ''
        for match_id in match_ids:
            self.logger.info(f'Match ID: {match_id}')
            data = self._make_api_request(
                config.MATCH_DETAIL_URL.format(
                    match_id=match_id, api_key=self.api_key))
            data = data['match_details'][0]

            team_name = (
                data['home_team_name']
                if int(data['home_team_id']) in team_ids
                else data['away_team_name']
            )
            result_letter = self._get_result_letter(data=data, team_ids=team_ids)
            result_string = team_name + ' ' + config.RESULTS_TEXT.get(result_letter or '', '')

            if result_letter == 'D':
                result_string = 'Match drawn'
            elif result_letter in config.NEUTRAL_RESULTS:
                pass
            elif data['batted_first'] == data['result_applied_to']:
                n_runs = int(data['innings'][0]['runs']) - int(data['innings'][1]['runs'])
                result_string += f' {n_runs} runs'
            else:
                n_wickets = 10 - int(data['innings'][1]['wickets'])
                result_string += f' {n_wickets} wickets'

            all_result_strings += result_string + '\n'

        return all_result_strings

    # ------------------------------------------------------------------
    # Match filtering
    # ------------------------------------------------------------------

    def get_weekend_matches(self, matches: pd.DataFrame, saturday: datetime) -> pd.DataFrame:
        """
        Filter a matches DataFrame to those played on a given Saturday or Sunday.

        Args:
            matches (pd.DataFrame): Full matches DataFrame.
            saturday (datetime): The Saturday date of the weekend to filter to.

        Returns:
            pd.DataFrame: Weekend matches ordered for display.
        """
        matches = matches.loc[
            matches['match_date'].isin([saturday, saturday + timedelta(days=1)])
        ].copy()
        return self.order_matches_for_the_graphics(matches=matches)

    # ------------------------------------------------------------------
    # Season lists
    # ------------------------------------------------------------------

    def get_season_opposition_list(self, matches: pd.DataFrame) -> str:
        """
        Return a newline-joined list of opposition team names for the season.

        Args:
            matches (pd.DataFrame): Matches DataFrame with ``home_club_name``
                and ``away_club_name`` columns.

        Returns:
            str: Newline-joined opposition names.
        """
        # Extract all team names from both columns in one vectorised pass.
        all_teams = matches[['home_club_name', 'away_club_name']].values.flatten().tolist()
        opposition = [
            self._clean_team_name(t) for t in all_teams if t not in self.team_names
        ]
        return '\n'.join(opposition)

    # ------------------------------------------------------------------
    # League table display
    # ------------------------------------------------------------------

    def get_cutout_off_league_table(self, league_table: pd.DataFrame, n_teams: int = 3) -> str:
        """
        Return a fixed-width string slice of the league table centred on the club.

        Args:
            league_table (pd.DataFrame): Full league table (must have POSITION,
                TEAM, W, D, L, PTS columns).
            n_teams (int, optional): Number of rows to include.  Defaults to 3.

        Returns:
            str: Newline-delimited table slice.

        Raises:
            AssertionError: If the table has fewer rows than ``n_teams``.
            Exception: If none of ``self.team_names`` appear in the table.
        """
        assert len(league_table) >= n_teams, "Not enough teams in the league"

        team_index = 1000
        for team in self.team_names:
            try:
                ti = [
                    i.split('-')[0].strip() for i in league_table['TEAM'].tolist()
                ].index(team)
            except ValueError:
                ti = 1000
            team_index = min(team_index, ti)

        if team_index == 1000:
            raise Exception(
                f"None of the teams ({','.join(self.team_names)}) in the league table")

        buffer = int((n_teams - 1) / 2)
        if team_index == 0 or n_teams == len(league_table):
            league_table = league_table.iloc[0:n_teams]
        else:
            league_table = league_table.iloc[
                max(team_index - buffer, 0):min(team_index + buffer + 1, len(league_table) + 1)
            ]

        league_table = league_table.copy()
        league_table['TEAM'] = league_table['TEAM'].apply(
            lambda x: self._clean_team_name(x))

        cols = ['POSITION', 'TEAM', 'W', 'D', 'L', 'PTS']
        return '\n'.join(str(v) for v in league_table[cols].values.flatten())

    # ------------------------------------------------------------------
    # Season stat totals
    # ------------------------------------------------------------------

    def get_alleyn_season_totals(
        self,
        match_ids: list,
        team_ids: list | None = None,
        group_by_team: bool = False,
        for_graphics: bool = False,
        n_players: int = 10,
    ):
        """
        Calculate season batting, bowling, and fielding totals for Alleyn CC teams.

        A thin wrapper around ``pc.get_stat_totals`` that defaults ``team_ids``
        to the club's registered team IDs.

        Args:
            match_ids (list): Match IDs to aggregate over.
            team_ids (list, optional): Defaults to ``self.team_ids``.
            group_by_team (bool, optional): Break stats down by team.
            for_graphics (bool, optional): Serialise output for the graphics pipeline.
            n_players (int, optional): Top-N player cutoff when ``for_graphics=True``.

        Returns:
            tuple: ``(batting, bowling, fielding)``
        """
        if not team_ids:
            team_ids = self.team_ids
        return self.get_stat_totals(
            match_ids=match_ids, team_ids=team_ids,
            group_by_team=group_by_team, for_graphics=for_graphics,
            n_players=n_players,
        )

    # ------------------------------------------------------------------
    # Individual performances
    # ------------------------------------------------------------------

    def get_best_individual_performances(
        self,
        match_ids: list,
        team_ids: list | None = None,
        n_players: int = 5,
        for_graphics: bool = False,
    ):
        """
        Return the best individual batting and bowling performances.

        Args:
            match_ids (list): Match IDs to search.
            team_ids (list, optional): Defaults to ``self.team_ids``.
            n_players (int, optional): Number of top performances to return.
            for_graphics (bool, optional): Serialise output for the graphics pipeline.

        Returns:
            tuple[pd.DataFrame | str, pd.DataFrame | str]: ``(batting, bowling)``
        """
        if not team_ids:
            team_ids = self.team_ids
        batting, bowling, _ = self.get_individual_stats_from_all_games(
            match_ids=match_ids, team_ids=team_ids, stat_string=True)

        if for_graphics:
            batting = self._get_individual_performance_title(
                batting)[config.INDIVIDUAL_PERFORMANCES_BATTING_COLUMNS].head(n_players)
            bowling = self._get_individual_performance_title(
                bowling)[config.INDIVIDUAL_PERFORMANCES_BOWLING_COLUMNS].head(n_players)
            batting = self._extract_string_for_graphic(batting)
            bowling = self._extract_string_for_graphic(bowling)

        return batting, bowling

    def _get_individual_performance_title(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add a ``title`` column in the form ``"JM Doe vs Opposition"`` to a stats DataFrame.

        Args:
            df (pd.DataFrame): DataFrame with ``initial_name`` and
                ``opposition_name`` columns.

        Returns:
            pd.DataFrame: DataFrame with ``title`` column added.
        """
        df['title'] = (
            df['initial_name'] + ' vs ' +
            df['opposition_name'].apply(lambda x: self._clean_team_name(x))
        )
        return df

    # ------------------------------------------------------------------
    # Players involved
    # ------------------------------------------------------------------

    def get_all_team_players_involved(
        self, match_ids: list, team_ids: list | None = None,
    ) -> pd.DataFrame:
        """
        Retrieve all players involved across matches, defaulting to club teams.

        Args:
            match_ids (list): Match IDs to query.
            team_ids (list, optional): Defaults to ``self.team_ids``.

        Returns:
            pd.DataFrame: Deduplicated player records.
        """
        if not team_ids:
            team_ids = self.team_ids
        return self.get_all_players_involved(match_ids=match_ids, team_ids=team_ids)
