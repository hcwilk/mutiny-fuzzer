import argparse
import yaml
import tempfile
import os
from agent import Agent

def main():
    parser = argparse.ArgumentParser(description='Run multiple agents.')
    parser.add_argument('--config', type=str, help='Path to the configuration file.')

    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    agents = config.get('agents', [])

    for agent_config in agents:
        # Write agent_config to a temporary yaml file
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False) as temp:
            yaml.dump(agent_config, temp)
            temp_filepath = temp.name

        # Instantiate and start the agent
        agent = Agent(temp_filepath)
        agent.start()

        # Remove the temporary yaml file
        os.remove(temp_filepath)

if __name__ == '__main__':
    main()
