import argparse
import json
import tempfile
import os
from agent3 import Agent

def main():
    parser = argparse.ArgumentParser(description='Run multiple agents.')
    parser.add_argument('--config', type=str, help='Path to the configuration file.')

    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = json.load(f)

    agents = config.get('agents', [])

    for agent_config in agents:
        # Write agent_config to a temporary json file
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp:
            json.dump(agent_config, temp)
            temp_filepath = temp.name

        # Instantiate and start the agent
        agent = Agent(temp_filepath)
        agent.start()

        # Remove the temporary json file
        os.remove(temp_filepath)

if __name__ == '__main__':
    main()
