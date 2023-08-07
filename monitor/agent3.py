import socket
from threading import Thread
import subprocess
import argparse
import time
import psutil
import os
import json
import re
from ping3 import ping

class ProcessMonitor(Thread):
    def __init__(self, callback, kill_callback, process_name: str, process_id: int, time_interval: float = 5) -> None:
        Thread.__init__(self)
        self.active = True
        self.name = process_name
        self.pid = process_id
        self.callback = callback
        self.time_interval = time_interval
        self.terminated_counts = 0
        self.kill_callback = kill_callback

    # platform-agnostic way to check if a process is running
    def check_process_running(self) -> bool:
        try:
            if self.pid:
                # Check if a process with the given PID is running
                subprocess.check_output(
                    'ps -p '+str(self.pid), shell=True)
            else:
                # Check if a process with the given name is running (if no PID is given)
                subprocess.check_output('pidof '+self.name, shell=True)
                if not self.pid:
                    raise subprocess.CalledProcessError()
        except subprocess.CalledProcessError as e:
            # If there's any error, we can assume the process is not running
            #*# Not sure if we want to filter for specific errors here
            return False
        else:
            return True


    def run(self) -> None:
        try:
            while self.active:
                if self.check_process_running():
                    self.callback(0, f"{self.name} is running")
                else:
                    self.callback(1, f"Process has crashed")
                    # Should kill the rest of the modules (no reason to be monitoring vitals if it's dead)
                    self.kill_callback()

                time.sleep(self.time_interval)
        except Exception as e:
            self.callback(2, "Error in process monitor")

