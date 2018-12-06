
import dash
import dash_core_components as dcc
import dash_html_components as html

import json
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import requests

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# have to load data first for setting ranges, etc. in buttons
df = pd.read_csv('data.csv', index_col=0, parse_dates=True)
live = pd.read_csv("live.csv", index_col=0, parse_dates=True)

# reformat timestamp
timestamp = "%Y-%m-%d %H:%M:%S"
df["timestamp"] = pd.to_datetime(df["timestamp"], format=timestamp)
df["hour"] = df["timestamp"].dt.hour

# restrict routes to those visible in historic data
routes = df["route_id"].unique()

colors = {'background': '#5369CA',
          'header': "#FFFFFF",
          'text': '#000000'}

server = app.server

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
                                   "display": "inline-block"})],
            style={'padding-left': '20px', 'width': '90%'}
        ),

        html.H3("Controls for 2015 data",
                style={'padding-top': '40px', 'padding-left': '20px'}),
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

    html.Div([dcc.Graph(id='time-of-day-graph'),
              dcc.Graph(id='box-plot')],
             style={'width': "75%", 'height': '800px', 'padding-left': '20px',
                    'display': 'inline-block'},
             className="six columns"
             )
])


def _flatten_dict(root_key, nested_dict, flattened_dict):
    for key, value in nested_dict.items():
        next_key = root_key + "_" + key if root_key != "" else key
        if isinstance(value, dict):
            _flatten_dict(next_key, value, flattened_dict)
        else:
            flattened_dict[next_key] = value
    return flattened_dict

# This is useful for the live MTA Data
params = {"key": "19faff8a-c061-4c7e-8dc4-63685ab24123", "MaximumStopVisits": 2}


def nyc_current():
    resp = requests.get(
        "http://bustime.mta.info/api/siri/vehicle-monitoring.json", params=params).json()
    info = resp['Siri']['ServiceDelivery'][
        'VehicleMonitoringDelivery'][0]['VehicleActivity']
    return pd.DataFrame([_flatten_dict('', i, {}) for i in info])


@app.callback(
    dash.dependencies.Output('button-clicks', 'children'),
    [dash.dependencies.Input('button', 'n_clicks')])
def clicks(n_clicks):
    if n_clicks is not None:
        current = nyc_current()
        sel_curr = current[['RecordedAtTime',
                            'MonitoredVehicleJourney_VehicleRef',
                            "MonitoredVehicleJourney_PublishedLineName",
                            'MonitoredVehicleJourney_VehicleLocation_Latitude',
                            'MonitoredVehicleJourney_VehicleLocation_Longitude']]
        sel_curr = sel_curr.rename(index=str,
                                   columns={
                                       'RecordedAtTime': "timestamp",
                                       'MonitoredVehicleJourney_VehicleRef': "vehicle_id",
                                       "MonitoredVehicleJourney_PublishedLineName": "route_id",
                                       'MonitoredVehicleJourney_VehicleLocation_Latitude': "latitude",
                                       'MonitoredVehicleJourney_VehicleLocation_Longitude': "longitude"})
        sel_curr["timestamp"] = pd.to_datetime(sel_curr["timestamp"])
        sel_curr.to_csv("live.csv")
        global live
        live = sel_curr

        return 'Live data has been refreshed {} times'.format(n_clicks)
    else:
        return "Using last saved version of live data."


def get_selected_data(hours, start_date, end_date, time_div):
    # apply start and end date criteria from date range picker
    # and hour criteria
    sel_mask = (df["timestamp"] >= pd.to_datetime(start_date)) & \
        (df["timestamp"] <= pd.to_datetime(end_date)) & \
        (df["hour"] >= hours[0]) & (df["hour"] <= hours[1])
    sel_data = df[sel_mask].copy()

    # want to only count unique vehicle ids in the time window with
    sampled = sel_data.resample("%sMin" % time_div,
                                on="timestamp").agg({"vehicle_id": "nunique",
                                                     "route_id": "first"})
    # easiest way to return to a pandas dataframe
    sampled = sampled.reset_index()

    # create hour for groupby
    sampled["hhmmss"] = sampled["timestamp"].apply(lambda x: x.time())
    sampled["hh"] = sampled["timestamp"].apply(lambda x: "%i:00" % (x.hour))
    dff = sampled.groupby("hhmmss", as_index=False).agg({"vehicle_id": 'sum',
                                                         "hh": 'first',
                                                         "route_id": 'first'})
    dff["timestamp"] = dff["hhmmss"].apply(lambda x: "2015-09-12 %s" % x)
    dff = dff.sort_values("timestamp")
    dff = dff[dff.vehicle_id > 0]

    # match routes from historic data in live
    sel_mask = (live.route_id.isin(routes))
    sel_live = live[sel_mask].copy()
    # live sample will always be short (~3 min so no resampling)
    min_time = pd.to_datetime(sel_live.timestamp.min())
    max_time = pd.to_datetime(sel_live.timestamp.max())
    duration = ((max_time - min_time).seconds) // 60
    count = sel_live.vehicle_id.nunique()
    time = "2015-09-12 %s:00" % pd.to_datetime(min_time).hour
    d = {'timestamp': [time], 'vehicle_id': [count]}
    curr = pd.DataFrame(data=d)

    return dff, curr, duration


@app.callback(
    dash.dependencies.Output('time-of-day-graph', "figure"),
    [dash.dependencies.Input("hour-slider", "value"),
     dash.dependencies.Input("date-range", 'start_date'),
     dash.dependencies.Input("date-range", 'end_date'),
     dash.dependencies.Input("time-div", 'value')])
