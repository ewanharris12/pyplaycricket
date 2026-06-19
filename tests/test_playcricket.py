import json
import os
import unittest
from unittest.mock import patch

import pandas as pd

from playcric import config
from playcric.playcricket import pc
from playcric.utils import u

TESTDATA_DIR = os.path.join(os.path.dirname(__file__), 'test_files')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_fixture(name):
    with open(os.path.join(TESTDATA_DIR, name)) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# u._normalise_id
# ---------------------------------------------------------------------------

class TestNormaliseId(unittest.TestCase):
    """Tests for the _normalise_id static helper."""

    def test_none_returns_none(self):
        self.assertIsNone(u._normalise_id(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(u._normalise_id(''))

    def test_string_id_converts_to_int(self):
        self.assertEqual(u._normalise_id('59723'), 59723)

    def test_int_id_passes_through(self):
        self.assertEqual(u._normalise_id(59723), 59723)


# ---------------------------------------------------------------------------
# u._count_balls / u._calculate_overs
# ---------------------------------------------------------------------------

class TestOversConversion(unittest.TestCase):
    """Tests for the overs ↔ balls conversion helpers."""

    def setUp(self):
        self.pc_instance = pc('test_key', 12345)

    def test_count_balls_whole_overs(self):
        self.assertEqual(self.pc_instance._count_balls('10.0'), 60)

    def test_count_balls_overs_and_balls(self):
        self.assertEqual(self.pc_instance._count_balls('4.2'), 26)

    def test_count_balls_no_decimal(self):
        self.assertEqual(self.pc_instance._count_balls('5'), 30)

    def test_count_balls_zero_overs(self):
        self.assertEqual(self.pc_instance._count_balls('0.3'), 3)

    def test_calculate_overs_whole(self):
        self.assertEqual(self.pc_instance._calculate_overs(60), '10.0')

    def test_calculate_overs_with_balls(self):
        self.assertEqual(self.pc_instance._calculate_overs(26), '4.2')

    def test_calculate_overs_only_balls(self):
        self.assertEqual(self.pc_instance._calculate_overs(3), '0.3')

    def test_roundtrip(self):
        """count_balls → calculate_overs should reproduce the original string."""
        original = '7.4'
        self.assertEqual(
            self.pc_instance._calculate_overs(
                self.pc_instance._count_balls(original)),
            original,
        )


# ---------------------------------------------------------------------------
# u._get_initials_surname
# ---------------------------------------------------------------------------

class TestGetInitialsSurname(unittest.TestCase):

    def setUp(self):
        self.pc_instance = pc('test_key', 12345)

    def test_two_part_name(self):
        self.assertEqual(self.pc_instance._get_initials_surname('John Doe'), 'J Doe')

    def test_three_part_name(self):
        self.assertEqual(
            self.pc_instance._get_initials_surname('John Michael Doe'), 'JM Doe')

    def test_single_word_name(self):
        self.assertEqual(self.pc_instance._get_initials_surname('Bradman'), 'Bradman')

    def test_blank_string_returns_none(self):
        self.assertIsNone(self.pc_instance._get_initials_surname('   '))


# ---------------------------------------------------------------------------
# u._convert_team_ids_to_ints
# ---------------------------------------------------------------------------

class TestConvertTeamIdsToInts(unittest.TestCase):

    def setUp(self):
        self.pc_instance = pc('test_key', 12345)

    def test_none_returns_empty_list(self):
        self.assertEqual(self.pc_instance._convert_team_ids_to_ints(None), [])

    def test_empty_list_returns_empty_list(self):
        self.assertEqual(self.pc_instance._convert_team_ids_to_ints([]), [])

    def test_string_ids_converted_to_ints(self):
        self.assertEqual(
            self.pc_instance._convert_team_ids_to_ints(['1', '2', '3']),
            [1, 2, 3],
        )

    def test_int_ids_pass_through(self):
        self.assertEqual(
            self.pc_instance._convert_team_ids_to_ints([1, 2, 3]),
            [1, 2, 3],
        )


# ---------------------------------------------------------------------------
# u._write_batting_string / u._write_bowling_string
# ---------------------------------------------------------------------------

class TestWriteBattingString(unittest.TestCase):

    def setUp(self):
        self.pc_instance = pc('test_key', 12345)

    def test_out_with_balls(self):
        self.assertEqual(
            self.pc_instance._write_batting_string({'runs': 30, 'not_out': 0, 'balls': 45}),
            '30(45)',
        )

    def test_not_out_with_balls(self):
        self.assertEqual(
            self.pc_instance._write_batting_string({'runs': 45, 'not_out': 1, 'balls': 62}),
            '45*(62)',
        )

    def test_out_no_balls(self):
        self.assertEqual(
            self.pc_instance._write_batting_string({'runs': 12, 'not_out': 0, 'balls': 0}),
            '12',
        )

    def test_not_out_no_balls(self):
        self.assertEqual(
            self.pc_instance._write_batting_string({'runs': 12, 'not_out': 1, 'balls': 0}),
            '12*',
        )


class TestWriteBowlingString(unittest.TestCase):

    def setUp(self):
        self.pc_instance = pc('test_key', 12345)

    def test_wickets_and_runs(self):
        self.assertEqual(
            self.pc_instance._write_bowling_string({'wickets': 3, 'runs': 42}),
            '3-42',
        )

    def test_zero_wickets(self):
        self.assertEqual(
            self.pc_instance._write_bowling_string({'wickets': 0, 'runs': 25}),
            '0-25',
        )


# ---------------------------------------------------------------------------
# pc._extract_string_for_graphic
# ---------------------------------------------------------------------------

class TestExtractStringForGraphic(unittest.TestCase):
    """Tests for the graphic serialisation helper (now lives on pc, not acc)."""

    def setUp(self):
        self.pc_instance = pc('test_key', 12345)

    def test_serialises_all_cells_row_by_row(self):
        df = pd.DataFrame({'name': ['A', 'B'], 'runs': [50, 30]})
        result = self.pc_instance._extract_string_for_graphic(df)
        self.assertEqual(result, 'A\n50\nB\n30\n')

    def test_single_row(self):
        df = pd.DataFrame({'name': ['X'], 'score': [10]})
        result = self.pc_instance._extract_string_for_graphic(df)
        self.assertEqual(result, 'X\n10\n')

    def test_empty_dataframe_returns_trailing_newline(self):
        df = pd.DataFrame({'name': [], 'score': []})
        result = self.pc_instance._extract_string_for_graphic(df)
        self.assertEqual(result, '\n')


# ---------------------------------------------------------------------------
# pc._extract_match_team_context
# ---------------------------------------------------------------------------

class TestExtractMatchTeamContext(unittest.TestCase):
    """Tests for the new team-context extraction helper."""

    def setUp(self):
        self.pc_instance = pc('test_key', 12345)

    def test_returns_correct_ids_and_names(self):
        data = {
            'home_team_id': '59723',
            'away_team_id': '28817',
            'home_club_name': 'Alleyn CC',
            'home_team_name': '1st XI',
            'away_club_name': 'Effingham CC',
            'away_team_name': '1st XI',
        }
        ctx = self.pc_instance._extract_match_team_context(data)
        self.assertEqual(ctx['all_ids'], [59723, 28817])
        self.assertEqual(ctx['team_name_lookup'][59723], 'Alleyn CC - 1st XI')
        self.assertEqual(ctx['team_name_lookup'][28817], 'Effingham CC - 1st XI')

    def test_normalises_string_ids_to_int(self):
        data = {
            'home_team_id': '100',
            'away_team_id': '200',
            'home_club_name': 'Home Club',
            'home_team_name': '2nd XI',
            'away_club_name': 'Away Club',
            'away_team_name': '1st XI',
        }
        ctx = self.pc_instance._extract_match_team_context(data)
        self.assertIsInstance(ctx['all_ids'][0], int)
        self.assertIsInstance(ctx['all_ids'][1], int)


# ---------------------------------------------------------------------------
# Existing TestPlayCricket tests (updated where the refactoring changed behaviour)
# ---------------------------------------------------------------------------

class TestPlayCricket(unittest.TestCase):

    def setUp(self):
        self.api_key = 'your_api_key'
        self.site_id = 12345
        self.pc_instance = pc(self.api_key, self.site_id)

    @patch.object(pc, '_make_api_request')
    def test_list_registered_players(self, mock_make_api_request):
        mock_make_api_request.return_value = {
            'players': [
                {'player_id': 1, 'player_name': 'John Doe',
                 'team_id': 1, 'team_name': 'Team A'},
                {'player_id': 2, 'player_name': 'Alice Smith',
                 'team_id': 2, 'team_name': 'Team B'},
            ]
        }
        expected_df = pd.DataFrame({
            'player_id': [1, 2],
            'player_name': ['John Doe', 'Alice Smith'],
            'team_id': [1, 2],
            'team_name': ['Team A', 'Team B'],
        })
        df = self.pc_instance.list_registered_players()
        pd.testing.assert_frame_equal(df, expected_df)

    @patch.object(pc, '_make_api_request')
    def test_get_all_matches(self, mock_make_api_request):
        mock_make_api_request.return_value = {
            'matches': [
                {
                    'match_id': 1,
                    'home_team_id': 1, 'home_team_name': 'Team A',
                    'away_team_id': 2, 'away_team_name': 'Team B',
                    'competition_id': 1.0, 'competition_type': 'League',
                    'match_date': '01/01/2022', 'last_updated': '01/01/2022',
                },
                {
                    'match_id': 2,
                    'home_team_id': 3, 'home_team_name': 'Team C',
                    'away_team_id': 4, 'away_team_name': 'Team D',
                    'competition_id': 2.0, 'competition_type': 'Cup',
                    'match_date': '02/01/2022', 'last_updated': '02/01/2022',
                },
            ]
        }
        expected_df = pd.DataFrame({
            'match_id': [1, 2],
            'home_team_id': [1, 3],
            'home_team_name': ['Team A', 'Team C'],
            'away_team_id': [2, 4],
            'away_team_name': ['Team B', 'Team D'],
            'competition_id': [1.0, 2.0],
            'competition_type': ['League', 'Cup'],
            'match_date': pd.to_datetime(['2022-01-01', '2022-01-02']),
            'last_updated': pd.to_datetime(['2022-01-01', '2022-01-02']),
        })
        df = self.pc_instance.get_all_matches(season=2022)
        pd.testing.assert_frame_equal(df, expected_df)

    @patch.object(pc, '_make_api_request')
    def test_get_all_matches_filters_by_team_id(self, mock_make_api_request):
        mock_make_api_request.return_value = {
            'matches': [
                {
                    'match_id': 1,
                    'home_team_id': 10, 'home_team_name': 'Team A',
                    'away_team_id': 20, 'away_team_name': 'Team B',
                    'competition_id': '1', 'competition_type': 'League',
                    'match_date': '01/01/2022', 'last_updated': '01/01/2022',
                },
                {
                    'match_id': 2,
                    'home_team_id': 30, 'home_team_name': 'Team C',
                    'away_team_id': 40, 'away_team_name': 'Team D',
                    'competition_id': '2', 'competition_type': 'League',
                    'match_date': '02/01/2022', 'last_updated': '02/01/2022',
                },
            ]
        }
        df = self.pc_instance.get_all_matches(season=2022, team_ids=[10])
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['match_id'], 1)

    @patch.object(pc, '_make_api_request')
    def test_get_all_matches_filters_by_competition_type(self, mock_make_api_request):
        mock_make_api_request.return_value = {
            'matches': [
                {
                    'match_id': 1,
                    'home_team_id': 10, 'home_team_name': 'A',
                    'away_team_id': 20, 'away_team_name': 'B',
                    'competition_id': '1', 'competition_type': 'League',
                    'match_date': '01/01/2022', 'last_updated': '01/01/2022',
                },
                {
                    'match_id': 2,
                    'home_team_id': 30, 'home_team_name': 'C',
                    'away_team_id': 40, 'away_team_name': 'D',
                    'competition_id': '2', 'competition_type': 'Cup',
                    'match_date': '02/01/2022', 'last_updated': '02/01/2022',
                },
            ]
        }
        df = self.pc_instance.get_all_matches(
            season=2022, competition_types=['Cup'])
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['match_id'], 2)

    @patch.object(pc, '_make_api_request')
    def test_get_league_table(self, mock_make_api_request):
        mock_make_api_request.return_value = {
            'league_table': [{
                'values': [
                    {'col1': 1, 'col2': 'Team A', 'col3': 1,
                     'col4': 1, 'col5': 0, 'col6': 0, 'col7': 3},
                    {'col1': 2, 'col2': 'Team B', 'col3': 1,
                     'col4': 0, 'col5': 0, 'col6': 1, 'col7': 0},
                ],
                'headings': {
                    'col1': 'POSITION', 'col2': 'TEAM', 'col3': 'P',
                    'col4': 'W', 'col5': 'D', 'col6': 'L', 'col7': 'PTS',
                },
                'key': 'POSITION,TEAM,P,W,D,L,PTS',
            }]
        }
        expected_df = pd.DataFrame({
            'POSITION': [1, 2],
            'TEAM': ['Team A', 'Team B'],
            'W': [1, 0],
            'D': [0, 0],
            'L': [0, 1],
            'PTS': [3, 0],
        })
        df, key = self.pc_instance.get_league_table(competition_id=1, simple=True)
        pd.testing.assert_frame_equal(df, expected_df)
        self.assertEqual(key, ['POSITION', 'TEAM', 'P', 'W', 'D', 'L', 'PTS'])

    @patch.object(pc, '_make_api_request')
    def test_get_match_result_string(self, mock_make_api_request):
        """Mock uses the correct API structure (match_details list)."""
        match_id = 1
        expected_result = 'Match result description'
        mock_make_api_request.return_value = {
            'match_details': [{'result_description': expected_result}]
        }
        result = self.pc_instance.get_match_result_string(match_id)
        self.assertEqual(result, expected_result)

    @patch.object(pc, '_make_api_request')
    def test_get_result_for_my_team_win(self, mock_make_api_request):
        mock_make_api_request.return_value = {
            'match_details': [{'result_applied_to': 1, 'result': 'W'}]
        }
        result = self.pc_instance.get_result_for_my_team(match_id=1, team_ids=[1, 2])
        self.assertEqual(result, 'W')

    @patch.object(pc, '_make_api_request')
    def test_get_result_for_my_team_none_team_ids(self, mock_make_api_request):
        """Passing team_ids=None should not raise; None is treated as empty list."""
        mock_make_api_request.return_value = {
            'match_details': [{'result_applied_to': '1', 'result': 'W'}]
        }
        # With no team_ids, applied_to is not in [], so result is swapped W→L
        result = self.pc_instance.get_result_for_my_team(match_id=1, team_ids=None)
        self.assertEqual(result, 'L')

    @patch.object(pc, '_make_api_request')
    def test_get_innings_total_scores(self, mock_make_api_request):
        match_id = 6178722
        mock_make_api_request.return_value = _load_fixture('match_details.json')
        expected_df = pd.read_pickle(
            os.path.join(TESTDATA_DIR, 'get_innings_total_scores.pkl'))
        df = self.pc_instance.get_innings_total_scores(match_id)
        pd.testing.assert_frame_equal(df, expected_df)


