import dash
from dash import dash_table
from dash import dcc
from dash import html
import pandas as pd
from integration.macro_data import get_macro_data

macro_data = get_macro_data()

df = pd.DataFrame(macro_data)

layout = html.Div([
    html.H1("Macroeconomic Data"),
    dash_table.DataTable(
        data=df.to_dict('records'),
        columns=[
            {'name': 'Name', 'id': 'name'},
            {'name': 'Value', 'id': 'value'},
            {'name': 'Metadata', 'id': 'metadata'}
        ],
        style_cell={'textAlign': 'left'}
    )
])
