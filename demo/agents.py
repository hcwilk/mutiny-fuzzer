import argparse
import json
import tempfile
import os
from agent3 import Agent
from server import Server
import threading

def main():
    parser = argparse.ArgumentParser(description='Run multiple agents.')
    parser.add_argument('--config', type=str, help='Path to the configuration file.')

    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = json.load(f)

    agents = config.get('agents', [])

    server_ip = agents[0]["agent"]["server"]["ip"]
    server_port = agents[0]["agent"]["server"]["port"]

    # Start the server in a separate thread
    server = Server(server_ip, server_port)
    server_thread = threading.Thread(target=server.run)
    server_thread.start()

    # Start all agents
    for i, agent_config in enumerate(agents):
        # Write agent_config to a temporary json file
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp:
            json.dump(agent_config, temp)
            temp_filepath = temp.name

        # Instantiate and start the agent in its own thread
        agent = Agent(temp_filepath, i)
        agent_thread = threading.Thread(target=agent.start)
        agent_thread.start()

        # Remove the temporary json file
        os.remove(temp_filepath)

if __name__ == '__main__':
    main()