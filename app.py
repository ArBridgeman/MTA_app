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

encoded_image = base64.b64encode(open("openstreetmap_nyc.png", 'rb').read())

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

    html.Div([dcc.Graph(id='time-of-day-graph'),

              dcc.Graph(id='violin-plot', style={'padding-top': '30px'}),

              html.P("Points (live data) and violins (historic data) are \
                          grouped in the legend by borough.",
                     style={"font-size": '15', 'padding-left': '30px'}),

              html.Div([
                  html.Div([dcc.Graph(id='graph-1')],
                           style={'textAlign': 'center', 'padding-top':
                                  '30px'}),

                  html.Div(dcc.Slider(id="show-me",
                                      min=0,
                                      max=24,
                                      value=0,
                                      marks={str(h): {'label': "%s:00" % h} for h in np.arange(0, 24, 1)}),
                           style={'textAlign': 'center', 'width': "85%", 'padding-bottom': "60px"})],
                       style={'textAlign': 'center'})
              ],
             style={'width': "95%", 'display': 'inline-block',
                    'textAlign': 'center', 'padding-left': '21%', 'padding-bottom': "60px"},
             className="six columns"
             )
])

# ---- used to load  and process live data ----


def nyc_current():
    """Request latests live feed"""

    def _flatten_dict(root_key, nested_dict, flattened_dict):
        """Flatten json file from MTA Bus Time API"""
        for key, value in nested_dict.items():
            next_key = root_key + "_" + key if root_key != "" else key
            if isinstance(value, dict):
                _flatten_dict(next_key, value, flattened_dict)
            else:
                flattened_dict[next_key] = value
        return flattened_dict

    params = {"key": "19faff8a-c061-4c7e-8dc4-63685ab24123",
              "MaximumStopVisits": 2}

    resp = requests.get("http://bustime.mta.info/api/siri/vehicle-monitoring.json",
                        params=params).json()
    info = resp['Siri']['ServiceDelivery'][
        'VehicleMonitoringDelivery'][0]['VehicleActivity']
    return pd.DataFrame([_flatten_dict('', i, {}) for i in info])


@app.callback(
    dash.dependencies.Output('button-clicks', 'children'),
    [dash.dependencies.Input('button', 'n_clicks')])
def clicks(n_clicks):
    """Update live data when button clicked"""

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
        # put into timestamp into EST
        sel_curr["timestamp"] = pd.to_datetime(sel_curr["timestamp"]) - \
            pd.Timedelta(hours=4)
        # get boolean columns for boroughs
        sel_curr = create_boroughs(sel_curr)
        sel_curr.to_csv("live.csv")
        return 'Live data has been refreshed {} times'.format(n_clicks)
    else:
        return "Using last saved version of live data."


def aggregate_live(live_ddf):
    """Return aggregated values for plotting live data"""

    # live sample will always be short (~3 min so no resampling)
    min_time = pd.to_datetime(live_ddf.timestamp.min())
    max_time = pd.to_datetime(live_ddf.timestamp.max())

    duration = ((max_time - min_time).seconds) // 60
    count = live_ddf.vehicle_id.nunique()
    time = "2015-09-12 %s:00" % pd.to_datetime(min_time).hour

    return time, count, duration


def match_routes(live_ddf, old_routes):
    """Match routes of live data with historic, as routes may have been
    added since then."""

    sel_mask = (live_ddf.route_id.isin(old_routes))
    sel_live = live_ddf[sel_mask].copy()

    return aggregate_live(sel_live)


# ---- used to process historic data ----


def get_selected_data(ddf, hours, start_date, end_date, time_div):
    """Apply start & end date and hour criteria. Returns selected dataframe"""
    sel_mask = (ddf["timestamp"] >= pd.to_datetime(start_date)) & \
        (ddf["timestamp"] <= pd.to_datetime(end_date)) & \
        (ddf["hour"] >= hours[0]) & (ddf["hour"] <= hours[1])
    sel_data = ddf[sel_mask].copy()

    routes = sel_data["route_id"].unique()

    return sel_data, routes


def get_vehicle_counts(ddf, hours, start_date, end_date, time_div):
    """Obtain vehicle counts from historic data in specified time intervals"""
    sel_data, routes = get_selected_data(ddf, hours, start_date, end_date,
                                         time_div)

    # want to only count unique vehicle ids in the time window with
    sampled = sel_data.resample("%sMin" % time_div,
                                on="timestamp").agg({"vehicle_id": "nunique"})
    # easiest way to return to a pandas dataframe
    sampled = sampled.reset_index()

    # create hour for groupby
    sampled["hhmmss"] = sampled["timestamp"].apply(lambda x: x.time())
    sampled["hh"] = sampled["timestamp"].apply(lambda x: "%i:00" % (x.hour))
    data = sampled.groupby("hhmmss", as_index=False).agg({"vehicle_id": 'sum',
                                                          "hh": 'first'})
    data = data.rename(index=str, columns={"vehicle_id": "vehicle_count"})
    data["timestamp"] = data["hhmmss"].apply(lambda x: "2015-09-12 %s" % x)
    data = data.sort_values("timestamp")
    data = data[data.vehicle_count > 0]

    return data, routes


