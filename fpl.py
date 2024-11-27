import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# Fetch FPL data with caching
@st.cache_data
def fetch_fpl_data():
    fpl_url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    response = requests.get(fpl_url)
    fpl_data = response.json()

    # Extract player and team data
    players = pd.DataFrame(fpl_data['elements'])
    teams = pd.DataFrame(fpl_data['teams'])

    # Add new fields
    players['selected_by_percent'] = pd.to_numeric(players['selected_by_percent'], errors='coerce')
    players['points_per_game'] = pd.to_numeric(players['points_per_game'], errors='coerce')
    players['points_per_million'] = players['total_points'] / (players['now_cost'] / 10)
    players['price_m'] = players['now_cost'] / 10

    # Map team names and merge team strength
    teams_mapping = teams[['id', 'name', 'strength_attack_home', 'strength_defence_away']]
    players = players.merge(teams_mapping, left_on='team', right_on='id', how='left')
    players['team_name'] = players['name']
    players['position'] = players['element_type'].map({1: 'Goalkeeper', 2: 'Defender', 3: 'Midfielder', 4: 'Forward'})

    return players, teams

players, teams = fetch_fpl_data()

# Fetch fixture data
@st.cache_data
def fetch_fixtures():
    fixtures_url = "https://fantasy.premierleague.com/api/fixtures/"
    response = requests.get(fixtures_url)
    fixtures = pd.DataFrame(response.json())
    return fixtures

fixtures = fetch_fixtures()

# App title
st.title("FPL Dashboard")

# Sidebar filters
st.sidebar.header("Filters")
selected_positions = st.sidebar.multiselect("Select Positions", options=players['position'].unique(), default=players['position'].unique())
selected_teams = st.sidebar.multiselect("Select Teams", options=players['team_name'].unique(), default=players['team_name'].unique())
max_price = st.sidebar.slider("Select Maximum Price (in £M)", min_value=float(players['price_m'].min()), max_value=float(players['price_m'].max()), value=float(players['price_m'].max()))

# Apply filters
filtered_players = players[
    (players['position'].isin(selected_positions)) &
    (players['team_name'].isin(selected_teams)) &
    (players['price_m'] <= max_price)
]

# Ensure required columns are numeric
numeric_columns = ['ict_index', 'points_per_game', 'form', 'points_per_million']
for col in numeric_columns:
    if col in filtered_players.columns:
        filtered_players[col] = pd.to_numeric(filtered_players[col], errors='coerce').fillna(0)
    else:
        filtered_players[col] = 0  # Add column with default value

# Tabs for insights
tabs = st.tabs(["Captain Picks", "Differential Players", "Set-Piece Takers", "Value Picks", "Form vs Fixture Difficulty", "Fixture Difficulty Heatmap"])

# Tab 1: Captain Picks
with tabs[0]:
    st.subheader("Top 10 Captain Picks")
    filtered_players['captaincy_score'] = filtered_players['form'] + filtered_players['ict_index']
    top_captains = filtered_players.nlargest(10, 'captaincy_score')
    fig = px.bar(
        top_captains,
        x='captaincy_score',
        y='web_name',
        orientation='h',
        color='captaincy_score',
        title="Top 10 Captain Picks",
        labels={'web_name': 'Player', 'captaincy_score': 'Captaincy Score'},
        color_continuous_scale='Reds'
    )
    fig.update_layout(yaxis=dict(categoryorder='total ascending'))
    st.plotly_chart(fig)

# Tab 2: Differential Players
with tabs[1]:
    st.subheader("Top 10 Differential Players")
    filtered_players['differential_score'] = filtered_players['points_per_game'] * (1 - (filtered_players['selected_by_percent'] / 100))
    top_differentials = filtered_players.nlargest(10, 'differential_score')
    fig = px.bar(
        top_differentials,
        x='differential_score',
        y='web_name',
        orientation='h',
        color='differential_score',
        title="Top 10 Differential Players",
        labels={'web_name': 'Player', 'differential_score': 'Differential Score'},
        color_continuous_scale='Blues'
    )
    fig.update_layout(yaxis=dict(categoryorder='total ascending'))
    st.plotly_chart(fig)

# Tab 3: Set-Piece Takers
with tabs[2]:
    st.subheader("Top 10 Set-Piece Takers (ICT Index)")
    top_set_piece = filtered_players.nlargest(10, 'ict_index')
    fig = px.bar(
        top_set_piece,
        x='ict_index',
        y='web_name',
        orientation='h',
        color='ict_index',
        title="Top 10 Set-Piece Takers",
        labels={'web_name': 'Player', 'ict_index': 'ICT Index'},
        color_continuous_scale='Greens'
    )
    fig.update_layout(yaxis=dict(categoryorder='total ascending'))
    st.plotly_chart(fig)

# Tab 4: Value Picks
with tabs[3]:
    st.subheader("Top 10 Value Picks (Points per Million)")
    top_value_picks = filtered_players.nlargest(10, 'points_per_million')
    fig = px.bar(
        top_value_picks,
        x='points_per_million',
        y='web_name',
        orientation='h',
        color='points_per_million',
        title="Top 10 Value Picks",
        labels={'web_name': 'Player', 'points_per_million': 'Points per Million'},
        color_continuous_scale='Purples'
    )
    fig.update_layout(yaxis=dict(categoryorder='total ascending'))
    st.plotly_chart(fig)

# Tab 5: Form vs Fixture Difficulty
with tabs[4]:
    st.subheader("Form vs Fixture Difficulty")
    
    filtered_players['fixture_difficulty'] = filtered_players.apply(
        lambda x: (x['strength_attack_home'] + x['strength_defence_away']) / 2 if pd.notnull(x['strength_attack_home']) else 0, axis=1
    )
    filtered_players['points_per_million'] = filtered_players['points_per_million'].apply(lambda x: max(x, 0))
    fig = px.scatter(
        filtered_players,
        x='fixture_difficulty',
        y='form',
        size='points_per_million',
        color='points_per_million',
        hover_name='web_name',
        title="Form vs Fixture Difficulty",
        labels={'fixture_difficulty': 'Fixture Difficulty', 'form': 'Form'},
        color_continuous_scale='Blues'
    )
    st.plotly_chart(fig)

# Tab 6: Fixture Difficulty Heatmap
#with tabs[5]:
    #st.subheader("Fixture Difficulty Heatmap")

    #def calculate_position_fdr(team, position):
        #team_fixtures = fixtures[(fixtures['team_h'] == team) | (fixtures['team_a'] == team)].head(5)
        #if not team_fixtures.empty:
            #if position in ['Defender', 'Goalkeeper']:
                #fdr = team_fixtures.apply(
                    #lambda row: row['difficulty_h'] if row['team_a'] == team else row['difficulty_a'], axis=1
                #)
            #elif position in ['Midfielder', 'Forward']:
                #fdr = team_fixtures.apply(
                    #lambda row: row['difficulty_a'] if row['team_a'] == team else row['difficulty_h'], axis=1
                #)
            #else:
                #fdr = pd.Series([0])
        #else:
            #fdr = pd.Series([0])
        #return fdr.mean()

    #filtered_players['fixture_difficulty'] = filtered_players.apply(
        #lambda x: calculate_position_fdr(x['team_name'], x['position']), axis=1
    #)
    #heatmap_data = filtered_players.pivot_table(
        #index='team_name',
        #columns='position',
        #values='fixture_difficulty',
        #aggfunc='mean'
    #).fillna(0)
    #st.dataframe(heatmap_data.style.background_gradient(cmap="coolwarm"))






