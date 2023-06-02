import socket
from threading import Thread
import subprocess
import sys
import argparse
import time


class Agent:
    def __init__(self, server_ip: str, server_port: int, pid: int) -> None:
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

        # The number of times we check for a pulse without a response
        self.checking_pulse_attempts = 0

    def start(self) -> None:
        self.server_heartbeat_thread.start()

    def check_process_running(self) -> bool:
        # Isn't being used now, but I want this to be able to work for local PIDs
        # Not sure exactly what I should be calling to get this done
        try:
            subprocess.check_output('ps -p '+str(self.pid)+' -o comm=', shell=True)
        except subprocess.CalledProcessError as e: 
            print("Process not found")
            return False
        else:
            return True
        

    def monitor_program_logs(self) -> None:

        while self.active:
            # Check if the process is still running
            # ideally, this will revolve around the PID instead of reading a log file
            # Is there a 'webhook' for PID events? I feel like querying the PID over and over will be computationally intensive
            # It could also lag behind the actual process state
            log_file = open('./tests/assets/integration_test_4/crash.log', 'r')
            if 'crashed' in log_file.readlines():
                message = 'crashed'
                self.conn.sendall(str.encode(message))  
                log_file.close()
                log_file = open('./tests/assets/integration_test_4/crash.log', 'w')
                log_file.write('')
                log_file.close()
                self.active = False
            log_file.close()

