import unittest
from unittest.mock import patch
from playcric.playcricket import pc
import pandas as pd
import json
import os


class TestPlayCricket(unittest.TestCase):
    def setUp(self):
        self.api_key = 'your_api_key'
        self.site_id = 'your_site_id'
        self.pc_instance = pc(self.api_key, self.site_id)

    @patch.object(pc, '_make_api_request')
    def test_list_registered_players(self, mock_make_api_request):
        mock_make_api_request.return_value = {
            'players': [
                {
                    'player_id': 1,
                    'player_name': 'John Doe',
                    'team_id': 1,
                    'team_name': 'Team A'
                },
                {
                    'player_id': 2,
                    'player_name': 'Alice Smith',
                    'team_id': 2,
                    'team_name': 'Team B'
                }
            ]
        }
        expected_df = pd.DataFrame({
            'player_id': [1, 2],
            'player_name': ['John Doe', 'Alice Smith'],
            'team_id': [1, 2],
            'team_name': ['Team A', 'Team B']
        })
        df = self.pc_instance.list_registered_players()
        pd.testing.assert_frame_equal(df, expected_df)

    @patch.object(pc, '_make_api_request')
    def test_get_all_matches(self, mock_make_api_request):
        mock_make_api_request.return_value = {
            'matches': [
                {
                    'match_id': 1,
                    'home_team_id': 1,
                    'home_team_name': 'Team A',
                    'away_team_id': 2,
                    'away_team_name': 'Team B',
                    'competition_id': 1,
                    'competition_type': 'League',
                    'match_date': '01/01/2022',
                    'last_updated': '01/01/2022'
                },
                {
                    'match_id': 2,
                    'home_team_id': 3,
                    'home_team_name': 'Team C',
                    'away_team_id': 4,
                    'away_team_name': 'Team D',
                    'competition_id': 2,
                    'competition_type': 'Cup',
                    'match_date': '02/01/2022',
                    'last_updated': '02/01/2022'
                }
            ]
        }
        expected_df = pd.DataFrame({
            'match_id': [1, 2],
            'home_team_id': [1, 3],
            'home_team_name': ['Team A', 'Team C'],
            'away_team_id': [2, 4],
            'away_team_name': ['Team B', 'Team D'],
            'competition_id': [1, 2],
            'competition_type': ['League', 'Cup'],
            'match_date': pd.to_datetime(['2022-01-01', '2022-01-02']),
            'last_updated': pd.to_datetime(['2022-01-01', '2022-01-02'])
        })
        df = self.pc_instance.get_all_matches(season=2022)
        pd.testing.assert_frame_equal(df, expected_df)

    @patch.object(pc, '_make_api_request')
    def test_get_league_table(self, mock_make_api_request):
        mock_make_api_request.return_value = {
            'league_table': [
                {
                    'values': [
                        {'col1': 1,
                            'col2': 'Team A',
                            'col3': 1,
                            'col4': 1,
                            'col5': 0,
                            'col6': 0,
                            'col7': 3
                         },
                        {'col1': 2,
                            'col2': 'Team B',
                            'col3': 1,
                            'col4': 0,
                            'col5': 0,
                            'col6': 1,
                            'col7': 0
                         }
                    ],
                    'headings': {
                        'col1': 'POSITION',
                        'col2': 'TEAM',
                        'col3': 'P',
                        'col4': 'W',
                        'col5': 'D',
                        'col6': 'L',
                        'col7': 'PTS'
                    },
                    'key': 'POSITION,TEAM,P,W,D,L,PTS'
                }
            ]
        }
        expected_df = pd.DataFrame({
            'POSITION': [1, 2],
            'TEAM': ['Team A', 'Team B'],
            'W': [1, 0],
            'D': [0, 0],
            'L': [0, 1],
            'PTS': [3, 0]
        })
        df, key = self.pc_instance.get_league_table(
            competition_id=1, simple=True)
        pd.testing.assert_frame_equal(df, expected_df)
        # self.assertEqual(key, ['TEAM', 'P', 'W', 'D', 'L', 'PTS'])

    @patch.object(pc, '_make_api_request')
    def test_get_match_result_string(self, mock_make_api_request):
        match_id = 1
        expected_result = 'Match result description'
        mock_make_api_request.return_value = [
            {'result_description': expected_result}]

        result = self.pc_instance.get_match_result_string(match_id)

        self.assertEqual(result, expected_result)

    @patch.object(pc, '_make_api_request')
    def test_get_result_for_my_team(self, mock_make_api_request):
        match_id = 1
        team_ids = [1, 2]
        expected_result = 'W'
        mock_make_api_request.return_value = {
            'match_details': [
                {'result_applied_to': 1,
                    'result': 'W'
                 }
            ]
        }

        result = self.pc_instance.get_result_for_my_team(match_id, team_ids)

        self.assertEqual(result, expected_result)

    @patch.object(pc, '_make_api_request')
    def test_get_innings_total_scores(self, mock_make_api_request):
        match_id = 6178722
        TESTDATA_FILENAME = os.path.join(os.path.dirname(
            __file__), 'test_files/match_details.json')
        f = open(TESTDATA_FILENAME)

        mock_make_api_request.return_value = json.load(f)
        EXPDATA_FILENAME = os.path.join(os.path.dirname(
            __file__), 'test_files/get_innings_total_scores.PKL')
        expected_df = pd.read_pickle(EXPDATA_FILENAME)
        df = self.pc_instance.get_innings_total_scores(match_id)
        pd.testing.assert_frame_equal(df, expected_df)


if __name__ == '__main__':
    unittest.main()