class StatsMonitor(Thread):
    def __init__(self, callback, process_name: str, process_id: int, host: str, time_interval: float = 5, health_config=None) -> None:
        print("Initializing StatsMonitor")
        Thread.__init__(self)
        self.active = True
        self.name = process_name
        self.pid = process_id
        self.callback = callback
        self.host = host
        self.time_interval = time_interval
        self.cpu_high_counts = 0
        self.ping_high_counts = 0
        self.memory_high_counts = 0
        self.disk_high_counts = 0
        self.process = psutil.Process(self.pid)

        # This configuration will come from an 'agent.json' or 'agents.json' file
        # These are the default values (can easily be changed, I really have no context as to what these values should be)
        if health_config is None:
            health_config = {
                "cpu_multiplier": 1.1,
                "ping_multiplier": 2,
                "memory_multiplier": 1.1,
                "disk_multiplier": 1.1
            }

        self.health_config = health_config


        # Setting ground truth for CPU, Ping, Memory, and Disk usage
        self.cpu = None
        self.ping = ping(self.host)
        self.memory = self.process.memory_info().rss
        # No easy way to fetch Disk Usage (which is really just I/O usage) in platform-agnostic setting, so we'll ignore it if there's an error
        try:
            self.disk = self.process.io_counters().read_bytes + self.process.io_counters().write_bytes
        except AttributeError:
            self.disk = None


        self.monitoring_list = [
    {
        "check_func": self.check_cpu_usage,
        "error_message": "CPU usage is higher than {}x the baseline of {}",
        "success_message": "CPU usage is normal",
    },
    {
        "check_func": self.check_ping_response,
        "error_message": "Ping response time is higher than {}x the baseline of {}",
        "success_message": "Ping response time is normal",
    },
    {
        "check_func": self.check_memory_usage,
        "error_message": "Memory usage is higher than {}x the baseline of {}",
        "success_message": "Memory usage is normal",
    },
    {
        "check_func": self.check_disk_usage,
        "error_message": "Disk usage is high",
        "success_message": "Disk usage is normal",
    },
]

    
    def check_cpu_usage(self) -> bool:
        cpu_usage = self.process.cpu_percent(interval=1)
        if self.cpu is None:
            self.cpu = cpu_usage
            return  # Skip this check, as we have just set the baseline CPU usage

        if cpu_usage > (self.cpu * self.health_config["cpu_multiplier"]) or \
            cpu_usage < self.cpu//2:
            self.cpu_high_counts += 1
            if self.cpu_high_counts >= 3:
                # recalibrate what a high CPU usage is after 3 consecutive high CPU usage readings
                self.callback(3, "CPU usage for {} recalibrated from {} to {}".format(self.name,self.cpu, cpu_usage))
                self.cpu = cpu_usage
                self.cpu_high_counts = 0
            return True
        return False


        # Running locally, this will obviously never throw an error, but it's here for when the host is remote
    def check_ping_response(self) -> bool:
        ping_response = ping(self.host)
        if ping_response > (self.ping * self.health_config["ping_multiplier"]):
            self.ping_high_counts += 1
            if self.ping_high_counts >= 3:
                self.callback(3, "Ping response time for {} recalibrated from {} to {}".format(self.name,self.ping, ping_response))
                self.ping = ping_response
                self.ping_high_counts = 0
            return True
        return False

    def check_memory_usage(self) -> bool:
        memory_info = self.process.memory_info().rss
        if memory_info > (self.memory * self.health_config["memory_multiplier"]):
            self.memory_high_counts += 1
            if self.memory_high_counts >= 3:
                self.callback(3, "Memory usage for {} recalibrated from {} to {}".format(self.name,self.memory, memory_info))
                self.memory = memory_info
                self.memory_high_counts = 0
            return True
        return False

    def check_disk_usage(self) -> bool:
        try:
            io_info = self.process.io_counters()
            disk_usage = io_info.read_bytes + io_info.write_bytes
            if disk_usage > self.disk * self.health_config["disk_multiplier"]:
                self.disk_high_counts += 1
                if self.disk_high_counts >= 3:
                    self.disk = disk_usage
                    self.disk_high_counts = 0
                return True
        except AttributeError:
            return False
        return False
    

    def run(self) -> None:
        while self.active:
            for monitor in self.monitoring_list:
                try:
                    if monitor["check_func"]():
                        # If we are checking CPU usage
                        if monitor["check_func"] == self.check_cpu_usage:
                            self.callback(1, monitor["error_message"].format(self.health_config["cpu_multiplier"], self.cpu))
                        # If we are checking ping response
                        elif monitor["check_func"] == self.check_ping_response:
                            self.callback(1, monitor["error_message"].format(self.health_config["ping_multiplier"], self.ping))
                        # If we are checking memory usage
                        elif monitor["check_func"] == self.check_memory_usage:
                            self.callback(1, monitor["error_message"].format(self.health_config["memory_multiplier"], self.memory))
                        # If we are checking disk usage
                        elif monitor["check_func"] == self.check_disk_usage:
                            self.callback(1, monitor["error_message"].format(self.health_config["disk_multiplier"], self.disk))
                        else:
                            self.callback(0, monitor["success_message"])
                        time.sleep(.1)
                except psutil.NoSuchProcess:
                    pass  # Ignore this exception. Process monitor will shut this down shortly, no reason to send this to the callback
                
                except Exception as e:
                    print(f'Error coming from StatsMonitor {e}')
                    self.callback(2, "Error in Health monitor")

            time.sleep(self.time_interval)

class FileMonitor(Thread):
    def __init__(self, callback, filename: str, f_regex: str = '', time_interval: int = 1) -> None:
        Thread.__init__(self)
        self.active = True
        self.filename = filename
        self.callback = callback
        self.last_modified = os.path.getmtime(filename)
        self.time_interval = time_interval
        self.regex = False
        if f_regex:
            try:
                self.regex = re.compile(f_regex)
            except Exception as e:
                print(e)
                print("Error parsing regex expression")

    def run(self) -> None:
        try:
            while self.active:
                modified = os.path.getmtime(self.filename)
                if modified != self.last_modified:
                    self.last_modified = modified
                    if not self.regex:
                        self.callback(1, "Log file modified")
                    else:
                        f = open(self.filename, 'r')
                        data = '\n'.join(f.readlines())
                        f.close()
                        if self.regex.search(data):
                            self.callback(
                                1, f"Error logged in log file ({self.regex})")
                            # Uncomment if you want to clear log file after it's been modified
							# Only works if you have write permission (which you likely wont)
                            # open(self.filename, 'w').close()    
                        else:
                            self.callback(0, "No error logged in log file")
                else:
                    self.callback(0, "Log file not modified")
                time.sleep(self.time_interval)
        except Exception as e:
            print(e)
            self.callback(2, "Error in file monitor")

