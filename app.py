import dash
import dash_core_components as dcc
import dash_html_components as html

import base64
# import matplotlib
import datetime
import json  # needed implicitly
from matplotlib import cm
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import requests


# style sheet and dictionary for style elements
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
colors = {'background': '#5369CA',
          'header': "#FFFFFF",
          'text': '#000000'}

# start application
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

# dictionaries translating bus route_id acronyms to boroughs
dic_borough = {"M": "Manhattan", "Bx": "Bronx", "B": "Brooklyn", "Q": "Queens",
               "S": "Staten Island", "SIM": "Express to Manhattan"}
inv_dic_borough = {v: k for k, v in dic_borough.items()}


def create_boroughs(ddf):
    """Add boolean columns for whether a route is in a specific borough"""
    new = ddf.copy()
    new["M"] = new.route_id.str.contains('M', regex=False)
    new["S"] = new.route_id.str.contains(r'^S\d+')
    new["Bx"] = new.route_id.str.contains('Bx', regex=False)
    new["Q"] = new.route_id.str.contains('Q', regex=False)
    new["B"] = new.route_id.str.contains(r"^B([A-Z]|\d)")
    new["SIM"] = new.route_id.str.contains(r"^SIM")
    return new

# have to load data first for setting ranges, etc. in buttons
df = pd.read_csv('data.csv', index_col=0, parse_dates=True)
# add borough
df = create_boroughs(df)
# reformat timestamp
timestamp = "%Y-%m-%d %H:%M:%S"
df["timestamp"] = pd.to_datetime(df["timestamp"], format=timestamp)
df["hour"] = df["timestamp"].dt.hour

app.layout = html.Div([

    # creating sidebar
    html.Div([
        html.H1(html.A('MTA Bus Times', title="Go to MTA Wiki",
                       href="http://bustime.mta.info/wiki/Developers/Index/",
                       style={'color': colors['header']}),
                style={
                    'textAlign': 'center',
                    'color': colors['header'],
                    'backgroundColor':colors['background']}
                ),

        html.H3("Controls for live data",
                style={'padding-top': '20px', 'padding-left': '20px'}),

        html.Div(
            [html.P(id='button-clicks'),

                html.Button('Click to refresh', id='button',
                            style={'textAlign': 'center', 'padding-left': '50px',
                                   "color": colors['header'], 'width': '80%',
                                   "display": "inline-block"}),

                html.P("NOTE: Refreshing takes several seconds.",
                       style={"font-size": '10', 'padding-top': '10px'})],
            style={'padding-left': '20px', 'width': '90%'}
        ),

        html.H3("Controls for historic data",
                style={'padding-top': '40px', 'padding-left': '20px'}),
        # ---- date range for historic data ----
        html.Div(
            dcc.DatePickerRange(
                id='date-range',
                min_date_allowed=df.timestamp.min(),
                max_date_allowed=df.timestamp.max(),
                initial_visible_month=df.timestamp.min(),
                start_date=df.timestamp.min(),
                end_date=df.timestamp.max()
            ), style={'padding-left': '20px', 'width': '90%'}
        ),

        # ---- time range for historic data ----
        html.H5("Hour range",
                style={'padding-top': '25px', 'padding-left': '20px'}),
        html.Div(
            dcc.RangeSlider(
                id='hour-slider',
                min=0,
                max=24,
                value=[0, 24],
                allowCross=False,
                marks={str(h): {'label': str(h),
                                'style': {'color': colors["header"]}} for h in np.arange(0, 24, 4)}),
            style={'width': '90%', 'padding-left': '20px', "color": colors['header']}),

        # ---- how to group historic data ----
        html.H5("Minutes to group data in",
                style={'padding-top': '40px', 'padding-left': '20px'}),
        dcc.RadioItems(id="time-div",
                       options=[{'label': '15', 'value': 15},
                                {'label': '30', 'value': 30},
                                {'label': '45', 'value': 45},
                                {'label': '60', 'value': 60}],
                       value=15, style={'padding-left': '20px'},
                       labelStyle={'display': 'inline-block', 'width': '32px'}),


        # ---- route related elements ----
        html.H5("Match routes within a borough",
                style={'padding-top': '20px', 'padding-left': '20px'}),

        html.P("May be mis-match between datasets due to changes to routes\
            If active, matches live routes with those in historic data",
               style={"font-size": '10', 'padding-left': '20px',
                      'padding-right': '20px'}),

        dcc.RadioItems(id="route-match",
                       options=[{'label': 'yes', 'value': 1},
                                {'label': 'no', 'value': 0}],
                       value=1, style={'padding-left': '20px'},
                       labelStyle={'display': 'inline-block', 'width': '32px'})],
        style={'color': colors["header"], 'backgroundColor': colors['text'],
               'width': '20%', 'height':'100vh', 'position': 'fixed'},
        className="six columns"),

    # html.Div([dcc.Graph(id='time-of-day-graph'),

    #           dcc.Graph(id='violin-plot', style={'padding-top': '30px'}),

    #           html.P("Points (live data) and violins (historic data) are \
    #             grouped in the legend by borough.",
    #                  style={"font-size": '15', 'padding-left': '30px'}),

    #           html.Div([
    #               html.Div([dcc.Graph(id='graph-1')],
    # style={'textAlign': 'center', 'padding-top': '30px'}),

    #               html.Div(dcc.Slider(id="show-me",
    #                                   min=0,
    #                                   max=24,
    #                                   value=0,
    #                                   marks={str(h): {'label': "%s:00" % h} for h in np.arange(0, 24, 1)}),
    #                        style={'textAlign': 'center', 'width': "85%"})], style={'textAlign': 'center'})
    #           ],
    #          style={'width': "95%", 'display': 'inline-block',
    #                 'textAlign': 'center', 'padding-left': '21%'},
    #          className="six columns"
    #          )
])


if __name__ == '__main__':
    # create iterator
    app.run_server(debug=True)
