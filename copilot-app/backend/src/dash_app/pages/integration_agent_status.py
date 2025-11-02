import dash
from dash import dash_table, html
import pandas as pd
from integration.agent_status import get_agent_status_data



def layout():
    data = get_agent_status_data()
    df = pd.DataFrame(data)

    return html.Div([
        html.H1("Integration Agent Status"),
        dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[{'id': c, 'name': c} for c in df.columns],
            style_cell={'textAlign': 'left'},
        )
    ])
