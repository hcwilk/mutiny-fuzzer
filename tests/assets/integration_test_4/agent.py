import socket
from threading import Thread, Lock
import subprocess
import sys
import argparse
import time
import psutil


class Agent:
    def __init__(self, server_ip: str, server_port: int, pid: int, host, port) -> None:

        self.lock = Lock()

        # Only needs to be one way communication, so I think we can cut down on some of the code here
        self.agent_logfile = open('./tests/assets/integration_test_4/agent.log', 'w')
        self.agent_logfile.write('Agent log file\n')
        self.agent_logfile.close()

        # The PID of the process to monitor
        self.pid = pid

        # connection with the 'monitor' server (this is a middle-man between Mutiny and the agent)
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Init the connection with the server
        self.conn.connect((server_ip, server_port-1500))
        print('agent connected to monitor server')

        # Instantiates the active bool that changes to false when the target process is dead
        self.active = True

        # create a single thread to report the status of the process to the server
        self.server_heartbeat_thread = Thread(target=self.monitor_program_logs)

        self.monitor_process_thread = Thread(target=self.monitor_process)
        self.cpu = None
        self.mem = None

        self.host = host
        self.port = port
        self.log = []
        self.receive_fuzz_messages_thread = Thread(target=self.receive_fuzz_messages)


        # The number of times we check for a pulse without a response
        self.checking_pulse_attempts = 0

    def start(self) -> None:
        self.server_heartbeat_thread.start()
        self.monitor_process_thread.start()
        self.receive_fuzz_messages_thread.start()

        self.server_heartbeat_thread.join()
        self.monitor_process_thread.join()
        self.receive_fuzz_messages_thread.join()

    # Monitors the programs's CPU and memory usage. Right now it just uses CPU, but if we can decide on a solid rule for memory usage, we can add that in too
    def monitor_process(self) -> bool:
        try:
            process = psutil.Process(self.pid)
        except psutil.NoSuchProcess:
            print(f"No process found with PID={self.pid}")
            return

        while True:
            try:
                if self.cpu != None:
                    cpu_percent = process.cpu_percent(interval=.1)
                    if abs(cpu_percent - self.cpu) >= self.cpu/10:
                        print(f"Unusual CPU percent: {cpu_percent}%, check these last three messages: ", self.log[-3:])   
                        with self.lock:
                            self.agent_logfile = open('./tests/assets/integration_test_4/agent.log', 'a')
                            self.agent_logfile.write('here are the inputs that couldve caused a CPU fluctuation: {}\n'.format(self.log[-3:]))
                            self.agent_logfile.close()
  
                        break
                else:
                    self.cpu = process.cpu_percent(interval=.1)
                    # self.mem = process.memory_info()

                print(f"CPU percent: {self.cpu}%")
                # print(f"Memory usage: {self.mem.rss / (1024**2)} MB")

                time.sleep(.1)
            except psutil.NoSuchProcess:
                print(f"Process with PID={self.pid} has terminated")
                break
        
    # This would probably just be a syslog monitor in the real world, but this is a good enough solution for now
    def monitor_program_logs(self) -> None:
        while self.active:
            log_file = open('./tests/assets/integration_test_4/crash.log', 'r')
            if 'crashed' in log_file.readlines():
                message = 'crashed'
                self.conn.sendall(str.encode(message))  
                log_file.close()
                log_file = open('./tests/assets/integration_test_4/crash.log', 'w')
                log_file.write('')
                log_file.close()
                self.active = False
                with self.lock:
                    self.agent_logfile = open('./tests/assets/integration_test_4/agent.log', 'a')
                    self.agent_logfile.write('here is the input that most likely caused a crash: {}\n'.format(self.log[-1]))
                    self.agent_logfile.close()
            log_file.close()

    # This allows the agent to receive copies of the fuzz messages so we're able to tell what could've caused a problem
    def receive_fuzz_messages(self) -> None:
        while self.active:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # Bind to the server address
                s.bind((self.host, self.port))
                print(f"Agent started at {self.host}:{self.port}")

                s.settimeout(1)
                while True:
                    try:
                        # Receive message
                        message, addr = s.recvfrom(1024)
                        print(f"Received message from {addr}: {message}")
                        self.log.append(message)
                    except socket.timeout:
                        # If no message arrives within the timeout, check if the thread should still be active
                        if not self.active:
                            break

