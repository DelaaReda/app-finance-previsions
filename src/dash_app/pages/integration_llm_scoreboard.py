import dash
from dash import dash_table
from dash import html
import pandas as pd
from integration.llm_scoreboard import get_llm_scoreboard_data

def layout():
    data = get_llm_scoreboard_data()
    df = pd.DataFrame(data)

    table = dash_table.DataTable(
        data=df.to_dict('records'),
        columns=[{'name': col, 'id': col} for col in df.columns],
        style_cell={'textAlign': 'left'},
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        }
    )

    return html.Div([
        html.H1("LLM Scoreboard"),
        table
    ])