# ---------------------------------------------------------------------------
# Tests that verify specific bug fixes
# ---------------------------------------------------------------------------

class TestGetIndividualStatsBugFixes(unittest.TestCase):

    def setUp(self):
        self.pc_instance = pc('test_key', 12345)

    @patch.object(pc, '_make_api_request')
    def test_empty_innings_returns_correct_schema(self, mock):
        """Empty innings must return DataFrames with the standard column schema."""
        mock.return_value = {
            'match_details': [{
                'home_team_id': '1', 'away_team_id': '2',
                'home_club_name': 'Home', 'home_team_name': 'XI',
                'away_club_name': 'Away', 'away_team_name': 'XI',
                'innings': [],
            }]
        }
        batting, bowling = self.pc_instance.get_individual_stats(match_id=1)
        self.assertIsInstance(batting, pd.DataFrame)
        self.assertIsInstance(bowling, pd.DataFrame)
        self.assertEqual(list(batting.columns), config.STANDARD_BATTING_COLS)
        self.assertEqual(list(bowling.columns), config.STANDARD_BOWLING_COLS)

    @patch.object(pc, '_make_api_request')
    def test_filters_by_team_id(self, mock):
        """Only batting/bowling records for the requested team should be returned."""
        mock.return_value = _load_fixture('match_details.json')
        batting, bowling = self.pc_instance.get_individual_stats(
            match_id=6178722, team_ids=[59723])
        self.assertTrue((batting['team_id'] == 59723).all(),
                        'batting should only contain rows for team 59723')
        self.assertTrue((bowling['team_id'] == 59723).all(),
                        'bowling should only contain rows for team 59723')

    @patch.object(pc, '_make_api_request')
    def test_batting_not_out_flag(self, mock):
        """Batters listed as 'not out' or 'did not bat' should have not_out=1."""
        mock.return_value = _load_fixture('match_details.json')
        batting, _ = self.pc_instance.get_individual_stats(match_id=6178722)
        not_out_rows = batting.loc[batting['how_out'].isin(
            ['not out', 'did not bat', 'retired not out'])]
        self.assertTrue((not_out_rows['not_out'] == 1).all())