# ---- used to generate or directly modify plots ----

@app.callback(
    dash.dependencies.Output("show-me", "step"),
    [dash.dependencies.Input("time-div", 'value')])
def redo_slider(time_div):
    """Change size of step in show-me slider"""
    return time_div / 60


@app.callback(
    dash.dependencies.Output('time-of-day-graph', "figure"),
    [dash.dependencies.Input('button-clicks', 'children'),
     dash.dependencies.Input("hour-slider", "value"),
     dash.dependencies.Input("date-range", 'start_date'),
     dash.dependencies.Input("date-range", 'end_date'),
     dash.dependencies.Input("time-div", 'value'),
     dash.dependencies.Input("route-match", "value"),
     dash.dependencies.Input('violin-plot', 'hoverData')])
def daily_graph(d, hours, start_date, end_date, time_div, route_match, borough):
    """Plot count of historic and live data as a function of time"""

    # --- load datasets ----
    # historic data
    hist_df = df.copy()
    # live data
    live_df = pd.read_csv("live.csv", index_col=0, parse_dates=True)

    # --- obtain hover item from violin plot---
    if borough is not None:
        key = borough["points"][0]["x"]
    else:
        key = "All"

    # if not all, then need to select specific borough to plot
    hist_plot = False
    live_plot = False

    if key != "All":
        if any(hist_df[inv_dic_borough[key]]):
            hist_df = hist_df[hist_df[inv_dic_borough[key]]]
            hist_plot = True
        if any(live_df[inv_dic_borough[key]]):
            live_df = live_df[live_df[inv_dic_borough[key]]]
            live_plot = True
        title = key
    else:
        title = "all boroughs of NYC"
        hist_plot = True
        live_plot = True

    traces = []

    # ---- perform time selection on historic data and plot----
    hist_routes = []
    if hist_plot:
        hist_df, hist_routes = get_vehicle_counts(hist_df, hours, start_date,
                                                  end_date, time_div)
        days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days

        hist_trace = go.Scatter(x=hist_df["timestamp"].astype(str),
                                y=hist_df["vehicle_count"] / days,
                                mode='markers+lines',
                                name='historic data: %i min' % time_div,
                                marker={'size': 8})
        traces.append(hist_trace)

    # ---- live data match route data of historic (if specified) and plot ----
    if live_plot:
        if route_match == 1 and len(hist_routes) > 0:
            time, count, dur = match_routes(live_df, hist_routes)
        else:
            time, count, dur = aggregate_live(live_df)

        live_trace = go.Scatter(x=[str(time)],
                                y=[count],
                                mode='markers+lines',
                                name='live data: %i min' % dur,
                                marker={'size': 8})

        traces.append(live_trace)

    layout = go.Layout(title="Daily activity of vehicles in %s" % title,
                       titlefont=dict(size=30),
                       height=400,
                       xaxis=dict(title='Time of day',
                                  titlefont=dict(size=20),
                                  tickangle=-45,
                                  tickfont=dict(size=15),
                                  nticks=10,
                                  tickformat="%H:%M"),
                       yaxis=dict(title='Number of active vehicles',
                                  titlefont=dict(size=20),
                                  tickfont=dict(size=15)),
                       legend=dict(font=dict(size=15)))

    return {"data": traces, 'layout': layout,
            'style': {'width': '40%', 'padding-left': '25px',
                      'display': 'inline-block'}}


@app.callback(
    dash.dependencies.Output('violin-plot', "figure"),
    [dash.dependencies.Input('button-clicks', 'children'),
     dash.dependencies.Input("hour-slider", "value"),
     dash.dependencies.Input("date-range", 'start_date'),
     dash.dependencies.Input("date-range", 'end_date'),
     dash.dependencies.Input("time-div", 'value'),
     dash.dependencies.Input("route-match", "value")])
