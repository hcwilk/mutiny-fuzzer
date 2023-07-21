import socket
from threading import Thread
import subprocess
import argparse
import time
import psutil
import os
import re
import platform
import json


## psutil is only required if you want to use the ProcessMonitor class

class ProcessMonitor(Thread):
    def __init__(self, callback, kill_callback, process_name, process_id, time_interval= 5):
        Thread.__init__(self)
        self.active = True
        self.name = process_name
        self.pid = process_id
        self.callback = callback
        self.time_interval = time_interval
        self.terminated_counts = 0
        self.kill_callback = kill_callback

    # platform-agnostic way to check if a process is running
    def check_process_running(self):
        try:
            if self.pid:
                # Check if a process with the given PID is running
                subprocess.call('ps -p '+str(self.pid), shell=True)
            else:
                # Check if a process with the given name is running (if no PID is given)
                subprocess.call('pidof '+self.name, shell=True)
                if not self.pid:
                    raise subprocess.CalledProcessError()
        except subprocess.CalledProcessError as e:
            # If there's any error, we can assume the process is not running
            #*# Not sure if we want to filter for specific errors here
            return False
        else:
            return True


    def run(self):
        try:
            while self.active:
                if self.check_process_running():
                    self.callback(0, "{} is running".format(self.name))
                else:
                    self.callback(1, "Process has crashed")
                    # Should kill the rest of the modules (no reason to be monitoring vitals if it's dead)

                    self.kill_callback()
                time.sleep(self.time_interval)
        except Exception as e:
            self.callback(2, "Error in process monitor")





class StatsMonitor(Thread):
    def __init__(self, callback, process_name, process_id, host, time_interval=5, health_config=None):
        print "Initializing StatsMonitor"
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


    
        
        # To be used in case we don't have access to psutil (has not been tested so not sure if the following modules would function the same)
        def get_process_info(pid):
            try:
                with open(os.path.join('/proc', str(pid), 'status')) as f:
                    return f.read()
            except IOError:  # process does not exist
                return None

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
        self.ping = self.ping_host()
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

    
    # Had to manually define this in python2
    def ping_host(self):
        """Ping host and return average response time"""
        
        # Option for the number of packets as a function of the OS
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        # Building the command. Ex: "ping -c 1 google.com"
        command = ['ping', param, '1', self.host]


        try:
            output = subprocess.check_output(command)
        except Exception as e:
            print 'Error pinging host',e
            return None

        # Use regex to find the response time
        patterns = [
            r"Average = (\d+)",  # Windows
            r"avg/max/stddev = (\d+\.\d+)/",  # Linux, macOS
        ]
        # Not the most efficient way to do this, but it works
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return float(match.group(1))

        # This should never hit
        return None


    def check_cpu_usage(self):
        cpu_usage = self.process.cpu_percent(interval=1)
        if self.cpu is None:
            self.cpu = cpu_usage
            return  # Skip this check, as we have just set the baseline CPU usage

        if cpu_usage > (self.cpu * self.health_config["cpu_multiplier"]) or \
                cpu_usage < self.cpu // 2:
            self.cpu_high_counts += 1
            if self.cpu_high_counts >= 3:
                # recalibrate what a high CPU usage is after 3 consecutive high CPU usage readings
                self.callback(3, "CPU usage for {} recalibrated from {} to {}".format(self.name, self.cpu, cpu_usage))
                self.cpu = cpu_usage
                self.cpu_high_counts = 0
            return True
        return False

    # Running locally, this will obviously never throw an error, but it's here for when the host is remote
    def check_ping_response(self):
        ping_response = self.ping_host()
        if ping_response is None:
            print 'something went wrong with the ping, check regex matching'
            # This is a catch for when the regex fails to find the ping response time, not sure why this is failing
            return False
        if ping_response > (self.ping * self.health_config["ping_multiplier"]):
            self.ping_high_counts += 1
            if self.ping_high_counts >= 3:
                self.callback(3, "Ping response time for {} recalibrated from {} to {}".format(self.name, self.ping,
                                                                                               ping_response))
                self.ping = ping_response
                self.ping_high_counts = 0
            print 'ping response is high'
            return True
        print 'ping response is normal'
        return False

    def check_memory_usage(self):
        memory_info = self.process.memory_info().rss
        if memory_info > (self.memory * self.health_config["memory_multiplier"]):
            self.memory_high_counts += 1
            if self.memory_high_counts >= 3:
                self.callback(3,
                              "Memory usage for {} recalibrated from {} to {}".format(self.name, self.memory,
                                                                                      memory_info))
                self.memory = memory_info
                self.memory_high_counts = 0
            return True
        return False

    def check_disk_usage(self):
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

    def run(self):
        while self.active:
            for monitor in self.monitoring_list:
                try:
                    if monitor["check_func"]():
                        # If we are checking CPU usage
                        if monitor["check_func"] == self.check_cpu_usage:
                            self.callback(1,
                                          monitor["error_message"].format(self.health_config["cpu_multiplier"],
                                                                          self.cpu))
                        # If we are checking ping response
                        elif monitor["check_func"] == self.check_ping_response:
                            self.callback(1,
                                          monitor["error_message"].format(self.health_config["ping_multiplier"],
                                                                          self.ping))
                        # If we are checking memory usage
                        elif monitor["check_func"] == self.check_memory_usage:
                            self.callback(1,
                                          monitor["error_message"].format(self.health_config["memory_multiplier"],
                                                                          self.memory))
                        # If we are checking disk usage
                        elif monitor["check_func"] == self.check_disk_usage:
                            self.callback(1,
                                          monitor["error_message"].format(self.health_config["disk_multiplier"],
                                                                          self.disk))
                        else:
                            self.callback(0, monitor["success_message"])
                        time.sleep(.1)
                except psutil.NoSuchProcess:
                    pass
                except Exception as e:
                    print 'Error coming from StatsMonitor', e
                    self.callback(2, "Error in Health monitor")
            time.sleep(self.time_interval)


