import logging
import requests
import pandas as pd
import numpy as np
import math

from playcric import config

module_logger = logging.getLogger('pyplaycricket')


# ---------------------------------------------------------------------------
# Module-level aggregation helpers used in groupby calls.
# Using named functions instead of lambdas ensures that the resulting column
# names are stable across pandas versions (lambda names like "<lambda_0>"
# can change).
# ---------------------------------------------------------------------------

def _count_five_fers(x):
    """Return the number of five-wicket hauls in a wickets Series."""
    return (x >= 5).sum()


def _count_fifties(x):
    """Return the number of half-centuries (50–99) in a runs Series."""
    return x[(x >= 50) & (x < 100)].count()


def _count_hundreds(x):
    """Return the number of centuries (100+) in a runs Series."""
    return x[x >= 100].count()


class u():
    """
    Base utility class for the Play-Cricket API wrapper.

    Provides private helper methods shared across the public API class (pc)
    and the club-specific subclass (acc).  Should not be instantiated
    directly — use pc or a subclass instead.
    """

    def __init__(self):
        self.logger = logging.getLogger('pyplaycricket.utils')
        # Declared here so type checkers recognise the attribute; set by pc.__init__.
        self.api_key: str = ''
        # Subclasses may override these to enable club-specific name cleaning.
        self.team_name_banned_words: list = []
        self.n_team_swap: list = []

    # ------------------------------------------------------------------
    # ID normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_id(value) -> int | None:
        """
        Coerce an API ID value to int, returning None for empty/null values.

        Args:
            value: Raw ID value from the API response (str, int, or None).

        Returns:
            int if value is non-empty, otherwise None.
        """
        if value in (None, ''):
            return None
        return int(value)

    # ------------------------------------------------------------------
    # Site / team helpers
    # ------------------------------------------------------------------

    def _set_site_id(self, site_id):
        """Return site_id if provided, otherwise fall back to self.site_id."""
        if site_id is None:
            site_id = self.site_id
        return site_id

    def _convert_team_ids_to_ints(self, team_ids):
        """
        Convert a list of team IDs to integers.

        Args:
            team_ids (list | None): A list of team IDs, or None.

        Returns:
            list[int]: Team IDs as integers, or an empty list if None was passed.
        """
        if team_ids is None:
            return []
        return [int(i) for i in team_ids]

    # ------------------------------------------------------------------
    # DataFrame mutation helpers
    # ------------------------------------------------------------------

    def _add_team_name_id_and_innings(
        self, df, team_name, team_id, opposition_name, opposition_id,
        innings_number, match_id,
    ):
        """
        Attach match-context columns to a batting or bowling DataFrame.

        Args:
            df (pd.DataFrame): DataFrame to annotate (mutated in place).
            team_name (str): Name of the batting/bowling team.
            team_id (int): ID of the batting/bowling team.
            opposition_name (str): Name of the opposition.
            opposition_id (int): ID of the opposition.
            innings_number (int): Innings sequence number within the match.
            match_id (int): ID of the match.

        Returns:
            pd.DataFrame: The same DataFrame with extra columns added.
        """
        df['team_name'] = team_name
        df['team_id'] = team_id
        df['opposition_name'] = opposition_name
        df['opposition_id'] = opposition_id
        df['innings'] = innings_number
        df['match_id'] = match_id
        return df

    def _clean_column_names(self, x):
        """
        Flatten a two-level column tuple produced by a groupby aggregation.

        Args:
            x (tuple): A (column_name, aggregation_label) tuple.

        Returns:
            str: ``column_name`` if the label is empty, otherwise
                 ``column_name_aggregation_label``.
        """
        if x[1] == '':
            return x[0]
        return x[0] + '_' + x[1]

    # ------------------------------------------------------------------
    # String formatting helpers
    # ------------------------------------------------------------------

    def _write_bowling_string(self, row):
        """
        Format a bowling figure as ``wickets-runs``.

        Args:
            row (dict): Row with ``wickets`` and ``runs`` keys.

        Returns:
            str: e.g. ``"3-42"``.
        """
        return f'{row["wickets"]}-{row["runs"]}'

    def _write_batting_string(self, row):
        """
        Format a batting score as ``runs*(balls)``.

        A ``*`` suffix denotes a not-out score.  Balls are omitted when zero.

        Args:
            row (dict): Row with ``runs``, ``not_out``, and ``balls`` keys.

        Returns:
            str: e.g. ``"45*(62)"`` or ``"30"``.
        """
        not_out = row['not_out'] == 1
        no_string = '*' if not_out else ''
        if row['balls'] > 0:
            return f"{row['runs']}{no_string}({row['balls']})"
        return f"{row['runs']}{no_string}"

    def _get_initials_surname(self, name):
        """
        Convert a full name to initials + surname.

        Args:
            name (str): Full name, e.g. ``"John Michael Doe"``.

        Returns:
            str | None: ``"JM Doe"``, or None if the name is blank.
        """
        if not name.replace(' ', ''):
            return None
        parts = name.split(' ')
        if len(parts) == 1:
            return parts[0]
        initials = ''.join(p[0] for p in parts[:-1])
        return f'{initials} {parts[-1]}'

    # ------------------------------------------------------------------
    # Data standardisation
    # ------------------------------------------------------------------

    def _standardise_bowl(self, bowl):
        """
        Coerce column types and add derived columns to a bowling DataFrame.

        Adds ``initial_name`` (initials + surname) and ``balls`` (converted
        from the overs string).  Returns an empty DataFrame with the standard
        schema if the input is empty.

        Args:
            bowl (pd.DataFrame): Raw bowling data from the API.

        Returns:
            pd.DataFrame: Standardised bowling DataFrame.
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
        return bowl

    def _standardise_bat(self, bat):
        """
        Coerce column types and add derived columns to a batting DataFrame.

        Sets ``not_out`` (1 if batter was not out, 0 otherwise) and adds
        ``initial_name``.  Returns an empty DataFrame with the standard schema
        if the input is empty.

        Args:
            bat (pd.DataFrame): Raw batting data from the API.

        Returns:
            pd.DataFrame: Standardised batting DataFrame.
        """
        if not bat.empty:
            bat['not_out'] = np.where(
                bat['how_out'].isin(['not out', 'retired not out', 'did not bat']),
                1, 0,
            )
            for col in ['runs', 'fours', 'sixes', 'balls', 'position']:
                bat[col] = bat[col].replace('', '0').astype('int')
            bat['initial_name'] = bat['batsman_name'].apply(
                lambda x: self._get_initials_surname(x))
        else:
            self.logger.info('No batting')
            bat = pd.DataFrame(columns=config.STANDARD_BATTING_COLS)
        return bat

    # ------------------------------------------------------------------
    # Result helpers
    # ------------------------------------------------------------------

    def _get_result_letter(self, data, team_ids):
        """
        Return the result code from the perspective of the supplied teams.

        Swaps W↔L when the result was applied to the opposing team.

        Args:
            data (dict): Match detail dictionary from the API.
            team_ids (list[int]): IDs of the teams whose perspective to use.

        Returns:
            str: Result code, e.g. ``'W'``, ``'L'``, ``'D'``.
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

    # ------------------------------------------------------------------
    # League table
    # ------------------------------------------------------------------

    def _clean_league_table(self, df, simple):
        """
        Normalise a raw league table DataFrame.

        Uppercases column names, coerces win/draw/loss columns to int, and
        optionally collapses variant win/draw/loss types into single W/D/L
        columns.

        Args:
            df (pd.DataFrame): Raw league table from the API.
            simple (bool): If True, collapse win-type variants into W/D/L.

        Returns:
            pd.DataFrame: Cleaned league table.
        """
        df.columns = [i.upper() for i in df.columns]
        wins = config.LEAGUE_TABLE_WIN_TYPES
        draws = config.LEAGUE_TABLE_DRAW_TYPES
        losses = config.LEAGUE_TABLE_LOSS_TYPES

        for col in wins + draws + losses:
            if col in df.columns:
                df[col] = df[col].astype('int')
            else:
                df[col] = 0

        if simple:
            df['wins'] = df[wins].sum(axis=1).astype('int')
            df['draws'] = df[draws].sum(axis=1).astype('int')
            df['losses'] = df[losses].sum(axis=1).astype('int')
            df = df[['POSITION', 'TEAM', 'wins', 'draws', 'losses', 'PTS']].rename(
                columns={'wins': 'W', 'draws': 'D', 'losses': 'L'})

        return df

    # ------------------------------------------------------------------
    # Name cleaning
    # ------------------------------------------------------------------

    def _clean_team_name(self, team: str) -> str:
        """
        Strip club-specific suffixes and banned words from a team name.

        Uses ``self.n_team_swap`` and ``self.team_name_banned_words``, which
        are set to club-specific values by subclasses (e.g. acc).

        Args:
            team (str): Raw team name from the API.

        Returns:
            str: Cleaned team name.
        """
        if team.split(' - ')[0] in self.team_names:
            team = team.split(' - ')[0]
        else:
            for nth_team in self.n_team_swap:
                team = team.replace(nth_team, 's')
            for banned_word in self.team_name_banned_words:
                team = team.replace(banned_word, '')
        return ' '.join(team.split())

    # ------------------------------------------------------------------
    # API request
    # ------------------------------------------------------------------

    def _make_api_request(self, url):
        """
        Issue an authenticated GET request and return the JSON response.

        Args:
            url (str): Full API URL including the api_token parameter.

        Returns:
            dict: Parsed JSON response body.

        Raises:
            Exception: If the server returns a non-200 status code.
        """
        self.logger.info(f'Making request to: {url}')
        req = requests.get(url)
        self.logger.info(f'Req response: {req.status_code}')
        if req.status_code != 200:
            raise Exception(f'ERROR ({req.status_code}): {req.reason}')
        return req.json()

    # ------------------------------------------------------------------
    # Overs / balls conversion
    # ------------------------------------------------------------------

    def _count_balls(self, overs_string):
        """
        Convert an overs string to a total ball count.

        Args:
            overs_string (str): Overs in ``"O.B"`` format, e.g. ``"4.2"``.

        Returns:
            int: Total balls bowled, e.g. ``26`` for ``"4.2"``.
        """
        parts = overs_string.split('.')
        if len(parts) == 0:
            return None
        if len(parts) == 1:
            parts += [0]

        overs = int(parts[0]) if parts[0] != '' else 0
        balls = int(parts[1]) if len(parts) > 1 and parts[1] != '' else 0
        return (overs * 6) + balls

    def _calculate_overs(self, ball_count):
        """
        Convert a total ball count back to an overs string.

        Args:
            ball_count (int): Total number of balls.

        Returns:
            str: Overs in ``"O.B"`` format, e.g. ``"4.1"`` for 25 balls.

        Example:
            >>> self._calculate_overs(25)
            '4.1'
        """
        overs = math.floor(ball_count / 6)
        balls = int(ball_count - (overs * 6))
        return f'{overs}.{balls}'

    # ------------------------------------------------------------------
    # Player retrieval
    # ------------------------------------------------------------------

    def _get_players_used_in_match(self, match_id: int):
        """
        Retrieve all players listed for both teams in a match.

        Args:
            match_id (int): The Play-Cricket match ID.

        Returns:
            pd.DataFrame: Combined home and away player records with
                ``team_id``, ``club_id``, and ``match_id`` columns added.
        """
        data = self._make_api_request(
            config.MATCH_DETAIL_URL.format(
                match_id=match_id, api_key=self.api_key))

        detail = data['match_details'][0]

        home_t = pd.json_normalize(detail['players'][0]['home_team'])
        home_t['team_id'] = self._normalise_id(detail['home_team_id'])
        home_t['club_id'] = self._normalise_id(detail['home_club_id'])

        away_t = pd.json_normalize(detail['players'][1]['away_team'])
        away_t['team_id'] = self._normalise_id(detail['away_team_id'])
        away_t['club_id'] = self._normalise_id(detail['away_club_id'])

        teams = pd.concat([home_t, away_t]).reset_index(drop=True)
        teams['match_id'] = match_id
        return teams

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------

    def _aggregate_fielding_stats(self, fielding, fielding_groupby):
        """
        Aggregate fielding data to dismissal and game counts per player.

        Args:
            fielding (pd.DataFrame): Row-level fielding data (derived from batting).
            fielding_groupby (list[str]): Columns to group by.

        Returns:
            pd.DataFrame: Aggregated fielding stats with a ``rank`` column.
        """
        fielding = fielding.groupby(
            fielding_groupby, as_index=False,
        ).agg({'match_id': ['count', pd.Series.nunique]})
        fielding.columns = [self._clean_column_names(col) for col in fielding.columns]
        fielding.rename(
            columns={'match_id_count': 'dismissals', 'match_id_nunique': 'n_games'},
            inplace=True,
        )
        fielding.sort_values(
            ['dismissals', 'n_games'], ascending=[False, True], inplace=True)
        fielding.dropna(subset=['fielder_name'], inplace=True)
        fielding = fielding.loc[fielding['fielder_name'] != '']
        fielding = (
            fielding.reset_index(drop=True)
            .reset_index()
            .rename(columns={'index': 'rank'})
        )
        fielding['rank'] += 1
        return fielding

    def _aggregate_bowling_stats(self, bowling, bowling_groupby):
        """
        Aggregate bowling data to season totals per player.

        Calculates wickets, overs, average, strike rate, and economy.
        Uses named aggregation functions so column names are stable across
        pandas versions.

        Args:
            bowling (pd.DataFrame): Row-level bowling data.
            bowling_groupby (list[str]): Columns to group by.

        Returns:
            pd.DataFrame: Aggregated bowling stats with a ``rank`` column.
        """
        bowling = bowling.groupby(bowling_groupby, as_index=False).agg(
            {
                'wickets': ['sum', 'max', _count_five_fers],
                'balls': 'sum',
                'maidens': 'sum',
                'runs': 'sum',
                'match_id': pd.Series.nunique,
            }
        )
        bowling.columns = [self._clean_column_names(col) for col in bowling.columns]
        bowling.rename(
            columns={
                'wickets_sum': 'wickets',
                'wickets_max': 'max_wickets',
                'wickets__count_five_fers': '5fers',
            },
            inplace=True,
        )
        for agg in config.GROUPBY_AGGS:
            bowling.columns = [col.replace(agg, '') for col in bowling.columns]

        bowling = (
            bowling.sort_values(
                ['wickets', 'runs', 'balls', 'match_id'],
                ascending=[False, True, True, True],
            )
            .reset_index(drop=True)
            .reset_index()
            .rename(columns={'index': 'rank'})
        )
        bowling['overs'] = bowling['balls'].apply(lambda x: self._calculate_overs(x))
        bowling['average'] = bowling['runs'] / bowling['wickets'].replace(0, pd.NA)
        bowling['sr'] = bowling['balls'] / bowling['wickets'].replace(0, pd.NA)
        bowling['econ'] = (bowling['runs'] / bowling['balls']) * 6
        bowling['rank'] += 1
        return bowling

    def _aggregate_batting_stats(self, batting, batting_groupby):
        """
        Aggregate batting data to season totals per player.

        Calculates runs, average, top score, fifties, and centuries.
        The batting average is computed vectorially (runs / dismissal innings).

        Args:
            batting (pd.DataFrame): Row-level batting data.
            batting_groupby (list[str]): Columns to group by.

        Returns:
            pd.DataFrame: Aggregated batting stats with a ``rank`` column.
        """
        batting = batting.loc[batting['how_out'] != 'did not bat']
        batting = batting.groupby(batting_groupby, as_index=False).agg(
            {
                'runs': ['sum', 'max', _count_fifties, _count_hundreds],
                'fours': 'sum',
                'sixes': 'sum',
                'balls': 'sum',
                'not_out': 'sum',
                'match_id': pd.Series.nunique,
                'position': 'mean',
            }
        )
        batting.columns = [self._clean_column_names(col) for col in batting.columns]
        batting.rename(
            columns={
                'runs_sum': 'runs',
                'runs_max': 'top_score',
                'runs__count_fifties': '50s',
                'runs__count_hundreds': '100s',
            },
            inplace=True,
        )
        for agg in config.GROUPBY_AGGS:
            batting.columns = [col.replace(agg, '') for col in batting.columns]

        batting['innings_to_count'] = batting['match_id'] - batting['not_out']
        # Vectorised average: divide runs by dismissal innings; result is NaN
        # (not None) when innings_to_count is 0.
        batting['average'] = (
            batting['runs'] / batting['innings_to_count'].replace(0, pd.NA)
        )
        batting = (
            batting.sort_values(
                ['runs', 'average', 'balls', 'fours', 'sixes'],
                ascending=[False, False, True, False, False],
            )
            .reset_index(drop=True)
            .reset_index()
            .rename(columns={'index': 'rank'})
        )
        batting['rank'] += 1
        return batting