def violin_plot(dummy, hours, start_date, end_date, time_div, route_match):
    """Draw violin plot with different boroughs"""

    # load historical data and add borough booleans
    hist_df, hist_routes = get_selected_data(df, hours, start_date, end_date,
                                             time_div)
    days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days

    # load live data and add borough booleans
    live_df = pd.read_csv("live.csv", index_col=0, parse_dates=True)

    # get counts for all historical data
    all_df, all_routes = get_vehicle_counts(hist_df, hours, start_date,
                                            end_date, time_div)
    all_counts = all_df.vehicle_count / days

    if route_match == 1:
        _, count_live, _ = match_routes(live_df, all_routes)
    else:
        _, count_live, _ = aggregate_live(live_df)

    #  create point and violin across all boroughs
    traces = [{"type": 'violin',
               "x": ["All"] * all_counts.shape[0],
               "y": all_counts,
               "bandwidth": 20,
               'name': "All",
               'legendgroup':"All",
               "showlegend": True,
               "box": {"visible": True},
               "meanline": {"visible": True}},

              go.Scatter(x=["All"],
                         y=[count_live],
                         mode='markers',
                         name='All',
                         legendgroup="All",
                         showlegend=False,
                         marker={'size': 8})
              ]

    for it, col in enumerate(dic_borough.keys()):
        if any(hist_df[col]):
            # extracting items within certain borough
            t_hist_df = hist_df[hist_df[col]]
            # getting counts with specified time division and criteria
            temp_df, temp_routes = get_vehicle_counts(t_hist_df, hours,
                                                      start_date, end_date,
                                                      time_div)

            counts = temp_df.vehicle_count / days
            violin = {"type": 'violin',
                      "x": [dic_borough[col]] * counts.shape[0],
                      "y": counts,
                      "bandwidth": 20,
                      'name': dic_borough[col],
                      'legendgroup': dic_borough[col],
                      "showlegend": True,
                      "box": {"visible": True},
                      "meanline": {"visible": True}}
            traces.append(violin)

            # want to match routes in case of live data so no discrepancy's
            # other than increase service within those routes
            if any(live_df[col]):
                # extracting items within certain borough
                t_live_df = live_df[live_df[col]]
                # ensure in same routes
                if route_match == 1:
                    _, count, _ = match_routes(t_live_df, temp_routes)
                else:
                    _, count, _ = aggregate_live(t_live_df)

                point = go.Scatter(x=[dic_borough[col]],
                                   y=[count],
                                   mode='markers',
                                   name=dic_borough[col],
                                   showlegend=False,
                                   legendgroup=dic_borough[col],
                                   marker={'size': 8})
                traces.append(point)

        # historic data may not include some boroughs that the live data does
        else:
            if any(live_df[col]):
                # extracting items within certain borough
                t_live_df = live_df[live_df[col]]
                _, count, _ = aggregate_live(t_live_df)

                point = go.Scatter(x=[dic_borough[col]],
                                   y=[count],
                                   mode='markers',
                                   name=dic_borough[col],
                                   legendgroup=dic_borough[col],
                                   marker={'size': 8})
                traces.append(point)

    layout = go.Layout(title="Number of active vehicles per borough",
                       titlefont=dict(size=30),
                       height=400,
                       xaxis=dict(title='Borough',
                                  titlefont=dict(size=20),
                                  tickfont=dict(size=15),
                                  nticks=10,
                                  tickformat="%H:%M"),
                       yaxis=dict(title='Number of active vehicles',
                                  titlefont=dict(size=20),
                                  tickfont=dict(size=15)),
                       legend=dict(font=dict(size=15)),
                       hovermode='closest')
    return {"data": traces, "layout": layout}


def matplotlib_to_plotly(cmap, pl_entries):
    """Convert matplotlib colormap to plotly version"""
    h = 1.0 / (pl_entries - 1)
    pl_colorscale = []

    for k in range(pl_entries):
        C = list(map(np.uint8, np.array(cmap(k * h)[:3]) * 255))
        pl_colorscale.append([k * h, 'rgb' + str((C[0], C[1], C[2]))])

    return pl_colorscale

# getting color map
viridis_cmap = cm.get_cmap('viridis')
viridis = matplotlib_to_plotly(viridis_cmap, 255)
# reset last one to be transparent
viridis[-1] = [1.0, 'rgba(68, 1, 84, 0)']


@app.callback(
    dash.dependencies.Output('graph-1', 'figure'),
    [dash.dependencies.Input('show-me', 'value')])
def update_graph_1(value):

    layout = dict(title="Daily activity of vehicles",
                  titlefont=dict(size=30),
                  xaxis=dict(range=[-74.30, -73.50], showticklabels=False),
                  yaxis=dict(range=[40.5, 40.95], showticklabels=False),
                  images=[dict(
                      source='data:image/png;base64,{}'.format(
                          encoded_image.decode()),
                      xref="x",
                      yref="y",
                      x=-74.30,
                      y=40.95,
                      sizex=0.8,
                      sizey=0.45,
                      sizing="stretch",
                      layer="below")],
                  hovermode='closest',
                  showlegend=False,
                  width=1156,
                  height=851
                  )

    return {'data': [], 'layout': layout}


if __name__ == '__main__':
    # create iterator
    app.run_server(debug=True)
