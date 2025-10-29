import pandas as pd

def get_macro_data():
    """
    Fetches macroeconomic data from src/research/macro_firecrawl.py and formats it
    for display in the Dash app.

    Returns:
        list: A list of dictionaries, where each dictionary represents a
              macroeconomic data point. Each dictionary includes the data
              point's name, value, and any relevant metadata.
    """
    # Placeholder for fetching data from src/research/macro_firecrawl.py
    # Replace this with the actual implementation
    data = [
        {"name": "GDP Growth", "value": 2.5, "metadata": {"unit": "percent"}},
        {"name": "Inflation Rate", "value": 1.8, "metadata": {"unit": "percent"}},
        {"name": "Unemployment Rate", "value": 4.2, "metadata": {"unit": "percent"}},
    ]
    return data

if __name__ == '__main__':
    macro_data = get_macro_data()
    for item in macro_data:
        print(item)