import unittest
from unittest.mock import patch
from playcric.alleyn import acc
from playcric.playcricket import pc
import pandas as pd
from datetime import date


class TestAlleyn(unittest.TestCase):
    def setUp(self):
        self.api_key = 'your_api_key'
        self.site_id = 'your_site_id'
        self.acc_instance = acc(self.api_key, self.site_id)

    def test_get_innings_scores(self):
        match_ids = [1, 2, 3]
        expected_team_names = "Team A\nTeam B\nTeam A\nTeam B\nTeam A\nTeam B"
        expected_innings_scores = "100-2\n150-3\n100-2\n150-3\n100-2\n150-3"
        with patch.object(self.acc_instance, '_make_api_request') as mock_make_api_request:
            mock_make_api_request.return_value = {
                'match_details': [
                    {
                        'result': True,
                        'innings': [
                            {
                                'team_batting_name': 'Team A',
                                'team_batting_id': 1,
                                'runs': 100,
                                'wickets': '2'
                            },
                            {
                                'team_batting_name': 'Team B',
                                'team_batting_id': 2,
                                'runs': 150,
                                'wickets': '3'
                            }
                        ]
                    }
                ]
            }
            team_names, innings_scores = self.acc_instance.get_innings_scores(
                match_ids)
            self.assertEqual(team_names, expected_team_names)
            self.assertEqual(innings_scores, expected_innings_scores)

    def test_make_sure_number_of_players_is_consistent(self):
        api_key = 'your_api_key'
        site_id = 'your_site_id'
        acc_instance = acc(api_key, site_id)

        names_list = ['John', 'Alice']
        stats_list = ['100', '50']
        expected_names_list = ['John', 'Alice', ' ']
        expected_stats_list = ['100', '50', ' ']

        actual_names_list, actual_stats_list = acc_instance._make_sure_number_of_players_is_consistent(
            names_list, stats_list)

        self.assertEqual(actual_names_list, expected_names_list)
        self.assertEqual(actual_stats_list, expected_stats_list)

    def test_get_result_description_and_margin(self):
        match_ids = [1]
        team_ids = [1, 10, 3]
        expected_result = "Team A Lost by 3 wickets\n"
        with patch.object(self.acc_instance, '_make_api_request') as mock_make_api_request:
            mock_make_api_request.return_value = {
                'match_details': [
                    {
                        'result': 'W',
                        'home_team_id': 1,
                        'home_team_name': 'Team A',
                        'away_team_id': 2,
                        'away_team_name': 'Team B',
                        'innings': [
                            {
                                'team_batting_name': 'Team A',
                                'team_batting_id': 1,
                                'runs': 100,
                                'wickets': '8'
                            },
                            {
                                'team_batting_name': 'Team B',
                                'team_batting_id': 2,
                                'runs': 101,
                                'wickets': '7'
                            }
                        ],
                        'result_applied_to': 2,
                        'batted_first': 1
                    }
                ]
            }
            result_description_and_margin = self.acc_instance.get_result_description_and_margin(
                match_ids, team_ids)
            self.assertEqual(result_description_and_margin, expected_result)

    def test_add_to_stats_string(self):
        names_list = ['John', 'Alice']
        stats_list = ['100', '50']
        expected_stats_summary = 'John\nAlice\n100\n50\n'

        actual_stats_summary = self.acc_instance._add_to_stats_string(
            '', names_list, stats_list)

        self.assertEqual(actual_stats_summary, expected_stats_summary)

    def test_order_matches_for_the_graphics(self):
        matches = pd.DataFrame({
            'match_date': ['2022-01-03', '2022-01-02', '2022-01-01'],
            'home_team_id': [3, 2, 1],
            'away_team_id': [6, 5, 4],
            'home_club_name': ['Team C', 'Team B', 'Team A'],
            'away_club_name': ['Team F', 'Team E', 'Team D']
        })

        expected_order = pd.DataFrame({
            'match_date': ['2022-01-01', '2022-01-02', '2022-01-03'],
            'home_team_id': [1, 2, 3],
            'away_team_id': [4, 5, 6],
            'home_club_name': ['Team A', 'Team B', 'Team C'],
            'away_club_name': ['Team D', 'Team E', 'Team F'], 'club_team_name': [None, None, None]
        })

        ordered_matches = self.acc_instance.order_matches_for_the_graphics(
            matches)

        ordered_matches.reset_index(inplace=True, drop=True)

        self.assertEqual(ordered_matches.to_dict(), expected_order.to_dict())

    def test_get_weekend_matches(self):
        saturday = date(2022, 1, 1)
        matches = pd.DataFrame({
            'match_date': ['2022-01-01', '2022-01-02', '2022-01-03'],
            'home_team_id': [1, 2, 3],
            'away_team_id': [4, 5, 6],
            'home_club_name': ['Team A', 'Team B', 'Team C'],
            'away_club_name': ['Team D', 'Team E', 'Team F']
        })
        matches['match_date'] = pd.to_datetime(matches['match_date'])

        expected_matches = pd.DataFrame({
            'match_date': ['2022-01-01', '2022-01-02'],
            'home_team_id': [1, 2],
            'away_team_id': [4, 5],
            'home_club_name': ['Team A', 'Team B'],
            'away_club_name': ['Team D', 'Team E'], 'club_team_name': [None, None]
        })

        expected_matches['match_date'] = pd.to_datetime(
            expected_matches['match_date'])

        weekend_matches = self.acc_instance.get_weekend_matches(
            matches, saturday)

        self.assertEqual(weekend_matches.to_dict(), expected_matches.to_dict())

    def test_get_season_opposition_list(self):
        self.acc_instance.team_names = ['Team A', 'Team E', 'Team F']
        matches = pd.DataFrame({
            'match_date': ['2022-01-01', '2022-01-02', '2022-01-03'],
            'home_team_id': [1, 2, 3],
            'away_team_id': [4, 5, 6],
            'home_club_name': ['Team A', 'Team B', 'Team C'],
            'away_club_name': ['Team D', 'Team E', 'Team F']
        })

        expected_opposition_list = "Team D\nTeam B\nTeam C"

        opposition_list = self.acc_instance.get_season_opposition_list(matches)

        self.assertEqual(opposition_list, expected_opposition_list)

    def test_get_cutout_off_league_table(self):
        self.acc_instance.team_names = ['Team B']
        league_table = pd.DataFrame({
            'POSITION': ['1', '2', '3', '4', '5'],
            'TEAM': ['Team A', 'Team B', 'Team C', 'Team D', 'Team E'],
            'W': ['5', '4', '3', '2', '1'],
            'D': ['0', '1', '2', '3', '4'],
            'L': ['0', '1', '2', '3', '4'],
            'PTS': ['15', '13', '9', '7', '5']
        })

        expected_cutout = "1\nTeam A\n5\n0\n0\n15\n2\nTeam B\n4\n1\n1\n13\n3\nTeam C\n3\n2\n2\n9"

        cutout = self.acc_instance.get_cutout_off_league_table(
            league_table, n_teams=3)

        self.assertEqual(cutout, expected_cutout)

    @patch.object(pc, 'get_individual_stats_from_all_games')
    def test_get_season_stats_totals(self, mock_get_individual_stats):
        match_ids = [1, 2, 3]
        team_ids = [1, 2, 3]
        for_graphics = False
        n_players = 10

        # Mock the return value of _get_individual_stats_from_all_games
        mock_get_individual_stats.return_value = (
            pd.DataFrame({
                'initial_name': ['John', 'Alice'],
                'batsman_name': ['John Doe', 'Alice Smith'],
                'runs': [100, 50],
                'fours': [10, 5],
                'sixes': [5, 2],
                'balls': [100, 60],
                'not_out': [0, 0],
                'match_id': [1, 2],
                'how_out': ['b', 'lbw']
            }),
            pd.DataFrame({
                'initial_name': ['Bob', 'Eve'],
                'bowler_name': ['Bob Smith', 'Eve Johnson'],
                'bowler_id': [1, 2],
                'wickets': [5, 3],
                'balls': [60, 50],
                'maidens': [1, 0],
                'runs': [30, 20],
                'match_id': [1, 2]
            }),
            pd.DataFrame({
                'fielder_name': ['John Doe', 'Alice Smith', 'John Doe'],
                'fielder_id': [1, 2, 1],
                'match_id': [1, 2, 3]
            })
        )

        expected_batting = pd.DataFrame({
            'rank': [1, 2],
            'initial_name': ['John', 'Alice'],
            'batsman_name': ['John Doe', 'Alice Smith'],
            'runs': [100, 50],
            'fours': [10, 5],
            'sixes': [5, 2],
            'balls': [100, 60],
            'not_out': [0, 0],
            'match_id': [1, 1],
            'innings_to_count': [1, 1],
            'average': [100.0, 50.0]
        })
        expected_bowling = pd.DataFrame({
            'rank': [1, 2],
            'initial_name': ['Bob', 'Eve'],
            'bowler_name': ['Bob Smith', 'Eve Johnson'],
            'bowler_id': [1, 2],
            'wickets': [5, 3],
            'balls': [60, 50],
            'maidens': [1, 0],
            'runs': [30, 20],
            'match_id': [1, 1],
            'overs': ['10.0', '8.2']
        })

        expected_fielding = pd.DataFrame({
            'rank': [1, 2],
            'fielder_name': ['John Doe', 'Alice Smith'],
            'fielder_id': [1, 2],
            'dismissals': [2, 1],
            'n_games': [2, 1]
        })
        batting, bowling, fielding = self.acc_instance.get_alleyn_season_totals(
            match_ids, team_ids, for_graphics, n_players)

        # batting['runs'] = batting['runs'].astype('float')

        pd.testing.assert_frame_equal(batting, expected_batting)
        pd.testing.assert_frame_equal(bowling, expected_bowling)
        pd.testing.assert_frame_equal(fielding, expected_fielding)

    def test_extract_string_for_graphic(self):
        df = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': ['a', 'b', 'c'],
            'col3': [True, False, True]
        })

        expected_string = "1\na\nTrue\n2\nb\nFalse\n3\nc\nTrue\n"

        actual_string = self.acc_instance._extract_string_for_graphic(df)

        self.assertEqual(actual_string, expected_string)

    @patch.object(pc, 'get_individual_stats_from_all_games')
    def test_get_best_individual_performances(self, mock_get_individual_stats):
        match_ids = [1, 2, 3]
        team_ids = [1, 2, 3]
        n_players = 5
        for_graphics = False

        # Mock the return value of _get_individual_stats_from_all_games
        mock_get_individual_stats.return_value = (
            pd.DataFrame({
                'initial_name': ['John', 'Alice'],
                'batsman_name': ['John Doe', 'Alice Smith'],
                'runs': [100, 50],
                'fours': [10, 5],
                'sixes': [5, 2],
                'balls': [100, 60],
                'not_out': [0, 0],
                'match_id': [1, 2],
                'how_out': ['b', 'lbw']
            }),
            pd.DataFrame({
                'initial_name': ['Bob', 'Eve'],
                'bowler_name': ['Bob Smith', 'Eve Johnson'],
                'bowler_id': [1, 2],
                'wickets': [5, 3],
                'balls': [60, 50],
                'maidens': [1, 0],
                'runs': [30, 20],
                'match_id': [1, 2]
            }),
            pd.DataFrame({
                'fielder_name': ['John Doe', 'Alice Smith', 'John Doe'],
                'fielder_id': [1, 2, 1],
                'match_id': [1, 2, 3]
            })
        )

        expected_batting = pd.DataFrame({
            'initial_name': ['John', 'Alice'],
            'batsman_name': ['John Doe', 'Alice Smith'],
            'runs': [100, 50],
            'fours': [10, 5],
            'sixes': [5, 2],
            'balls': [100, 60],
            'not_out': [0, 0],
            'match_id': [1, 2],
            'how_out': ['b', 'lbw'],
        })

        expected_bowling = pd.DataFrame({
            'initial_name': ['Bob', 'Eve'],
            'bowler_name': ['Bob Smith', 'Eve Johnson'],
            'bowler_id': [1, 2],
            'wickets': [5, 3],
            'balls': [60, 50],
            'maidens': [1, 0],
            'runs': [30, 20],
            'match_id': [1, 2]
        })

        batting, bowling = self.acc_instance.get_best_individual_performances(
            match_ids, team_ids, n_players, for_graphics)

        pd.testing.assert_frame_equal(batting, expected_batting)
        pd.testing.assert_frame_equal(bowling, expected_bowling)

    def test_get_individual_performance_title(self):
        batting_data = {
            'initial_name': ['John', 'Alice'],
            'opposition_name': ['Team A', 'Team B']
        }
        expected_title = ['John vs Team A', 'Alice vs Team B']

        batting_df = pd.DataFrame(batting_data)

        result_df = self.acc_instance._get_individual_performance_title(
            batting_df)

        self.assertEqual(result_df['title'].tolist(), expected_title)

    @patch.object(acc, 'get_individual_stats')
    def test_get_individual_stats_from_all_games(self, mock_get_individual_stats):
        match_ids = [1, 2, 3]
        team_ids = [1, 2, 3]
        stat_string = "runs,wickets"

        # Mock the return value of get_individual_stats
        mock_get_individual_stats.side_effect = [
            (pd.DataFrame({'player_name': ['John'], 'runs': [100], 'balls': [80], 'team_id': [1]}), pd.DataFrame(
                {'player_name': ['Alice'], 'wickets': [5], 'balls': [30], 'runs': [300], 'team_id': [1]})),
            (pd.DataFrame({'player_name': ['Bob'], 'runs': [50], 'balls': [50], 'team_id': [1]}), pd.DataFrame(
                {'player_name': ['Eve'], 'wickets': [3], 'balls': [25], 'runs': [200], 'team_id': [1]})),
            (pd.DataFrame({'player_name': ['Charlie'], 'runs': [75], 'balls': [20], 'team_id': [1]}), pd.DataFrame(
                {'player_name': ['Dave'], 'wickets': [2], 'balls': [5], 'runs': [100], 'team_id': [1]}))
        ]

        expected_batting = pd.DataFrame({
            'player_name': ['John', 'Charlie', 'Bob'],
            'runs': [100, 75, 50],
            'balls': [80, 20, 50],
            'team_id': [1, 1, 1]
        })

        expected_bowling = pd.DataFrame({
            'player_name': ['Alice', 'Eve', 'Dave'],
            'wickets': [5, 3, 2],
            'balls': [30, 25, 5],
            'runs': [300, 200, 100],
            'team_id': [1, 1, 1]
        })

        batting, bowling, _ = self.acc_instance.get_individual_stats_from_all_games(
            match_ids, team_ids, stat_string)

        pd.testing.assert_frame_equal(batting, expected_batting)
        pd.testing.assert_frame_equal(bowling, expected_bowling)

    @patch.object(pc, '_get_players_used_in_match')
    def test_get_all_players_involved(self, mock_get_players_used_in_match):
        match_ids = [1, 2, 3]
        team_ids = [1, 2, 3]

        # Mock the return value of get_players_used_in_match
        mock_get_players_used_in_match.side_effect = [
            pd.DataFrame({
                'player_name': ['John Doe', 'Alice Smith'],
                'player_id': [1, 2],
                'team_id': [1, 2]
            }),
            pd.DataFrame({
                'player_name': ['Bob Johnson', 'Eve Brown'],
                'player_id': [3, 4],
                'team_id': [1, 3]
            }),
            pd.DataFrame({
                'player_name': ['Charlie Davis', 'Frank Wilson'],
                'player_id': [5, 6],
                'team_id': [2, 3]
            })
        ]

        expected_players = pd.DataFrame({
            'player_name': ['John Doe', 'Alice Smith', 'Bob Johnson', 'Eve Brown', 'Charlie Davis', 'Frank Wilson'],
            'player_id': [1, 2, 3, 4, 5, 6],
            'team_id': [1, 2, 1, 3, 2, 3]
        })

        players = self.acc_instance.get_all_players_involved(
            match_ids, team_ids)

        pd.testing.assert_frame_equal(players, expected_players)