class FileMonitor(Thread):
    def __init__(self, callback, filename, f_regex='', time_interval=1):
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
                print e
                print "Error parsing regex expression"

    def run(self):
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
                                1, "Error logged in log file ({})".format(self.regex.pattern))
                            # Uncomment if you want to clear log file after it's been modified
                            open(self.filename, 'w').close()
                        else:
                            self.callback(0, "No error logged in log file")
                else:
                    self.callback(0, "Log file not modified")
                time.sleep(self.time_interval)
        except Exception as e:
            print e
            self.callback(2, "Error in file monitor")


class Agent:
    def __init__(self, config_file):
        with open(config_file, 'r') as f:
            self.config = json.load(f)

        # Initialize connection the Monitor Server
        #*# This does make the connection one-way, meaning we have to have the IP and port of the monitor server before this is run
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((self.config['agent']['server']['ip'], self.config['agent']['server']['port']))
        message = '{}|{}'.format(self.config["agent"]["channel"], self.config["agent"]["type"])
        self.conn.sendall(str.encode(message))
        self.active = True

        self.minimal_mode = self.config['agent']['minimal_mode']

        self.server_heartbeat_thread = Thread(target=self.send_server_heartbeat)

        self.modules = []

    def start(self):

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

    def monitor_callback(self, exception_type, exception_info):
            
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
            print e
            print "Error sending exception data to server"

    def send_server_heartbeat(self):
        while self.active:
            self.conn.sendall(str.encode(":heartbeat"))
            time.sleep(5)

    def kill_callback(self):
        for module in self.modules:
            if not isinstance(module, FileMonitor):
                print module
                module.active = False
    
           
def main():
    parser = argparse.ArgumentParser(description='Run an agent.')
    parser.add_argument('--config', type=str, help='Path to the configuration file.')

    args = parser.parse_args()
    

    agent = Agent(args.config)

    agent.start()

if __name__ == '__main__':
    main()