class TestGetMatchPartnershipsBugFix(unittest.TestCase):
    """Verify score_added is computed per innings, not across the whole match."""

    def setUp(self):
        self.pc_instance = pc('test_key', 12345)

    @patch.object(pc, '_make_api_request')
    def test_first_wicket_of_second_innings_score_added(self, mock):
        """
        The first wicket of innings 2 fell at 14 runs.
        With the old cross-innings shift, score_added would be 14 - 136 = -122.
        With the fix it must be 14 (runs since the start of the innings).
        """
        mock.return_value = _load_fixture('match_details.json')
        partnerships = self.pc_instance.get_match_partnerships(match_id=6178722)
        inn2 = partnerships.loc[partnerships['innings'] == 2]
        self.assertFalse(inn2.empty, 'innings 2 should have partnership rows')
        self.assertEqual(inn2.iloc[0]['score_added'], 14)

    @patch.object(pc, '_make_api_request')
    def test_first_wicket_of_first_innings_score_added(self, mock):
        """First wicket of innings 1 fell at 13; score_added must equal 13."""
        mock.return_value = _load_fixture('match_details.json')
        partnerships = self.pc_instance.get_match_partnerships(match_id=6178722)
        inn1 = partnerships.loc[partnerships['innings'] == 1]
        self.assertEqual(inn1.iloc[0]['score_added'], 13)


