import os
import sys
import inspect

# Add the project root to the sys.path to allow absolute imports
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from src.agents import *
from src.agent_runner import scheduler


def get_agent_status_data():
    """
    Fetches data from src/agents and src/agent_runner and formats it for display.

    Returns:
        list: A list of dictionaries, where each dictionary represents the status
              of an agent. The dictionary includes the agent's name, status,
              and any relevant metrics.
    """
    agent_status_data = []

    # Get a list of all agent classes in src/agents
    agent_classes = [
        (name, cls)
        for name, cls in inspect.getmembers(sys.modules['src.agents'], inspect.isclass)
        if cls.__module__.startswith('src.agents') and name != 'Agent'
    ]

    # Get the scheduler instance
    scheduler_instance = scheduler.Scheduler()

    # Iterate through the agent classes and get their status
    for name, agent_class in agent_classes:
        # Check if the agent is running in the scheduler
        if name in scheduler_instance.scheduled_agents:
            status = "Running"
            metrics = scheduler_instance.scheduled_agents[name].metrics if hasattr(scheduler_instance.scheduled_agents[name], 'metrics') else {}
        else:
            status = "Stopped"
            metrics = {}

        agent_status = {
            "name": name,
            "status": status,
            "metrics": metrics,
        }
        agent_status_data.append(agent_status)

    return agent_status_data


if __name__ == '__main__':
    data = get_agent_status_data()
    print(data)