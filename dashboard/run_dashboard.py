from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import streamlit as st
# from playcric import alleyn, playcricket
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append('../')
from playcric import alleyn, playcricket
from dashboard_utils import get_opposition_players, get_opposition_fixtures

opposition_players = pd.DataFrame()
get_stats = None
# import os
# import clipboard
# import pyperclip
# from bokeh.models.widgets import
# from load_data import get_all_ball_by_ball_data, get_most_balls_faced
# import matplotlib.pyplot as plt
# import math
# from dashboard_utils import get_player_stats
st.set_page_config(layout="wide")

st.title("PlayCricket Badger")
FIXTURE_COLUMNS = ['league_name','competition_name','competition_type','match_date', 'home_club_name','home_team_name', 'away_club_name', 'away_team_name']

fixtures = pd.DataFrame(columns=FIXTURE_COLUMNS)
# st.session_state.fixtures = fixtures
# ALL_APPEARANCES_FILE_PATH = './data/all_appearances.pkl'
# HOLE_CONFIG_FILE_PATH = './data/hole_config.csv'
fixtures_dataframe = st.empty()
fixtures_dataframe.selection = None
# st.session_state.copied = []
# st.session_state.fixtures = fixtures
# st.session_state.selection = None

# st.session_state.fixtures_dataframe = fixtures

def callback():
    with st.sidebar:
        st.write("**Callback called**")
        st.write(fixtures_dataframe.selection)

with st.form("club_input_form", border=True):
    st.subheader('Input your club details')
    st.session_state.club_site_id = st.text_input('Club Site ID')
    st.session_state.api_key = st.text_input('Club API Key')
    st.session_state.team_ids = st.text_input(
        'Team IDs (comma-separated, e.g., 12345,67890)', value=None)
    st.session_state.season_number = st.text_input(
        'Specify Season', value=datetime.today().year)
    submitted_club_details = st.form_submit_button('Input Club Details')

# if submitted_club_details:
if not (st.session_state.club_site_id and st.session_state.api_key):
    st.error("Please enter both Club Site ID and API Key.")

alleyn_object = alleyn.acc(api_key=st.session_state.api_key, site_id=st.session_state.club_site_id)
if st.session_state.team_ids:
    st.write("Team IDs provided:", st.session_state.team_ids)
    alleyn_object.team_ids = [int(team_id.strip()) for team_id in st.session_state.team_ids.split(',') if team_id.strip().isdigit()]

if 'fixtures' not in st.session_state.keys() and submitted_club_details:
    st.session_state.fixtures = alleyn_object.get_all_matches(season=st.session_state.season_number, team_ids=alleyn_object.team_ids).sort_values(by='match_date', ascending=True)

