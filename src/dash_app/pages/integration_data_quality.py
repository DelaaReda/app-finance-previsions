from dash import dash_table, html
import pandas as pd
from integration.data_quality import get_data_quality_data

data = get_data_quality_data()
df = pd.DataFrame(data)

layout = html.Div([
    dash_table.DataTable(
        data=df.to_dict('records'),
        columns=[{'id': c, 'name': c} for c in df.columns],
        style_cell={'textAlign': 'left'},
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        }
    )
])
