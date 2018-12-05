import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go


app = dash.Dash()

df = pd.read_csv('worldwide_indicators_by_year.csv')

colors = {
    'background': '#111111',
    'text': '#7FDBFF'
}

available_indicators = df['Indicator Name'].unique()

app.layout = html.Div([
	 
	html.H1(
        children='Worldwide indicators',
        style={
            'textAlign': 'center',
			#'color': colors['text']
        }
    ),
    html.Div([

        html.Div([
            dcc.Dropdown(
                id='crossfilter-xaxis-column',
                options=[{'label': i, 'value': i} for i in available_indicators],
                value='Electric power consumption (kWh per capita)'
            ),
            dcc.RadioItems(
                id='crossfilter-xaxis-type',
                options=[{'label': i, 'value': i} for i in ['Linear', 'Log']],
                value='Linear',
                labelStyle={'display': 'inline-block'}
            )], style={'width': '49%', 'display': 'inline-block'}
		),

        html.Div([
            dcc.Dropdown(
                id='crossfilter-yaxis-column',
                options=[{'label': i, 'value': i} for i in available_indicators],
                value='CO2 emissions (metric tons per capita)'
            ),
            dcc.RadioItems(
                id='crossfilter-yaxis-type',
                options=[{'label': i, 'value': i} for i in ['Linear', 'Log']],
                value='Linear',
                labelStyle={'display': 'inline-block'}
            )], style={'width': '49%', 'float': 'right', 'display': 'inline-block'}
		)
    ], style={
        'borderBottom': 'thin lightgrey solid',
        'backgroundColor': 'rgb(250, 250, 250)',
        'padding': '10px 5px'
    }),
	
	
	html.Div([
		dcc.Graph(
			id='crossfilter-indicator-scatter',
			hoverData={'points': [{'customdata': 'Norway'}]}
		)], style={'width': '49%', 'display': 'inline-block', 'padding': '0 20'}
	),
	
	html.Div([
		dcc.Graph(id='y-time-series'),
		dcc.Graph(id='x-time-series')
		], style={'width': '49%', 'padding-left': '25px','display': 'inline-block'} 
	),

    html.Div(
		dcc.Slider(
			id='crossfilter-year--slider',
			min=df['Year'].min(),
			max=df['Year'].max(),
			value=df['Year'].max(),
			marks={str(year): str(year) for year in df['Year'].unique()}
		), style={'width': '48%', 'padding': '0px 20px 20px 20px'}
	)
])


@app.callback(
    dash.dependencies.Output('crossfilter-indicator-scatter', 'figure'),
    [dash.dependencies.Input('crossfilter-xaxis-column', 'value'),
     dash.dependencies.Input('crossfilter-yaxis-column', 'value'),
     dash.dependencies.Input('crossfilter-xaxis-type', 'value'),
     dash.dependencies.Input('crossfilter-yaxis-type', 'value'),
	 dash.dependencies.Input('crossfilter-year--slider', 'value')])
def update_graph(xaxis_column_name, yaxis_column_name,
                 xaxis_type, yaxis_type, year_value):
				 
    dff = df[df['Year'] == year_value]
	
    return {
        'data': [go.Scatter(
            x=dff[dff['Indicator Name'] == xaxis_column_name]['Value'],
            y=dff[dff['Indicator Name'] == yaxis_column_name]['Value'],
            text=dff[dff['Indicator Name'] == yaxis_column_name]['Country Name'],
            customdata=dff[dff['Indicator Name'] == yaxis_column_name]['Country Name'],
            mode='markers',
            marker={
                'size': 15,
                'opacity': 0.5,
                'line': {'width': 0.5, 'color': 'white'}
            }
        )],
        'layout': go.Layout(
            xaxis={
                'title': xaxis_column_name,
                'type': 'linear' if xaxis_type == 'Linear' else 'log'
            },
            yaxis={
                'title': yaxis_column_name,
                'type': 'linear' if yaxis_type == 'Linear' else 'log'
            },
            margin={'l': 40, 'b': 30, 't': 10, 'r': 0},
            height=600,
            hovermode='closest'
        )
    }


def create_time_series(dff, axis_type, title):
    return {
        'data': [go.Scatter(
            x=dff['Year'],
            y=dff['Value'],
            mode='lines+markers',
			marker={'color':'#fdaa48'},
        )],
        'layout': {
			'title': title,
            'height': 300, #225
			#'width': 500,
			'titlefont': {'size': 14},
            'margin': {'l': 35, 'b': 45, 'r': 10, 't': 25}, #'t': 10 'b': 40
            'yaxis': {'type': 'linear' if axis_type == 'Linear' else 'log'},
            'xaxis': {'showgrid': False}
        }
    }
	
@app.callback(
    dash.dependencies.Output('y-time-series', 'figure'),
    [dash.dependencies.Input('crossfilter-indicator-scatter', 'hoverData'),
     dash.dependencies.Input('crossfilter-yaxis-column', 'value'),
     dash.dependencies.Input('crossfilter-yaxis-type', 'value')])
def update_y_timeseries(hoverData, yaxis_column_name, axis_type):
    country_name = hoverData['points'][0]['customdata']
    dff = df[df['Country Name'] == country_name]
    dff = dff[dff['Indicator Name'] == yaxis_column_name]
    title = '<b>{}</b><br>{}'.format(country_name, yaxis_column_name)
    return create_time_series(dff, axis_type, title)

@app.callback(
    dash.dependencies.Output('x-time-series', 'figure'),
    [dash.dependencies.Input('crossfilter-indicator-scatter', 'hoverData'),
     dash.dependencies.Input('crossfilter-xaxis-column', 'value'),
     dash.dependencies.Input('crossfilter-xaxis-type', 'value')])
def update_y_timeseries(hoverData, xaxis_column_name, axis_type):
    dff = df[df['Country Name'] == hoverData['points'][0]['customdata']]
    dff = dff[dff['Indicator Name'] == xaxis_column_name]
    return create_time_series(dff, axis_type, xaxis_column_name)

 
if __name__ == '__main__':
    app.run_server()