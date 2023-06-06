import socket
from threading import Thread, Lock
import subprocess
import sys
import argparse
import time
import psutil


class Agent:
    def __init__(self, server_ip: str, server_port: int, pid: int, channel: str, type: str = 'remote-agent') -> None:

        self.lock = Lock()

        # # Only needs to be one way communication, so I think we can cut down on some of the code here
        # self.agent_logfile = open('./tests/assets/integration_test_4/agent.log', 'w')
        # self.agent_logfile.write('Agent log file\n')
        # self.agent_logfile.close()

        # The PID of the process to monitor
        self.pid = pid

        # connection with the 'monitor' server (this is a middle-man between Mutiny and the agent)
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Init the connection with the server
        self.conn.connect((server_ip, server_port))

        self.conn.sendall(str.encode(f'{channel}|{type}'))

        print('here is the pid of the process Im monitoring: ' + str(self.pid))

        # Instantiates the active bool that changes to false when the target process is dead
        self.active = True

        # create a single thread to report the status of the process to the server
        self.server_heartbeat_thread = Thread(target=self.monitor_program_logs)

        self.monitor_process_thread = Thread(target=self.monitor_process)
        self.cpu = None
        self.mem = None

        # self.host = host
        # self.port = port
        # self.log = []
        # self.receive_fuzz_messages_thread = Thread(target=self.receive_fuzz_messages)


        # The number of times we check for a pulse without a response
        self.checking_pulse_attempts = 0

    def start(self) -> None:
        self.server_heartbeat_thread.start()
        self.monitor_process_thread.start()

        self.server_heartbeat_thread.join()
        self.monitor_process_thread.join()

    # Monitors the programs's CPU and memory usage. Right now it just uses CPU, but if we can decide on a solid rule for memory usage, we can add that in too
    def monitor_process(self) -> bool:
        try:
            process = psutil.Process(self.pid)
        except psutil.NoSuchProcess:
            print(f"No process found with PID={self.pid}")
            return

        while True:
            try:
                print('trying to get CPU percent')
                if self.cpu != None:
                    print('making comparison')
                    cpu_percent = process.cpu_percent(interval=.1)
                    if abs(cpu_percent - self.cpu) >= self.cpu/10:
                        print(f"Unusual CPU percent: {cpu_percent}%, check these last three messages")   
                        # with self.lock:
                        #     self.agent_logfile = open('./tests/assets/integration_test_4/agent.log', 'a')
                        #     self.agent_logfile.write('here are the inputs that couldve caused a CPU fluctuation: {}\n'.format(self.log[-3:]))
                        #     self.agent_logfile.close()
  
                        break
                else:
                    print('setting')
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
                print('trying to send')
                message = 'crashed'
                self.conn.sendall(str.encode(message))  
                log_file.close()
                log_file = open('./tests/assets/integration_test_4/crash.log', 'w')
                log_file.write('')
                log_file.close()
                self.active = False
                # with self.lock:
                #     self.agent_logfile = open('./tests/assets/integration_test_4/agent.log', 'a')
                #     self.agent_logfile.write('here is the input that most likely caused a crash: {}\n'.format(self.log[-1]))
                #     self.agent_logfile.close()
            log_file.close()


