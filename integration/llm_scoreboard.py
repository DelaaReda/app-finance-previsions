from src.agents.g4f_model_watcher import get_model_data

def get_llm_scoreboard_data():
    """
    Fetches data from g4f_model_watcher and formats it for display.

    Returns:
        list: A list of dictionaries, where each dictionary represents an LLM model's performance.
              Each dictionary includes the model's name, score, and any relevant metrics.
    """
    model_data = get_model_data()
    scoreboard_data = []
    for model in model_data:
        scoreboard_data.append({
            "name": model["name"],
            "score": model["score"],
            "latency": model["latency"],
            "cost": model["cost"]
        })
    return scoreboard_data