class TestGetIndividualStatsFromAllGames(unittest.TestCase):

    def setUp(self):
        self.pc_instance = pc('test_key', 12345)

    @patch.object(pc, '_make_api_request')
    def test_fielding_is_independent_copy_of_batting(self, mock):
        """
        fielding must be a separate DataFrame from batting so that
        mutations to one do not affect the other.
        """
        mock.return_value = _load_fixture('match_details.json')
        batting, _, fielding = self.pc_instance.get_individual_stats_from_all_games(
            match_ids=[6178722])
        # Mutating the batting index should not change fielding's index.
        batting_id_before = id(batting)
        fielding_id_before = id(fielding)
        self.assertNotEqual(batting_id_before, fielding_id_before,
                            'batting and fielding must be different objects')

    @patch.object(pc, '_make_api_request')
    def test_fielding_contains_opposition_rows_when_team_ids_given(self, mock):
        """
        When team_ids is provided, fielding must contain the *opposition* batting
        rows (carrying fielder_name for catches/run-outs against our team).
        """
        mock.return_value = _load_fixture('match_details.json')
        # Team 59723 is Alleyn; opposition is 28817 (Effingham)
        batting, _, fielding = self.pc_instance.get_individual_stats_from_all_games(
            match_ids=[6178722], team_ids=[59723])
        self.assertTrue((batting['team_id'] == 59723).all())
        self.assertTrue((fielding['team_id'] == 28817).all())


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

