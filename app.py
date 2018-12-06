
import dash
import dash_core_components as dcc
import dash_html_components as html

import numpy as np
import pandas as pd
import plotly.graph_objs as go


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# have to load data first for setting ranges, etc. in buttons
df = pd.read_csv('data.csv', index_col=0, parse_dates=True)

# reformat timestamp
timestamp = "%Y-%m-%d %H:%M:%S"
df["timestamp"] = pd.to_datetime(df["timestamp"], format=timestamp)
df["hour"] = df["timestamp"].dt.hour

colors = {'background': '#5369CA',
          'header': "#FFFFFF",
          'text': '#000000'}

server = app.server

app.layout = html.Div([

    # creating sidebar
    html.Div([
        html.H1('MTA Bus Times',
                style={
                    'textAlign': 'center',
                    'color': colors['header'],
                    'backgroundColor':colors['background']}
                ),

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
                                'style': {'color': colors["header"]}} for h in np.arange(0, 24, 4)}
            ), style={'width': '90%', 'padding-left': '20px',
                      "color": colors['header']}),

        html.H5("Minutes to group data in",
                style={'padding-top': '40px', 'padding-left': '20px'}),
        dcc.RadioItems(
            id="time-div",
            options=[{'label': '15', 'value': 15},
                     {'label': '30', 'value': 30},
                     {'label': '45', 'value': 45},
                     {'label': '60', 'value': 60}],
            value=15, labelStyle={'display': 'inline-block', 'width': '32px'},
            style={'padding-left': '20px'})

    ], style={'color': colors["header"], 'backgroundColor': colors['text'],
              'width': '20%', 'height':'100vh'},
        className="six columns"),

    html.Div([dcc.Graph(id='time-of-day-graph')], style={'width': '40%'},
             className="six columns"
             ),
])


def get_selected_data(hours, start_date, end_date, time_div):
    # apply start and end date criteria from date range picker
    # and hour criteria
    sel_mask = (df["timestamp"] >= pd.to_datetime(start_date)) & \
        (df["timestamp"] <= pd.to_datetime(end_date)) & \
        (df["hour"] >= hours[0]) & (df["hour"] <= hours[1])
    sel_data = df[sel_mask].copy()

    # want to only count unique vehicle ids in the time window with
    sampled = sel_data.resample("%sMin" % time_div, on="timestamp")[
        "vehicle_id"].nunique()
    # easiest way to return to a pandas dataframe
    sampled = sampled.reset_index()

    # create hour for groupby
    sampled["hhmmss"] = sampled["timestamp"].apply(lambda x: x.time())
    sampled["hh"] = sampled["timestamp"].apply(lambda x: "%i:00" % (x.hour))
    dff = sampled.groupby("hhmmss", as_index=False).agg({"vehicle_id": 'sum',
                                                         "hh": 'first',
                                                         'timestamp': 'first'})
    dff = dff.sort_values("timestamp")
    return dff


@app.callback(
    dash.dependencies.Output('time-of-day-graph', "figure"),
    [dash.dependencies.Input("hour-slider", "value"),
     dash.dependencies.Input("date-range", 'start_date'),
     dash.dependencies.Input("date-range", 'end_date'),
     dash.dependencies.Input("time-div", 'value')])
def daily_graph(hours, start_date, end_date, time_div):
    dff = get_selected_data(hours, start_date, end_date, time_div)

    trace = go.Scatter(x=dff["timestamp"].astype(str),
                       y=dff["vehicle_id"],
                       mode='markers+lines')

    layout = go.Layout(title="Daily activity of vehicles",
                       titlefont=dict(size=30),
                       xaxis=dict(title='Time of day',
                                  titlefont=dict(size=20),
                                  tickangle=-45,
                                  tickfont=dict(size=15),
                                  nticks=10,
                                  tickformat="%H:%M"),
                       yaxis=dict(title='Number of active vehicles',
                                  titlefont=dict(size=20),
                                  tickfont=dict(size=15),
                                  dtick=np.round(
                                      dff["vehicle_id"].max() // 10 * 2, -2)
                                  ))

    return {"data": [trace], 'layout': layout,
            'style': {'width': '40%', 'padding-left': '25px',
                      'display': 'inline-block'}}


if __name__ == '__main__':
    app.run_server(debug=True)
