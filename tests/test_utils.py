from playcric.utils import u
from playcric import config
import pandas as pd
import unittest
from unittest.mock import patch


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.utils = u()

    def test_add_team_name_id_and_innings(self):
        df = pd.DataFrame(index=[0])
        team_name = 'Team A'
        team_id = 1
        opposition_name = 'Team B'
        opposition_id = 2
        innings_n = 1
        match_id = 123

        expected_df = pd.DataFrame({
            'team_name': ['Team A'],
            'team_id': [1],
            'opposition_name': ['Team B'],
            'opposition_id': [2],
            'innings': [1],
            'match_id': [123]
        })

        modified_df = self.utils._add_team_name_id_and_innings(
            df, team_name, team_id, opposition_name, opposition_id, innings_n, match_id)

        pd.testing.assert_frame_equal(modified_df, expected_df)

    def test_write_bowling_string(self):
        row = {
            "wickets": 3,
            "runs": 25
        }
        expected_result = "3-25"

        result = self.utils._write_bowling_string(row)

        self.assertEqual(result, expected_result)

    def test_write_batting_string(self):
        row = {
            "runs": 50,
            "balls": 30,
            "not_out": 0
        }
        expected_result = "50(30)"

        result = self.utils._write_batting_string(row)

        self.assertEqual(result, expected_result)

    def test_get_initials_surname(self):
        # Test case 1: Full name with multiple words
        name1 = "John Doe"
        expected_result1 = "J Doe"
        result1 = self.utils._get_initials_surname(name1)
        self.assertEqual(result1, expected_result1)

        # Test case 2: Full name with single word
        name2 = "Alice"
        expected_result2 = "Alice"
        result2 = self.utils._get_initials_surname(name2)
        self.assertEqual(result2, expected_result2)

        # Test case 3: Empty name
        name3 = ""
        expected_result3 = None
        result3 = self.utils._get_initials_surname(name3)
        self.assertEqual(result3, expected_result3)

        class TestUtils(unittest.TestCase):
            def setUp(self):
                self.utils = u()

    def test_standardise_bowl_with_data(self):
        # Test case with non-empty DataFrame
        bowl = pd.DataFrame({
            'bowler_name': ['John Doe', 'Alice Smith'],
            'overs': ['4.2', '3.5'],
            'runs': ['25', '15'],
            'wickets': ['2', '1'],
            'maidens': ['0', '1'],
            'no_balls': ['1', '0'],
            'wides': ['2', '1']
        })

        expected_result = pd.DataFrame({
            'bowler_name': ['John Doe', 'Alice Smith'],
            'overs': ['4.2', '3.5'],
            'runs': [25, 15],
            'wickets': [2, 1],
            'maidens': [0, 1],
            'no_balls': [1, 0],
            'wides': [2, 1],
            'initial_name': ['J Doe', 'A Smith'],
            'balls': [26, 23]
        })

        modified_bowl = self.utils._standardise_bowl(bowl)

        pd.testing.assert_frame_equal(modified_bowl, expected_result)

    def test_standardise_bowl_with_empty_data(self):
        # Test case with empty DataFrame
        bowl = pd.DataFrame()

        expected_result = pd.DataFrame(columns=config.STANDARD_BOWLING_COLS)

        modified_bowl = self.utils._standardise_bowl(bowl)

        pd.testing.assert_frame_equal(modified_bowl, expected_result)

    def test_standardise_bat_with_non_empty_data(self):
        # Test case with non-empty DataFrame
        bat = pd.DataFrame({
            'batsman_name': ['John Doe', 'Alice Smith'],
            'how_out': ['not out', 'caught'],
            'runs': ['50', '25'],
            'fours': ['5', '3'],
            'sixes': ['2', '1'],
            'balls': ['30', '20'],
            'position': ['1', '2']
        })

        expected_result = pd.DataFrame({
            'batsman_name': ['John Doe', 'Alice Smith'],
            'how_out': ['not out', 'caught'],
            'runs': [50, 25],
            'fours': [5, 3],
            'sixes': [2, 1],
            'balls': [30, 20],
            'position': [1, 2],
            'not_out': [1, 0],
            'initial_name': ['J Doe', 'A Smith']
        })

        modified_bat = self.utils._standardise_bat(bat)

        pd.testing.assert_frame_equal(modified_bat, expected_result)

    def test_standardise_bat_with_empty_data(self):
        # Test case with empty DataFrame
        bat = pd.DataFrame()

        expected_result = pd.DataFrame(columns=config.STANDARD_BATTING_COLS)

        modified_bat = self.utils._standardise_bat(bat)

        pd.testing.assert_frame_equal(modified_bat, expected_result)

    def test_get_result_letter(self):
        data = {
            'result': 'W',
            'result_applied_to': 4
        }
        team_ids = [1, 2]

        result_letter = self.utils._get_result_letter(data, team_ids)

        self.assertEqual(result_letter, 'L')

        class TestUtils(unittest.TestCase):
            def setUp(self):
                self.utils = u()

    def test_clean_league_table_simple(self):
        # Test case with simple cleaning
        df = pd.DataFrame({
            'position': [1, 2, 3],
            'team': ['Team A', 'Team B', 'Team C'],
            'tw': [5, 4, 3],
            'wd': [1, 2, 3],
            'l': [0, 1, 2],
            'pts': [10, 8, 6]
        })

        expected_result = pd.DataFrame({
            'POSITION': [1, 2, 3],
            'TEAM': ['Team A', 'Team B', 'Team C'],
            'W': [5, 4, 3],
            'D': [1, 2, 3],
            'L': [0, 1, 2],
            'PTS': [10, 8, 6]
        })

        modified_df = self.utils._clean_league_table(
            df, simple=True, key='W - Total wins')

        pd.testing.assert_frame_equal(modified_df, expected_result)

    def test_clean_league_table_advanced(self):
        # Test case with advanced cleaning
        df = pd.DataFrame({
            'position': [1, 2, 3],
            'team': ['Team A', 'Team B', 'Team C'],
            'tw': [5, 4, 3],
            'wd': [1, 2, 3],
            'l': [0, 1, 2],
            'pts': [10, 8, 6]
        })

        expected_result = pd.DataFrame({
            'POSITION': [1, 2, 3],
            'TEAM': ['Team A', 'Team B', 'Team C'],
            'TW': [5, 4, 3],
            'WD': [1, 2, 3],
            'L': [0, 1, 2],
            'PTS': [10, 8, 6]
        })

        wins = config.LEAGUE_TABLE_WIN_TYPES
        draws = config.LEAGUE_TABLE_DRAW_TYPES
        losses = config.LEAGUE_TABLE_LOSS_TYPES

        for col in wins+draws+losses:
            if col not in expected_result.columns:
                expected_result[col] = 0

        modified_df = self.utils._clean_league_table(
            df, simple=False, key='WD - Total wins and draws')

        pd.testing.assert_frame_equal(modified_df, expected_result)

    @patch('requests.get')
    def test_make_api_request_success(self, mock_get):
        # Mock the response from the API
        mock_response = {
            'status': 'success',
            'data': {
                'id': 1,
                'name': 'Team A'
            }
        }
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        # Make the API request
        url = 'https://api.example.com/teams/1'
        response = self.utils._make_api_request(url)

        # Assert the response
        self.assertEqual(response, mock_response)

    @patch('requests.get')
    def test_make_api_request_failure(self, mock_get):
        # Mock the response from the API
        mock_get.return_value.status_code = 404

        # Make the API request
        url = 'https://api.example.com/teams/1'

        # Assert that an exception is raised
        with self.assertRaises(Exception):
            self.utils._make_api_request(url)

    def test_convert_team_ids_to_ints(self):
        team_ids = ['1', '2', '3', '4']
        expected_result = [1, 2, 3, 4]

        result = self.utils._convert_team_ids_to_ints(team_ids)

        self.assertEqual(result, expected_result)

    def test_count_balls(self):
        # Test case 1: Valid input string with overs and balls
        input_str1 = '4.2'
        expected_result1 = 26
        result1 = self.utils._count_balls(input_str1)
        self.assertEqual(result1, expected_result1)

        # Test case 2: Valid input string with only overs
        input_str2 = '5'
        expected_result2 = 30
        result2 = self.utils._count_balls(input_str2)
        self.assertEqual(result2, expected_result2)

        # Test case 3: Valid input string with only balls
        input_str3 = '.3'
        expected_result3 = 3
        result3 = self.utils._count_balls(input_str3)
        self.assertEqual(result3, expected_result3)

        # Test case 4: Empty input string
        input_str4 = ''
        expected_result4 = 0
        result4 = self.utils._count_balls(input_str4)
        self.assertEqual(result4, expected_result4)

    def test_calculate_overs(self):
        # Test case 1: Total balls is a multiple of 6
        total_balls1 = 24
        expected_result1 = '4.0'
        result1 = self.utils._calculate_overs(total_balls1)
        self.assertEqual(result1, expected_result1)

        # Test case 2: Total balls is not a multiple of 6
        total_balls2 = 25
        expected_result2 = '4.1'
        result2 = self.utils._calculate_overs(total_balls2)
        self.assertEqual(result2, expected_result2)

        # Test case 3: Total balls is 0
        total_balls3 = 0
        expected_result3 = '0.0'
        result3 = self.utils._calculate_overs(total_balls3)
        self.assertEqual(result3, expected_result3)

    def test_clean_team_name(self):
        # Test case 1: Team name with unwanted characters and words
        self.utils.team_names = ['Team A', 'Team C']

        team1 = "Team A - Test"
        expected_result1 = "Team A"
        result1 = self.utils._clean_team_name(team1)
        self.assertEqual(result1, expected_result1)

        # Test case 2: Team name without unwanted characters and words
        team2 = "Team B"
        expected_result2 = "Team B"
        result2 = self.utils._clean_team_name(team2)
        self.assertEqual(result2, expected_result2)

        # Test case 3: Team name with banned words
        team3 = "Team C - Banned Word"
        expected_result3 = "Team C"
        result3 = self.utils._clean_team_name(team3)
        self.assertEqual(result3, expected_result3)

        # Test case 4: Team name with multiple spaces
        team4 = "Team   D     "
        expected_result4 = "Team D"
        result4 = self.utils._clean_team_name(team4)
        self.assertEqual(result4, expected_result4)

    def test_calculate_batting_average_with_non_zero_innings(self):
        # Test case with non-zero innings
        row = {
            "runs": 100,
            "innings_to_count": 10
        }
        expected_result = 10.0

        result = self.utils._calculate_batting_average(row)

        self.assertEqual(result, expected_result)

    def test_calculate_batting_average_with_zero_innings(self):
        # Test case with zero innings
        row = {
            "runs": 100,
            "innings_to_count": 0
        }
        expected_result = None

        result = self.utils._calculate_batting_average(row)

        self.assertEqual(result, expected_result)

    @patch.object(u, '_make_api_request')
    def test_get_players_used_in_match(self, mock_make_api_request):
        match_id = 1
        mock_make_api_request.return_value = {
            'match_details': [
                {'home_team_id': 1,
                    'away_team_id': 100,
                    'home_club_id': 2,
                    'away_club_id': 200,
                    'players': [
                        {
                            'home_team': [
                                {
                                    'player_id': 1,
                                    'player_name': 'John Doe',
                                    # 'team_id': 1,
                                    # 'club_id': 2,
                                    'team_name': 'Team A'
                                },
                                {
                                    'player_id': 2,
                                    'player_name': 'Alice Smith',
                                    # 'team_id': 1,
                                    # 'club_id': 2,
                                    'team_name': 'Team A'
                                }
                            ]},
                        {'away_team': [
                            {
                                'player_id': 3,
                                'player_name': 'Bob Johnson',
                                # 'team_id': 100,
                                # 'club_id': 200,
                                'team_name': 'Team B'
                            },
                            {
                                'player_id': 4,
                                'player_name': 'Eve Williams',
                                # 'team_id': 100,
                                # 'club_id': 200,

                                'team_name': 'Team B'
                            }
                        ]
                        }
                    ]
                 }
            ]
        }
        expected_df = pd.DataFrame({
            'player_id': [1, 2, 3, 4],
            'player_name': ['John Doe', 'Alice Smith', 'Bob Johnson', 'Eve Williams'],


            'team_name': ['Team A', 'Team A', 'Team B', 'Team B'],
            'team_id': [1, 1, 100, 100],
            'club_id': [2, 2, 200, 200],
            'match_id': [1, 1, 1, 1]
        })
        df = self.utils._get_players_used_in_match(
            match_id, api_key='test_api_key')
        pd.testing.assert_frame_equal(df, expected_df)


if __name__ == '__main__':
    unittest.main()
