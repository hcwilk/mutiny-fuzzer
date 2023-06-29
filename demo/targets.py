# Targets server's accept_fuzz implementation for 
# campaign mode tests

import socket
import sys
import argparse
import multiprocessing
import struct
import os
import ssl


class MockServer(object):
    def __init__(self, proto, listen_if, listen_port):
        self.proto = proto
        self.listen_if = listen_if
        self.listen_port = listen_port
        self.incoming_buffer = []
        self.pid = None

    def accept_connection(self): 
        if self.proto == 'tcp':
            socket_family = socket.AF_INET if '.' in self.listen_if else socket.AF_INET6
            self.listen_conn = socket.socket(socket_family, socket.SOCK_STREAM)
            self.listen_conn.bind((self.listen_if, self.listen_port))
            self.listen_conn.listen()
            self.pid = os.getpid()
            self.communication_conn = self.listen_conn.accept()[0]
        
    

    def receive_packet(self, packet_len):
        if self.communication_conn.type == socket.SOCK_STREAM :
            response = self.communication_conn.recv(packet_len)

            self.incoming_buffer.append(bytearray(response))

        else:
            response, self.addr = self.communication_conn.recvfrom(packet_len)
            self.incoming_buffer.append(bytearray(response))


    def send_packet(self, data):
        if self.communication_conn.type == socket.SOCK_STREAM:
            self.communication_conn.send(data)
    
        else:
            self.communication_conn.sendto(data, self.addr)

class Target1(MockServer):
    
    def accept_fuzz(self):
        self.accept_connection()

        current_dir = os.path.dirname(os.path.abspath(__file__))
        crash_log_path = os.path.join(current_dir, 'crash1.log')

        # accept initial connection
        while True:
            # receive hi
            self.receive_packet(2)
            # send hello, addr not required since tcp
            self.send_packet(bytearray('hello', 'utf-8'))
            self.receive_packet(4096)
            result = self.incoming_buffer.pop()
            if len(result) > 114 and len(result) < 120:
                # 15th iteration should cause a crash
                # write to file that monitor_target is reading
                with open(crash_log_path, 'w') as file:
                    file.write('crashed!!')
                print('[target 1] crash inducing input: {}'.format(result))
                print('[target 1] error: illegal memory access')
                if(len(result) == 118):
                    print(f'[target 1] error: will now crash. Here shte input: {result}')    
                    if self.communication_conn.type == socket.SOCK_STREAM:
                        self.listen_conn.close()
                    self.communication_conn.close()
                    return
            self.send_packet(bytearray('incorrect magic phrase, try again!', 'utf-8'))
            self.communication_conn = self.listen_conn.accept()[0]

class Target2(MockServer):
    
    def accept_fuzz(self):
        self.accept_connection()

        current_dir = os.path.dirname(os.path.abspath(__file__))
        crash_log_path = os.path.join(current_dir, 'crash2.log')

        # accept initial connection
        while True:
            # receive hi
            self.receive_packet(2)
            # send hello, addr not required since tcp
            self.send_packet(bytearray('hello', 'utf-8'))
            self.receive_packet(4096)
            result = self.incoming_buffer.pop()
            if len(result) > 120 and len(result) < 160:

                with open(crash_log_path, 'w') as file:
                    file.write('crashed')
                print('[target 2] crash inducing input: {}'.format(result))
                print('[target 2] error: illegal memory access')
              
            self.send_packet(bytearray('incorrect magic phrase, try again!', 'utf-8'))
            self.communication_conn = self.listen_conn.accept()[0]

class Target3(MockServer):
    
    def accept_fuzz(self):
        self.accept_connection()
        # accept initial connection

        current_dir = os.path.dirname(os.path.abspath(__file__))
        crash_log_path = os.path.join(current_dir, 'crash3.log')

        while True:
            # receive hi
            self.receive_packet(2)
            # send hello, addr not required since tcp
            self.send_packet(bytearray('hello', 'utf-8'))
            self.receive_packet(4096)
            result = self.incoming_buffer.pop()
            if len(result) > 80 and len(result) < 100:

                with open(crash_log_path, 'w') as file:
                    file.write('crashed')
                print('[target 3] crash inducing input: {}'.format(result))
                print('[target 3] error: illegal memory access')
            
            self.send_packet(bytearray('incorrect magic phrase, try again!', 'utf-8'))
            self.communication_conn = self.listen_conn.accept()[0]

def main():
    parser = argparse.ArgumentParser(description='Start a target for fuzzing')
    parser.add_argument('--target', type=int, choices=[1, 2, 3], required=True, help='Target to start (1, 2, or 3)')
    args = parser.parse_args()

    target_ports = {1: 6660, 2: 6661, 3: 6662}

    target_class = globals()[f'Target{args.target}']
    target = target_class('tcp', '127.0.0.1', target_ports[args.target])

    print(f'[target {args.target}] listening on port {target_ports[args.target]}')

    process = multiprocessing.Process(target=target.accept_fuzz, args=())
    process.start()


    print(f'[target {args.target}] started with pid {process.pid}')

if __name__ == "__main__":
    main()