def daily_graph(hours, start_date, end_date, time_div):
    dff, curr, dur = get_selected_data(hours, start_date, end_date, time_div)

    days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
    trace = go.Scatter(x=dff["timestamp"].astype(str),
                       y=dff["vehicle_id"] / days,
                       mode='markers+lines',
                       name='2015 data: %i min' % time_div,
                       marker={'size': 8})

    trace1 = go.Scatter(x=curr["timestamp"].astype(str),
                        y=curr["vehicle_id"],
                        mode='markers+lines',
                        name='Live data: %i min' % dur,
                        marker={'size': 8})

    layout = go.Layout(title="Daily activity of vehicles",
                       titlefont=dict(size=30),
                       height=500,
                       xaxis=dict(title='Time of day',
                                  titlefont=dict(size=20),
                                  tickangle=-45,
                                  tickfont=dict(size=15),
                                  nticks=10,
                                  tickformat="%H:%M"),
                       yaxis=dict(title='Number of active vehicles',
                                  titlefont=dict(size=20),
                                  tickfont=dict(size=15),
                                  ))

    return {"data": [trace, trace1], 'layout': layout,
            'style': {'width': '40%', 'padding-left': '25px',
                      'display': 'inline-block'}}


def create_boroughs(ddf):
    new = ddf.copy()
    new["M"] = new.route_id.str.contains('M', regex=False)
    new["S"] = new.route_id.str.contains(r'^S\d+')
    new["Bx"] = new.route_id.str.contains('Bx', regex=False)
    new["Q"] = new.route_id.str.contains('Q', regex=False)
    new["B"] = new.route_id.str.contains(r"^B([A-Z]|\d)")
    new["SIM"] = new.route_id.str.contains(r"^SIM")
    return new


@app.callback(
    dash.dependencies.Output('box-plot', "figure"),
    [dash.dependencies.Input("hour-slider", "value"),
     dash.dependencies.Input("date-range", 'start_date'),
     dash.dependencies.Input("date-range", 'end_date'),
     dash.dependencies.Input("time-div", 'value')])
def box_plot(hours, start_date, end_date, time_div):

    boroughs = {"M": "Manhattan", "Bx": "Bronx", "B": "Brooklyn",
                "S": "Staten Island", "Q": "Queens", "SIM": "Express to Manhattan"}

    dff, _, _ = get_selected_data(hours, start_date, end_date, time_div)
    dff = create_boroughs(dff)

    curr = create_boroughs(live)

    days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days

    traces = []
    shown = [False, False]
    for it, col in enumerate(["M", "S", "Bx", "Q", "B", "SIM"]):
        if any(dff[col]):
            temp = dff[dff[col]].vehicle_id / days
            trace = {"type": 'violin',
                     "x": [boroughs[col]] * temp.shape[0],
                     "y": temp,
                     "bandwidth": 20,
                     'name': "2015 data",
                     "showlegend": False if shown[0] else True,
                     "box": {"visible": True},
                     "meanline": {"visible": True}}
            shown[0] = True
            traces.append(trace)

            if any(curr[col]):
                routes2 = dff[dff[col]].route_id.unique()
                temp = curr[curr[col]]
                mask = (temp.route_id.isin(routes2))
                count = temp[mask].vehicle_id.nunique()

                trace = go.Scatter(x=[boroughs[col]],
                                   y=[count],
                                   mode='markers',
                                   name='Live data',
                                   showlegend=False if shown[1] else True,
                                   marker={'size': 8})
                shown[1] = True
                traces.append(trace)
        else:
            if any(curr[col]):
                count = curr[curr[col]].vehicle_id.nunique()
                trace = go.Scatter(x=[boroughs[col]],
                                   y=[count],
                                   mode='markers',
                                   name='Live data',
                                   showlegend=False if shown[1] else True,
                                   marker={'size': 8})
                shown[1] = True
                traces.append(trace)
    return {"data": traces, "layout": {"title": "",
                                       "violinmode": "group"}}
    # temp =
    # xs.append()
    # ys.append(temp)
    # print("ok")

    # group_curr = curr.groupby()
    # print(sum(curr.M.astype(int)))

    # boxes = []

    # print("ok")
    # dff, curr, dur = get_selected_data(hours, start_date, end_date, time_div)

    # days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
    # trace = go.Scatter(x=dff["timestamp"].astype(str),
    #                    y=dff["vehicle_id"] / days,
    #                    mode='markers+lines',
    #                    name='2015 data: %i min' % time_div,
    #                    marker={'size': 8})

    # trace1 = go.Scatter(x=curr["timestamp"].astype(str),
    #                     y=curr["vehicle_id"],
    #                     mode='markers+lines',
    #                     name='Live data: %i min' % dur,
    #                     marker={'size': 8})

    # layout = go.Layout(title="Daily activity of vehicles",
    #                    titlefont=dict(size=30),
    #                    xaxis=dict(title='Time of day',
    #                               titlefont=dict(size=20),
    #                               tickangle=-45,
    #                               tickfont=dict(size=15),
    #                               nticks=10,
    #                               tickformat="%H:%M"),
    #                    yaxis=dict(title='Number of active vehicles',
    #                               titlefont=dict(size=20),
    #                               tickfont=dict(size=15),
    #                               ))

    # return {"data": [trace, trace1], 'layout': layout,
    #         'style': {'width': '40%', 'padding-left': '25px',
    #                   'display': 'inline-block'}}


if __name__ == '__main__':
    app.run_server(debug=True)
