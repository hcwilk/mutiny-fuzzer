import socket
from threading import Thread
import subprocess
import sys
import argparse
import time
import psutil
import os
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
        # conditional based on Darwin or not
        try:
            if self.pid:
                # Check if a process with the given PID is running
                subprocess.check_output(
                    'ps -p '+str(self.pid), shell=True)
            else:
                # Get the PID of the process by name
                pid = subprocess.check_output(
                    'pgrep '+self.name, shell=True)
                if not pid:
                    raise subprocess.CalledProcessError()
        except subprocess.CalledProcessError as e:
            return False
        else:
            return True


    def run(self) -> None:
        try:
            while self.active:
                if self.check_process_running():
                    self.callback(0, f"{self.name} is running")
                else:
                    self.callback(1, f"Process {self.pid} has crashed")
                    # Should kill the rest of the modules (no reason to be monitoring vitals if it's dead)
                    self.kill_callback()

                    # self.terminated_counts += 1
                    # # If the process has terminated 3 times in a row, we'll assume it's not coming back and shut down this module
                    # if self.terminated_counts > 3:
                    #     self.active = False

                time.sleep(self.time_interval)
        except Exception as e:
            print('This is the exception',e)
            self.callback(2, "Error in process monitor")


class StatsMonitor(Thread):
    def __init__(self, callback, process_name: str, process_id: int, host: str, time_interval: float = 5) -> None:
        print("Initializing StatsMonitor")
        Thread.__init__(self)
        self.active = True
        self.name = process_name
        self.pid = process_id
        self.callback = callback
        self.host = host
        self.time_interval = time_interval
        self.cpu_high_counts = 0
        self.process = psutil.Process(self.pid)

        


        # Setting ground truth for CPU, Ping, Memory, and Disk usage
        self.cpu = self.process.cpu_percent(interval=self.time_interval)
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
            "error_message": "CPU usage is high",
            "success_message": "CPU usage is normal",
        },
        {
            "check_func": self.check_ping_response,
            "error_message": "Ping response time is slow",
            "success_message": "Ping response time is normal",
        },
        {
            "check_func": self.check_memory_usage,
            "error_message": "Memory usage is high",
            "success_message": "Memory usage is normal",
        },
        {
            "check_func": self.check_disk_usage,
            "error_message": "Disk usage is high",
            "success_message": "Disk usage is normal",
        },
    ]
        
        # let these be default, let user input to change them

    def check_cpu_usage(self) -> bool:
        if self.process.cpu_percent(interval=self.time_interval) > (self.cpu*1.1):
            self.cpu_high_counts += 1
            if self.cpu_high_counts >= 3:
                # recalibrate what a high CPU usage is after 3 consecutive high CPU usage readings
                self.cpu = self.process.cpu_percent(interval=self.time_interval)
                self.cpu_high_counts = 0
            return True

    # Running locally, this will obviously never throw an error, but it's here for when the host is remote
    def check_ping_response(self) -> bool:
        return ping(self.host) > (self.ping * 2)

    # Wasn't too sure what the rule for this should be 
    def check_memory_usage(self) -> bool:
        return self.process.memory_info().rss > (self.memory * 1.1)

    def check_disk_usage(self) -> bool:
        try:
            io_info = self.process.io_counters()
            return (io_info.read_bytes + io_info.write_bytes) > self.disk * 1.1
        except AttributeError:
            # platform issues handled here
            return False

    def run(self) -> None:
        while self.active:
            for monitor in self.monitoring_list:
                try:
                    if monitor["check_func"]():
                        self.callback(1, monitor["error_message"])
                    else:
                        self.callback(0, monitor["success_message"])
                    time.sleep(.1)
                
                except Exception as e:
                    print('Likely process has ended, coming from StatsMonitor',e)
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
                            # clear log file
                            open(self.filename, 'w').close()    
                        else:
                            self.callback(0, "No error logged in log file")
                else:
                    self.callback(0, "Log file not modified")
                time.sleep(self.time_interval)
        except Exception as e:
            print(e)
            self.callback(2, "Error in file monitor")


class Agent:
    def __init__(self, host_ip: str, host_port: int, channel: str, minimal_mode: bool, type: str = 'remote-agent') -> None:
        # established connection with server and sends initial packed containing channel and type
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((host_ip, host_port))
        self.conn.sendall(str.encode(f'{channel}|{type}'))
        self.active = True
        self.channel = channel

        # creates three threads to be used for monitoring server input, user input, and sending server heartbeats every 5 seconds
        self.server_heartbeat_thread = Thread(
            target=self.send_server_heartbeat)

        self.minimal_mode = minimal_mode
        self.modules: list[Thread] = []

    def start(self) -> None:
        self.server_heartbeat_thread.start()
        for module in self.modules:
            module.start()
            offset = ((module.time_interval * 10)//3) / 10
            print('offset',offset)
            time.sleep(offset)

    def monitor_callback(self, exception_type: int, exception_info: str) -> None:

            try:
                if exception_type == 0:
                    if not self.minimal_mode:
                        self.conn.sendall(str.encode(exception_info))
                elif exception_type == 1:
                    message = f"!{exception_info}"
                    print('sending to mutiny',message)
                    self.conn.sendall(str.encode(message))
                else:
                    message = f"#{exception_info}"
                    print('here is message',message)
                    self.conn.sendall(str.encode(message))            
            except Exception as e:
                print(e)
                print("Error sending exception data to server")


    def send_server_heartbeat(self) -> None:
        while self.active:
            self.conn.sendall(str.encode(":heartbeat"))
            time.sleep(5)

    def kill_callback(self) -> None:
        print('kill callback called, shutting down channel', self.channel)
        for module in self.modules:
            module.active = False

    # Here's a version that keeps FileMonitor alive

    # def kill_callback(self) -> None:
    #     print('kill callback called')
    #     for module in self.modules:
    #         if not isinstance(module, FileMonitor):
    #             print(module)
    #             module.active = False
           