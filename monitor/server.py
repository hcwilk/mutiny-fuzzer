import socket
from threading import Thread
import argparse
import sys
import logging


class ClientThread(Thread):

    def __init__(self, connection: socket.socket, address, id: int, exception_callback, type: str = "", channel: list[str] = []) -> None:
        Thread.__init__(self)
        self.conn = connection
        self.address = address
        self.id = id
        self.type = type
        self.channel = channel
        self.active = True
        self.exception_callback = exception_callback

    def send_quit(self) -> None:
        self.active = False
        try:
            self.conn.sendall(':quit'.encode())
        except Exception as e:
            print(e)
            print("Could not send :quit signal")

    def send_exception(self, exception_info: str) -> None:
        try:
            self.conn.sendall(exception_info.encode())
        except Exception as e:
            print(e)
            print("Could not send exception data to mutiny client")
            self.send_quit()

    def run(self) -> None:
        try:
            data = self.conn.recv(1024)
            decoded = data.decode('utf-8').split("|")
            self.channel.append(decoded[0])
            self.type = decoded[1]
        except Exception as e:
            print(e)
            print(
                "New client could not be created. Data must be sent in the form of {channel}|{type}")
            self.send_quit()
        if self.type != 'mutiny':
            while self.active:
                try:
                    self.conn.settimeout(15)
                    data = self.conn.recv(1024)
                    decoded = data.decode('utf-8')
                    message = decoded[1:]
                    if decoded[0] == ':':
                        decoded = decoded[1:]
                        if decoded == 'quit':
                            print(f"[{self.id}] Client Disconnecting")
                            self.send_quit()
                            return
                        if decoded == 'heartbeat':
                            pass
                    elif decoded[0] == '!':
                        print(
                            f"\033[91m[{self.id}] {self.channel} {self.address} ({self.type}): {message}\033[0m")
                        self.exception_callback(
                            message, self.id, self.channel[0])
                    elif decoded[0] == '?':
                          self.exception_callback(message, self.id, self.channel[0])
                    elif decoded[0] == '#':
                        self.exception_callback(decoded, self.id, self.channel[0])             
                    else:
                        print(
                            f"[{self.id}] {self.channel} {self.address} ({self.type}): {decoded}")
                except Exception as e:
                    print(
                        f"Could not receive data from client {self.id}. Disconnecting.")
                    self.send_quit()


class Server(Thread):
    def __init__(self, ip: str, port: int) -> None:
        Thread.__init__(self)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((ip, port))
        self.socket.listen()

        self.connections: list[ClientThread] = []
        self.total_connections = 0

        self.active = True

          # Create a logger
        self.logger = logging.getLogger('ServerLogger')
        self.logger.setLevel(logging.ERROR)  # Log only error and above

        # Create a file handler
        handler = logging.FileHandler('server.log')  # Log to server.log in current directory
        handler.setLevel(logging.ERROR)

        # Create a logging format
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        # Add the handler to the logger
        self.logger.addHandler(handler)

    def add_exception(self, exception_info, agent_id, channel):
        if exception_info[0] == '#':    
            self.logger.error(f'Exception in Monitoring Module {channel}: {exception_info}')
        else:

            self.logger.error(f'Exception in target {channel}: {exception_info}')
            for conn in self.connections:
                if conn.active and conn.type == 'mutiny' and (channel in conn.channel or 'all' in conn.channel):
                    conn.send_exception(exception_info)

    def run(self) -> None:
        while self.active:
            new_conn, address = self.socket.accept()
            self.connections.append(ClientThread(
                new_conn, address, self.total_connections, self.add_exception, channel=[]))
            self.total_connections += 1
            self.connections[-1].start()

    def shutdown(self) -> None:
        for conn in self.connections:
            if conn.active:
                conn.send_quit()
        self.active = False
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description='Run a server.')
    parser.add_argument('--ip', type=str, help='The IP to bind the server to.')
    parser.add_argument('--port', type=int, help='The port to bind the server to.')

    args = parser.parse_args()

    server = Server(args.ip, args.port)
    server.start()

if __name__ == '__main__':
    main()