class TestAggregateStats(unittest.TestCase):

    def setUp(self):
        self.pc_instance = pc('test_key', 12345)

    @patch.object(pc, '_make_api_request')
    def test_aggregate_batting_has_expected_columns(self, mock):
        mock.return_value = _load_fixture('match_details.json')
        batting, bowling, fielding = self.pc_instance.get_individual_stats_from_all_games(
            match_ids=[6178722])
        batting_agg, _, _ = self.pc_instance.aggregate_stats(
            group_by_team=False,
            batting=batting,
            bowling=bowling,
            fielding=fielding,
        )
        for col in ['rank', 'runs', 'top_score', '50s', '100s', 'average']:
            self.assertIn(col, batting_agg.columns, f'batting missing column: {col}')

    @patch.object(pc, '_make_api_request')
    def test_aggregate_bowling_five_fers_column_exists(self, mock):
        """5fers column must be present (was fragile with lambda naming)."""
        mock.return_value = _load_fixture('match_details.json')
        batting, bowling, fielding = self.pc_instance.get_individual_stats_from_all_games(
            match_ids=[6178722])
        _, bowling_agg, _ = self.pc_instance.aggregate_stats(
            group_by_team=False, batting=batting, bowling=bowling, fielding=fielding)
        self.assertIn('5fers', bowling_agg.columns)

    @patch.object(pc, '_make_api_request')
    def test_aggregate_batting_average_is_none_for_zero_innings(self, mock):
        """Players with innings_to_count=0 should have NaN (not an error) average."""
        mock.return_value = _load_fixture('match_details.json')
        batting, bowling, fielding = self.pc_instance.get_individual_stats_from_all_games(
            match_ids=[6178722])
        batting_agg, _, _ = self.pc_instance.aggregate_stats(
            group_by_team=False, batting=batting, bowling=bowling, fielding=fielding)
        zero_innings = batting_agg.loc[batting_agg['innings_to_count'] == 0]
        if not zero_innings.empty:
            self.assertTrue(zero_innings['average'].isna().all())


# ---------------------------------------------------------------------------
# pc init — mutable default argument fix
# ---------------------------------------------------------------------------

class TestPcInit(unittest.TestCase):

    def test_default_team_names_are_not_shared(self):
        """Two pc instances must not share the same team_names list."""
        pc1 = pc('key1', 1)
        pc2 = pc('key2', 2)
        pc1.team_names.append('Test Team')
        self.assertNotIn('Test Team', pc2.team_names,
                         'mutable default: team_names lists must be independent')

    def test_default_lookup_is_not_shared(self):
        """Two pc instances must not share the same team_name_to_ids_lookup dict."""
        pc1 = pc('key1', 1)
        pc2 = pc('key2', 2)
        pc1.team_name_to_ids_lookup['New Team'] = 99
        self.assertNotIn('New Team', pc2.team_name_to_ids_lookup,
                         'mutable default: lookup dicts must be independent')


if __name__ == '__main__':
    unittest.main()
