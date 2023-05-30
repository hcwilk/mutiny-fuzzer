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
        print('agent trying to connect to server')
        self.conn.connect((server_ip, server_port-1500))
        print('agent connected to server')

        # Instantiates the active bool that changes to false when the target process is dead
        self.active = True

        # create a single thread to report the status of the process to the server
        self.server_heartbeat_thread = Thread(target=self.send_server_heartbeat)

        # The number of times we check for a pulse without a response
        self.checking_pulse_attempts = 0

    def start(self) -> None:
        self.server_heartbeat_thread.start()

    def check_process_running(self) -> bool:
        try:
            subprocess.check_output('ps -p '+str(self.pid)+' -o comm=', shell=True)
        except subprocess.CalledProcessError as e: 
            print("Process not found")
            return False
        else:
            return True
        

    def send_server_heartbeat(self) -> None:
        while self.active:
            try:
                if self.check_process_running():
                    print('allgood')
                    
                else:
                    print('not active for some reason')
                    message = 'crashed'
                    self.conn.sendall(str.encode(message))  
                    self.checking_pulse_attempts += 1
                    if self.checking_pulse_attempts > 5:
                        print("Process not found")
                        self.active = False
                    time.sleep(5)

            except Exception as e:
                print(e)
                print("Error sending server heartbeat")
                self.active = False


# if __name__ == '__main__':
#     parser = argparse.ArgumentParser(description="Client details")
#     parser.add_argument("host", help="The server ip to connect to")
#     parser.add_argument("port", help="The port on the server to connect to", type=int)
#     parser.add_argument("-num", help="The PID of the process to montior")

#     args = parser.parse_args()

#     agent = Agent(args.host, args.port, args.num)
#     agent.start()
