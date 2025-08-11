import streamlit as st
import clipboard


def on_copy_click(text):
    st.session_state.copied.append(text)
    clipboard.copy(text)

def get_opposition_players(alleyn_object, match_id):
    players = alleyn_object.get_all_players_involved([match_id])
    opposition_players = players.loc[~players['team_id'].isin(alleyn_object.team_ids)]
    opposition_player_ids = opposition_players['player_id'].unique()
    return opposition_players, opposition_player_ids

def get_opposition_fixtures(alleyn_object, oppo_club_id):
    oppo_fixtures = alleyn_object.get_all_matches(season=st.session_state.season_number, site_id=oppo_club_id)
    oppo_fixtures['saturday_game'] = oppo_fixtures['match_date'].dt.strftime('%A') == 'Saturday'
    oppo_fixtures = oppo_fixtures[oppo_fixtures['saturday_game']]
    oppo_fixtures = oppo_fixtures.loc[oppo_fixtures['game_type'] == 'Standard']
    oppo_fixtures = oppo_fixtures.loc[oppo_fixtures['competition_type'] == 'League']
    return oppo_fixtures