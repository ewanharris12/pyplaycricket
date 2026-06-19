import pandas as pd
import logging
import numpy as np
from playcric import config
from playcric.utils import u


class pc(u):
    """
    Primary public API class for the Play-Cricket wrapper.

    Provides methods to retrieve match results, league tables, player stats,
    and innings data from the Play-Cricket API (play-cricket.com/api/v2).

    Inherits private helpers from ``u`` (utils).  Club-specific display logic
    lives in the ``acc`` subclass.

    Args:
        api_key (str): Play-Cricket API token.
        site_id (int): Default site ID used when none is passed to a method.
        team_names (list): Human-readable team names for this club.
        team_name_to_ids_lookup (dict): Mapping of team name → Play-Cricket team ID.
    """

    def __init__(
        self,
        api_key: str,
        site_id: int,
        team_names: list | None = None,
        team_name_to_ids_lookup: dict | None = None,
    ):
        super().__init__()
        self.api_key = api_key
        self.logger = logging.getLogger('pyplaycricket.playcricket')
        self.logger.info(f'Setting site_id as {site_id}')
        self.site_id = site_id
        self.team_names = team_names if team_names is not None else []
        self.team_name_to_ids_lookup = (
            team_name_to_ids_lookup if team_name_to_ids_lookup is not None else {}
        )
        self.team_ids = list(self.team_name_to_ids_lookup.values())
        self.team_ids_to_names_lookup = {
            v: k for k, v in self.team_name_to_ids_lookup.items()
        }

    # ------------------------------------------------------------------
    # Players
    # ------------------------------------------------------------------

    def list_registered_players(self, site_id: int = None):
        """
        Retrieve all registered players for a site.

        Args:
            site_id (int, optional): Site to query.  Falls back to
                ``self.site_id`` when not provided.

        Returns:
            pd.DataFrame: One row per registered player.
        """
        site_id = self._set_site_id(site_id)
        data = self._make_api_request(
            config.PLAYERS_URL.format(site_id=site_id, api_key=self.api_key))
        return pd.json_normalize(data['players'])

    # ------------------------------------------------------------------
    # Matches
    # ------------------------------------------------------------------

    def get_all_matches(
        self,
        season: int,
        team_ids: list | None = None,
        competition_ids: list | None = None,
        competition_types: list | None = None,
        site_id: int | None = None,
    ):
        """
        Retrieve all matches for a season, with optional filters.

        Args:
            season (int): Season year to fetch.
            team_ids (list, optional): Only return matches involving these teams.
            competition_ids (list, optional): Only return matches in these competitions.
            competition_types (list, optional): Only return matches of these types.
            site_id (int, optional): Site to query.  Falls back to ``self.site_id``.

        Returns:
            pd.DataFrame: One row per match.
        """
        if team_ids is None:
            team_ids = []
        if competition_ids is None:
            competition_ids = []
        if competition_types is None:
            competition_types = []

        self.logger.info(
            f'Getting all matches for season {season} with team_ids: {team_ids}, '
            f'competition_ids: {competition_ids}, competition_types: {competition_types}'
        )
        site_id = self._set_site_id(site_id)
        team_ids = self._convert_team_ids_to_ints(team_ids)
        data = self._make_api_request(
            config.MATCHES_URL.format(
                site_id=site_id, season=season, api_key=self.api_key))

        df = pd.json_normalize(data['matches'])
        if df.empty:
            return pd.DataFrame()

        for col in ['last_updated', 'match_date']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format='%d/%m/%Y')
        for col in ['competition_id']:
            df[col] = df[col].replace('', np.nan).astype('float')
        for col in ['home_team_id', 'away_team_id']:
            if col in df.columns:
                df[col] = df[col].astype('int')

        if team_ids:
            self.logger.info(f'Filtering to team_ids: {team_ids}')
            df = df.loc[
                (df['home_team_id'].isin(team_ids)) |
                (df['away_team_id'].isin(team_ids))
            ]
        if competition_ids:
            self.logger.info(f'Filtering to competition_ids: {competition_ids}')
            df = df.loc[df['competition_id'].isin(competition_ids)]
        if competition_types:
            self.logger.info(f'Filtering to competition_types: {competition_types}')
            df = df.loc[df['competition_type'].isin(competition_types)]

        return df

    # ------------------------------------------------------------------
    # League table
    # ------------------------------------------------------------------

    def get_league_table(self, competition_id: int, simple: bool = False, clean_names: bool = True) -> tuple:
        """
        Retrieve the league table for a division.

        Args:
            competition_id (int): Play-Cricket division/competition ID.
            simple (bool, optional): Collapse win-type variants into W/D/L.
                Defaults to False.
            clean_names (bool, optional): Strip club suffixes from team names.
                Defaults to True.

        Returns:
            tuple[pd.DataFrame, list]: The league table and the key list that
                describes the column headings.
        """
        data = self._make_api_request(
            config.LEAGUE_TABLE_URL.format(
                competition_id=competition_id, api_key=self.api_key))

        df = pd.json_normalize(data['league_table'][0]['values'])
        df.rename(columns=data['league_table'][0]['headings'], inplace=True)
        key = [
            i.replace('&nbsp;', '')
            for i in data['league_table'][0]['key'].split(',')
        ]
        df = self._clean_league_table(df=df, simple=simple)
        if clean_names:
            df['TEAM'] = df['TEAM'].apply(lambda x: self._clean_team_name(team=x))

        return df, key

    # ------------------------------------------------------------------
    # Match results
    # ------------------------------------------------------------------

    def get_match_result_string(self, match_id: int):
        """
        Return the raw result description text from the API for a match.

        Args:
            match_id (int): Play-Cricket match ID.

        Returns:
            str: Human-readable result description.
        """
        data = self._make_api_request(
            config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))
        return data['match_details'][0]['result_description']

    def get_result_for_my_team(self, match_id: int, team_ids: list | None = None):
        """
        Return the result code (W/L/D/etc.) from the perspective of the given teams.

        Args:
            match_id (int): Play-Cricket match ID.
            team_ids (list, optional): Team IDs to treat as "our" teams.

        Returns:
            str: Result code, e.g. ``'W'``, ``'L'``, ``'D'``.
        """
        team_ids = self._convert_team_ids_to_ints(team_ids)
        data = self._make_api_request(
            config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))
        data = data['match_details'][0]
        return self._get_result_letter(data=data, team_ids=team_ids)

    # ------------------------------------------------------------------
    # Players involved
    # ------------------------------------------------------------------

    def get_all_players_involved(self, match_ids: list, team_ids: list | None = None):
        """
        Retrieve deduplicated player records across a set of matches.

        Args:
            match_ids (list): Match IDs to query.
            team_ids (list, optional): If provided, restrict to players from
                these teams.

        Returns:
            pd.DataFrame: One row per unique player–match combination.
        """
        if team_ids is None:
            team_ids = []

        players = []
        for match_id in match_ids:
            try:
                self.logger.info(f'Getting players for match {match_id}')
                players.append(self._get_players_used_in_match(match_id=match_id))
            except Exception as e:
                self.logger.error(f'Error occurred while fetching players for match {match_id}: {e}')
        
        if not players:
            raise ValueError('No player data could be retrieved for the provided match IDs.')
        players = pd.concat(players)

        if team_ids:
            players = players.loc[players['team_id'].isin(team_ids)]

        players = players.drop_duplicates(
            subset=['player_name', 'player_id', 'match_id'])
        players.reset_index(inplace=True, drop=True)
        return players

    # ------------------------------------------------------------------
    # Match detail helpers
    # ------------------------------------------------------------------

    def _extract_match_team_context(self, data: dict) -> dict:
        """
        Extract a team-ID-to-name lookup and ordered ID list from match detail data.

        This avoids duplicating the same four lines in every method that reads
        match detail responses.

        Args:
            data (dict): The ``match_details[0]`` dict from the API response.

        Returns:
            dict: ``{'all_ids': [home_id, away_id],
                     'team_name_lookup': {id: name, ...}}``
        """
        home_id = self._normalise_id(data['home_team_id'])
        away_id = self._normalise_id(data['away_team_id'])
        all_ids = [home_id, away_id]
        team_name_lookup = {
            home_id: data['home_club_name'] + ' - ' + data['home_team_name'],
            away_id: data['away_club_name'] + ' - ' + data['away_team_name'],
        }
        return {'all_ids': all_ids, 'team_name_lookup': team_name_lookup}

    def get_innings_total_scores(self, match_id: int):
        """
        Retrieve innings-level totals (runs, wickets, etc.) for a match.

        Args:
            match_id (int): Play-Cricket match ID.

        Returns:
            pd.DataFrame: One row per innings with summary scores.
        """
        data = self._make_api_request(
            config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))
        inn = pd.json_normalize(data['match_details'][0]['innings'])
        inn = inn.drop(
            columns=['bat', 'fow', 'bowl', 'innings_number'], errors='ignore',
        ).reset_index()
        inn['match_id'] = match_id
        inn['index'] += 1
        inn.rename(columns={'index': 'innings_number'}, inplace=True)
        inn.dropna(axis=0, how='all', inplace=True)
        return inn

    def get_match_partnerships(self, match_id: int):
        """
        Retrieve fall-of-wicket partnership data for each innings of a match.

        The ``score_added`` column is computed per innings (not across the
        whole match), so the first wicket of each innings always shows the
        runs scored from the start of that innings.

        Args:
            match_id (int): Play-Cricket match ID.

        Returns:
            pd.DataFrame: One row per wicket with partnership details.
        """
        data = self._make_api_request(
            config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))
        data = data['match_details'][0]
        ctx = self._extract_match_team_context(data)
        all_ids = ctx['all_ids']
        team_name_lookup = ctx['team_name_lookup']

        innings_number = 1
        partnerships = []
        for innings in data['innings']:
            p = pd.json_normalize(innings['fow'])
            batting_id = self._normalise_id(innings['team_batting_id'])
            batting_name = innings['team_batting_name']
            bowling_id = all_ids[1] if batting_id == all_ids[0] else all_ids[0]
            bowling_name = team_name_lookup.get(bowling_id)

            p = self._add_team_name_id_and_innings(
                p, batting_name, batting_id, bowling_name, bowling_id,
                innings_number, match_id,
            )
            partnerships.append(p)
            innings_number += 1

        partnerships = pd.concat(partnerships)
        if not partnerships.empty:
            partnerships['runs'] = np.where(
                partnerships['runs'] == '', None, partnerships['runs'])
            runs_int = partnerships['runs'].fillna(0).astype('int')
            # Shift within each innings so the first wicket of each innings
            # is not compared against the last wicket of the previous innings.
            shifted = (
                runs_int.groupby(partnerships['innings']).shift(1).fillna(0).astype('int')
            )
            partnerships['score_added'] = runs_int - shifted
        else:
            partnerships['score_added'] = None

        return partnerships

    # ------------------------------------------------------------------
    # Individual stats
    # ------------------------------------------------------------------

    def get_individual_stats(self, match_id: int, team_ids: list | None = None, stat_string: bool = False):
        """
        Retrieve batting and bowling statistics for a single match.

        Args:
            match_id (int): Play-Cricket match ID.
            team_ids (list, optional): If provided, restrict results to these teams.
            stat_string (bool, optional): If True, add a formatted ``stat``
                column to each DataFrame.  Defaults to False.

        Returns:
            tuple[pd.DataFrame, pd.DataFrame]: ``(batting, bowling)`` DataFrames.
                Empty DataFrames with the standard schema are returned when no
                innings data is available.
        """
        if team_ids is None:
            team_ids = []

        data = self._make_api_request(
            config.MATCH_DETAIL_URL.format(match_id=match_id, api_key=self.api_key))
        data = data['match_details'][0]
        ctx = self._extract_match_team_context(data)
        all_ids = ctx['all_ids']
        team_name_lookup = ctx['team_name_lookup']

        all_batting = []
        all_bowling = []

        innings_number = 1
        for innings in data['innings']:
            bat = pd.json_normalize(innings['bat'])
            if bat.empty:
                continue
            batting_id = self._normalise_id(innings['team_batting_id'])
            batting_name = innings['team_batting_name']
            bowling_id = all_ids[1] if batting_id == all_ids[0] else all_ids[0]
            bowling_name = team_name_lookup.get(bowling_id)

            bowl = pd.json_normalize(innings['bowl'])
            if bowl.empty:
                continue

            bowl = self._add_team_name_id_and_innings(
                bowl, bowling_name, bowling_id, batting_name, batting_id,
                innings_number, match_id,
            )
            bat = self._add_team_name_id_and_innings(
                bat, batting_name, batting_id, bowling_name, bowling_id,
                innings_number, match_id,
            )
            all_batting.append(bat)
            all_bowling.append(bowl)
            innings_number += 1

        if len(all_batting) == 0:
            return (
                pd.DataFrame(columns=config.STANDARD_BATTING_COLS),
                pd.DataFrame(columns=config.STANDARD_BOWLING_COLS),
            )

        all_batting = self._standardise_bat(pd.concat(all_batting))
        all_bowling = self._standardise_bowl(pd.concat(all_bowling))

        if team_ids:
            all_batting = all_batting.loc[all_batting['team_id'].isin(team_ids)]
            all_bowling = all_bowling.loc[all_bowling['team_id'].isin(team_ids)]

        if stat_string:
            all_batting['stat'] = all_batting.apply(
                lambda row: self._write_batting_string(row), axis=1)
            all_bowling['stat'] = all_bowling.apply(
                lambda row: self._write_bowling_string(row), axis=1)

        return all_batting, all_bowling

    def get_individual_stats_from_all_games(
        self, match_ids: list, team_ids: list | None = None, stat_string: bool = False,
    ):
        """
        Collect individual batting, bowling, and fielding stats across multiple matches.

        Fielding data is derived from the batting DataFrames of the opposition
        (the ``fielder_name`` and ``fielder_id`` columns record the fielder
        who took the dismissal).

        Args:
            match_ids (list): Match IDs to include.
            team_ids (list, optional): If provided, batting/bowling are filtered
                to these teams and fielding to their opposition.
            stat_string (bool, optional): Passed through to ``get_individual_stats``.

        Returns:
            tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
                ``(batting, bowling, fielding)``

        Raises:
            ValueError: If fetching stats for any match ID fails.
        """
        if team_ids is None:
            team_ids = []

        batting_frames: list[pd.DataFrame] = []
        bowling_frames: list[pd.DataFrame] = []
        for match_id in match_ids:
            try:
                bat, bowl = self.get_individual_stats(
                    match_id=match_id, stat_string=stat_string)
            except Exception as e:
                raise ValueError(f'MATCH ID {match_id} FAILED WITH: {e}')
            batting_frames.append(bat)
            bowling_frames.append(bowl)

        batting = pd.concat(batting_frames)
        bowling = pd.concat(bowling_frames)
        bowling['wickets'] = bowling['wickets'].fillna(0).astype('int')

        # Fielding is drawn from the opposition's batting records (which carry
        # fielder_name/fielder_id for each dismissal).
        if team_ids:
            fielding = batting.loc[~batting['team_id'].isin(team_ids)].copy()
            batting = batting.loc[batting['team_id'].isin(team_ids)]
            bowling = bowling.loc[bowling['team_id'].isin(team_ids)]
        else:
            fielding = batting.copy()

        batting.sort_values(['runs', 'balls'], ascending=[False, True], inplace=True)
        bowling.sort_values(
            ['wickets', 'runs', 'balls'], ascending=[False, True, True], inplace=True)

        batting.reset_index(inplace=True, drop=True)
        fielding.reset_index(inplace=True, drop=True)
        bowling.reset_index(inplace=True, drop=True)

        return batting, bowling, fielding

    # ------------------------------------------------------------------
    # Season aggregates
    # ------------------------------------------------------------------

    def get_stat_totals(
        self,
        match_ids: list,
        team_ids: list = None,
        group_by_team: bool = False,
        for_graphics: bool = False,
        n_players: int = 10,
    ):
        """
        Return aggregated batting, bowling, and fielding totals for a set of matches.

        Args:
            match_ids (list): Match IDs to include.
            team_ids (list, optional): Teams to include.
            group_by_team (bool, optional): Break stats down by team as well as player.
            for_graphics (bool, optional): If True, truncate to ``n_players`` and
                serialise each DataFrame to a newline-delimited string.
            n_players (int, optional): Player count limit when ``for_graphics=True``.

        Returns:
            tuple[pd.DataFrame | str, ...]: ``(batting, bowling, fielding)``
        """
        if team_ids is None:
            team_ids = []

        batting, bowling, fielding = self.get_individual_stats_from_all_games(
            match_ids, team_ids, stat_string=False)

        batting, bowling, fielding = self.aggregate_stats(
            group_by_team, batting, bowling, fielding)

        if for_graphics:
            batting = batting[config.STATS_TOTALS_BATTING_COLUMNS].head(n_players)
            bowling = bowling[config.STATS_TOTALS_BOWLING_COLUMNS].head(n_players)
            fielding = fielding[config.STATS_TOTALS_FIELDING_COLUMNS].head(n_players)

            batting = self._extract_string_for_graphic(batting)
            bowling = self._extract_string_for_graphic(bowling)
            fielding = self._extract_string_for_graphic(fielding)

        return batting, bowling, fielding

    def aggregate_stats(self, group_by_team, batting, bowling, fielding):
        """
        Dispatch raw per-match DataFrames to the three aggregation helpers.

        Args:
            group_by_team (bool): Include team ID in the groupby keys.
            batting (pd.DataFrame): Row-level batting data.
            bowling (pd.DataFrame): Row-level bowling data.
            fielding (pd.DataFrame): Row-level fielding data (derived from batting).

        Returns:
            tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
                Aggregated ``(batting, bowling, fielding)``.
        """
        batting_groupby = ['initial_name', 'batsman_name', 'batsman_id']
        bowling_groupby = ['initial_name', 'bowler_name', 'bowler_id']
        fielding_groupby = ['fielder_name', 'fielder_id']
        if group_by_team:
            batting_groupby += ['team_id']
            bowling_groupby += ['team_id']
            fielding_groupby += ['team_id']

        batting = self._aggregate_batting_stats(batting, batting_groupby)
        bowling = self._aggregate_bowling_stats(bowling, bowling_groupby)
        fielding = self._aggregate_fielding_stats(fielding, fielding_groupby)
        return batting, bowling, fielding

    # ------------------------------------------------------------------
    # Display / ordering
    # ------------------------------------------------------------------

    def _extract_string_for_graphic(self, df: pd.DataFrame) -> str:
        """
        Serialise every cell of a DataFrame to a newline-delimited string.

        Cells are written row-by-row, column-by-column, each on its own line.
        This format is consumed by the graphics pipeline.

        Args:
            df (pd.DataFrame): DataFrame to serialise.

        Returns:
            str: Newline-delimited string of all cell values.
        """
        return '\n'.join(str(v) for v in df.values.flatten()) + '\n'

    def order_matches_for_the_graphics(self, matches: pd.DataFrame):
        """
        Add a ``club_team_name`` column and sort matches for display.

        Args:
            matches (pd.DataFrame): Matches DataFrame (must include
                ``home_team_id``, ``away_team_id``, and ``match_date``).

        Returns:
            pd.DataFrame: Sorted matches with ``club_team_name`` column.

        Raises:
            ValueError: If ``self.team_ids`` has not been set.
        """
        if self.team_ids is None:
            raise ValueError(
                'Please set the team_ids attribute before calling this method.')
        matches['club_team_name'] = np.where(
            matches['home_team_id'].isin(self.team_ids),
            matches['home_team_id'].apply(
                lambda x: self.team_ids_to_names_lookup.get(int(x))),
            matches['away_team_id'].apply(
                lambda x: self.team_ids_to_names_lookup.get(int(x))),
        )
        matches.sort_values(
            ['match_date', 'club_team_name'], ascending=True, inplace=True)
        return matches
