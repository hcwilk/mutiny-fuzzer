import socket
from threading import Thread
import subprocess
import sys
import argparse
import time
import psutil


class Agent:
    def __init__(self, server_ip: str, server_port: int, pid: int, host, port) -> None:
        # Only needs to be one way communication, so I think we can cut down on some of the code here

        # The PID of the process to monitor
        self.pid = pid

        # connection with the 'monitor' server (this is a middle-man between Mutiny and the agent)
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Init the connection with the server
        self.conn.connect((server_ip, server_port-1500))
        print('agent connected to server')

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
        self.receive_fuzz_messages = Thread(target=self.receive_fuzz_messages)


        # The number of times we check for a pulse without a response
        self.checking_pulse_attempts = 0

    def start(self) -> None:
        self.server_heartbeat_thread.start()
        self.monitor_process_thread.start()
        self.receive_fuzz_messages.start()

    def monitor_process(self) -> bool:
        try:
            process = psutil.Process(self.pid)
        except psutil.NoSuchProcess:
            print(f"No process found with PID={self.pid}")
            return

        while True:
            try:
                if self.cpu != None:
                    cpu_percent = process.cpu_percent(interval=1)
                    if abs(cpu_percent - self.cpu) >= self.cpu/10:
                        print(f"Unusual CPU percent: {cpu_percent}%")     
                        break
                # Get process details
                self.cpu = process.cpu_percent(interval=1)
                self.mem = process.memory_info()

                # print(f"CPU percent: {self.cpu}%")
                # print(f"Memory usage: {self.mem.rss / (1024**2)} MB")

                time.sleep(.01)  # Sleep for 5 seconds before next check
            except psutil.NoSuchProcess:
                print(f"Process with PID={self.pid} has terminated")
                break
        

    def monitor_program_logs(self) -> None:
        while self.active:
            log_file = open('./tests/assets/integration_test_4/crash.log', 'r')
            if 'crashed' in log_file.readlines():
                print('process crashed, check these last three messages: ', self.log[-3:])
                message = 'crashed'
                self.conn.sendall(str.encode(message))  
                log_file.close()
                log_file = open('./tests/assets/integration_test_4/crash.log', 'w')
                log_file.write('')
                log_file.close()
                self.active = False
            log_file.close()

    def receive_fuzz_messages(self) -> None:
        while self.active:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # Bind to the server address
                s.bind((self.host, self.port))
                print('agent bound to receive fuzz messages')
                print(f"Server started at {self.host}:{self.port}")
                while True:
                    # Receive message
                    message, addr = s.recvfrom(1024)
                    print(f"Received message from {addr}: {message}")
                    self.log.append(message)