class Agent:
    def __init__(self, config_file: str) -> None:
        with open(config_file, 'r') as file:
            self.config = json.load(file)    

        # Initialize connection the Monitor Server
        #*# This does make the connection one-way, meaning we have to have the IP and port of the monitor server before this is run
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((self.config['agent']['server']['ip'], self.config['agent']['server']['port']))
        message = f'{self.config["agent"]["channel"]}|{self.config["agent"]["type"]}'
        self.conn.sendall(str.encode(message))
        self.active = True


        self.minimal_mode = self.config['agent']['minimal_mode']

        self.server_heartbeat_thread = Thread(target=self.send_server_heartbeat)

        self.modules = []

    def start(self) -> None:
        # There's probably a better way to do this, but this is what reads in the config file and set's the contstants that deal with the modules abvoe
        for module_config in self.config['agent']['modules']:
            if module_config['type'] == 'ProcessMonitor' and module_config['active'] == True:
                process = ProcessMonitor(self.monitor_callback, self.kill_callback, 
                                        module_config['process_name'], 
                                        module_config['process_id'], time_interval = module_config['time_interval'])
                self.modules.append(process)
                process.start()

            elif module_config['type'] == 'FileMonitor' and module_config['active'] == True:
                file = FileMonitor(self.monitor_callback, module_config['filename'], module_config['f_regex'], module_config['time_interval'])
                self.modules.append(file)
                file.start()

            elif module_config['type'] == 'StatsMonitor' and module_config['active'] == True:
                stats = StatsMonitor(self.monitor_callback, module_config['process_name'], 
                                    module_config['process_id'], module_config['host'], 
                                    module_config['time_interval'], module_config['health_config'])
                self.modules.append(stats)
                stats.start()
            offset = ((module_config['time_interval'] * 10)//3) / 10
            time.sleep(offset)



    def monitor_callback(self, exception_type: int, exception_info: str) -> None:
            
        # This is just the funciton that reports info back to the monitor server
        try:
            # If everything is normal
            if exception_type == 0:
                if not self.minimal_mode:
                    self.conn.sendall(str.encode(exception_info))
            # If the agent is reporting some abnormality
            elif exception_type == 1:
                message = "!{}".format(exception_info)
                self.conn.sendall(str.encode(message))
            # If the agent is reporting a recalibration
            elif exception_type == 3:
                message = "?{}".format(exception_info)
                self.conn.sendall(str.encode(message))
            # (This will always be two, but just in case) If the agent is reporting an error with itself (not the target)
            else:
                message = "#{}".format(exception_info)
                self.conn.sendall(str.encode(message))            
        except Exception as e:
            print(e)
            print("Error sending exception data to server")


    def send_server_heartbeat(self) -> None:
        while self.active:
            self.conn.sendall(str.encode(":heartbeat"))
            time.sleep(5)

    # This version just shuts down everything
    # def kill_callback(self) -> None:
    #     for module in self.modules:
    #         module.active = False

    # Here's a version that keeps FileMonitor alive (just in case you care about post-mortem logs)
    def kill_callback(self) -> None:
        for module in self.modules:
            # Leave file monitor alive incase useful debug / crash information is logged
            if not isinstance(module, FileMonitor):
                print(module)
                module.active = False

           
def main():
    parser = argparse.ArgumentParser(description='Run an agent.')
    parser.add_argument('--config', type=str, help='Path to the configuration file.')

    args = parser.parse_args()

    agent = Agent(args.config)

    agent.start()

if __name__ == '__main__':
    main()