if 'fixtures' in st.session_state.keys():
    fixtures_dataframe = st.dataframe(
        st.session_state.fixtures[FIXTURE_COLUMNS],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

get_opposition_team_sheet = st.button("Get opposition team sheet", type="primary")

if 'fixtures' in st.session_state.keys():
    if fixtures_dataframe.selection.rows and get_opposition_team_sheet:
        st.session_state.selected_fixture = fixtures_dataframe.selection.rows[0]
        st.session_state.selected_fixture_dataframe = st.session_state.fixtures.iloc[st.session_state.selected_fixture]
        st.write("Selected Fixture Details:")
        st.write(f"{st.session_state.selected_fixture_dataframe['home_club_name']} ({st.session_state.selected_fixture_dataframe['home_team_name']}) vs {st.session_state.selected_fixture_dataframe['away_club_name']} ({st.session_state.selected_fixture_dataframe['away_team_name']})")
        st.session_state.match_id = st.session_state.selected_fixture_dataframe['id']
        st.session_state.home_club_id = st.session_state.selected_fixture_dataframe['home_club_id']
        st.session_state.away_club_id = st.session_state.selected_fixture_dataframe['away_club_id']
        st.session_state.opposition_players, st.session_state.opposition_player_ids = get_opposition_players(alleyn_object, st.session_state.match_id)
        # print(f"Opposition Players: {st.session_state.opposition_players}")
        if not st.session_state.opposition_players.empty:
            st.write("Opposition Players:")
            st.dataframe(st.session_state.opposition_players[['player_id', 'player_name']].sort_values(by='player_name'), use_container_width=False, hide_index=True)

# if not opposition_players.empty:
get_stats = st.button("Get opposition stats", type="primary")

if get_stats:
    if st.session_state.opposition_players.empty:
        st.error("No opposition players found. Please select a fixture first.")
        st.stop()
    st.write('Getting opposition stats...')

    st.session_state.oppo_club_id = int(st.session_state.away_club_id) if int(st.session_state.home_club_id) == int(st.session_state.club_site_id) else int(st.session_state.home_club_id)
    # print('Getting opposition stats for club ID:', oppo_club_id)
    st.write(f"Getting stats for opposition club ID: {st.session_state.oppo_club_id}")
    st.session_state.oppo_fixtures = get_opposition_fixtures(alleyn_object, st.session_state.oppo_club_id)
    st.write("Opposition Fixtures acuiqred")
    st.session_state.all_team_sheets = alleyn_object.get_all_players_involved(match_ids=st.session_state.oppo_fixtures['id'].unique().tolist())

    st.session_state.relevant_matches = st.session_state.all_team_sheets.loc[st.session_state.all_team_sheets['player_id'].isin(st.session_state.opposition_player_ids)]

    st.session_state.bat, st.session_state.bowl, st.session_state.field = alleyn_object.get_stat_totals(match_ids=st.session_state.relevant_matches['match_id'].unique(), group_by_team=True)

    st.session_state.bat['batsman_id'] = st.session_state.bat['batsman_id'].astype(int)
    st.session_state.bat = st.session_state.bat.loc[st.session_state.bat['batsman_id'].isin(st.session_state.opposition_player_ids)]

    st.session_state.bowl['bowler_id'] = st.session_state.bowl['bowler_id'].astype(int)
    st.session_state.bowl = st.session_state.bowl.loc[st.session_state.bowl['bowler_id'].isin(st.session_state.opposition_player_ids)]
    st.session_state.home_team_name_lookup = st.session_state.oppo_fixtures[['home_team_id','home_team_name']].rename(columns={'home_team_id':'team_id', 'home_team_name':'team_name'})
    st.session_state.away_team_name_lookup = st.session_state.oppo_fixtures[['away_team_id','away_team_name']].rename(columns={'away_team_id':'team_id', 'away_team_name':'team_name'})
    st.session_state.team_name_lookup = pd.concat([st.session_state.home_team_name_lookup, st.session_state.away_team_name_lookup], ignore_index=True).drop_duplicates()
    st.session_state.bowl = st.session_state.bowl.merge(st.session_state.team_name_lookup, how='left', left_on='team_id', right_on='team_id')
    st.session_state.bat = st.session_state.bat.merge(st.session_state.team_name_lookup, how='left', left_on='team_id', right_on='team_id')

    def print_and_add_to_string_header(text, all_stats_string):
        st.header(text)
        all_stats_string += str(text) + '\n'
        return all_stats_string
    
    def print_and_add_to_string_subheader(text, all_stats_string):
        st.subheader(text)
        all_stats_string += str(text) + '\n'
        return all_stats_string
    
    def print_and_add_to_string_text(text, all_stats_string):
        st.write(text)
        all_stats_string += str(text) + '\n'
        return all_stats_string
    
    st.title("Opposition Player Stats")
    st.session_state.all_stats_string = ''
    st.session_state.all_stats_string = print_and_add_to_string_header("\n" + "="*50 + "\n", st.session_state.all_stats_string)
    for player in st.session_state.opposition_players.sort_values('position')['player_id'].unique():
        oppo_player_info = st.session_state.opposition_players.loc[st.session_state.opposition_players['player_id'] == player].iloc[0]
        player_name = f"{oppo_player_info['player_name']}"
        if oppo_player_info['captain']:
            player_name += " (C)"
        if oppo_player_info['wicket_keeper']:
            player_name += " (WK)"
        player_bat = st.session_state.bat.loc[st.session_state.bat['batsman_id'] == player].sort_values(['match_id', 'runs'], ascending=[True, True])
        player_bowl = st.session_state.bowl.loc[st.session_state.bowl['bowler_id'] == player].sort_values(['match_id', 'overs'], ascending=[True, True])
        st.session_state.all_stats_string = print_and_add_to_string_header(f'Stats for Player {player_name}', st.session_state.all_stats_string)
        st.session_state.all_stats_string = print_and_add_to_string_subheader(f'They are carded to bat at position {oppo_player_info["position"]}', st.session_state.all_stats_string)

        if not player_bat.empty:
            st.session_state.all_stats_string = print_and_add_to_string_header(f"Batting -------------:", st.session_state.all_stats_string)
            st.session_state.all_stats_string = print_and_add_to_string_text(player_bat[['team_name','match_id', 'runs', 'average', 'top_score']], st.session_state.all_stats_string)
        
        if not player_bowl.empty:
            st.session_state.all_stats_string = print_and_add_to_string_header(f"\nBowling -------------:", st.session_state.all_stats_string)
            st.session_state.all_stats_string = print_and_add_to_string_text(player_bowl[['team_name','match_id', 'overs', 'maidens', 'runs', 'wickets','average']], st.session_state.all_stats_string)
        
        st.session_state.all_stats_string = print_and_add_to_string_header("\n" + "="*50 + "\n", st.session_state.all_stats_string)