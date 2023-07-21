import argparse
import json
import tempfile
import os
from agent3 import Agent
import threading

def create_agent_config_interactively():
    print("Configuring Server")
    server_ip = input("Enter server IP: ")
    server_port = int(input("Enter server port: "))

    agents = []
    num_agents = int(input("Enter the number of agents to configure: "))
    for i in range(num_agents):
        modules = []



        print(f"\nConfiguring agent {i+1}")
        channel = i
        minimal_mode = input("Minimal mode (yes/no): ").lower() == 'yes'
        agent_type = 'remote-agent'

        process_name = input("Enter common process name: ")
        process_id = int(input("Enter common process id: "))

        num_modules = int(input("Enter the number of modules for this agent: "))
        for j in range(num_modules):
            print(f"\nConfiguring module {j+1}")
            module_type = {
                "P": "ProcessMonitor",
                "F": "FileMonitor",
                "S": "StatsMonitor"
            }[input("Enter module type (P for ProcessMonitor/F for FileMonitor/S for StatsMonitor): ")]
            if module_type == "ProcessMonitor":
                time_interval = int(input("Enter time interval: "))
                active = input("Is the module active (yes/no): ").lower() == 'yes'
                modules.append({
                    "type": module_type,
                    "process_name": process_name,
                    "process_id": process_id,
                    "time_interval": time_interval,
                    "active": active
                })
            # ... rest of module configurations ...

        agent = {
            "agent": {
                "server": {
                    "ip": server_ip,
                    "port": server_port,
                },
                "channel": channel,
                "minimal_mode": minimal_mode,
                "type": agent_type,
                "modules": modules
            }
        }
        agents.append(agent)

    return {"server": {"ip": server_ip, "port": server_port}, "agents": agents}

def main():
    parser = argparse.ArgumentParser(description='Run multiple agents.')
    parser.add_argument('--config', type=str, help='Path to the configuration file.', default="")

    args = parser.parse_args()

    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
    else:
        config = create_agent_config_interactively()
        save_path = input("Enter a filename to save this configuration for future use: ")
        with open(save_path, 'w') as f:
            json.dump(config, f)

    server = config.get('server')
    agents = config.get('agents', [])

    # Start all agents in separate threads
    for i, agent_config in enumerate(agents):
        # Append server configuration to each agent
        agent_config['agent']['server'] = server
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
