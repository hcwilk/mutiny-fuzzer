import socket
from threading import Thread
import argparse
import sys
import json


# Class that handles each client connection (both mutiny and remote-agent)
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

    def send_exception(self, exception_info:str) -> None:
        try:
            self.conn.sendall(exception_info.encode())
        except Exception as e:
            print(e)
            print("Could not send exception data to mutiny client")

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
                    if decoded == ':quit' or decoded == '':
                        print(f"[{self.id}] Client Disconnecting")
                        self.send_quit()
                        return
                    print(
                        f"[{self.id}] {self.channel} {self.address} ({self.type}): {decoded}")
                    if decoded[0] == '!':
                        self.exception_callback(decoded, self.id, self.channel[0])
                except Exception as e:
                    print(
                        f"Could not receive data from client {self.id}. Disconnecting with error: {e}")
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

    def add_exception(self, exception_info, agent_id, channel):
        for conn in self.connections:
            if conn.type == 'mutiny' and (channel in conn.channel or 'all' in conn.channel):
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