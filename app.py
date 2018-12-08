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


if __name__ == '__main__':
    # create iterator
    app.run_server(debug=True)
