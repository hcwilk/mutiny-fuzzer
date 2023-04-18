#!/usr/bin/env python3
#------------------------------------------------------------------
# November 2014, created within ASIG
# Author James Spadaro (jaspadar)
# Co-Author Lilith Wyatt (liwyatt)
#------------------------------------------------------------------
# Copyright (c) 2014-2022 by Cisco Systems, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the Cisco Systems, Inc. nor the
#    names of its contributors may be used to endorse or promote products
#    derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS "AS IS" AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#------------------------------------------------------------------
# Mock Target object that can be extended for integration and unit tests 
# to act as a fake target for mutiny to fuzz
#------------------------------------------------------------------

import socket
import ssl
from backend.packets import PROTO
from time import sleep

class MockTarget(object):
    def __init__(self, proto, listen_if, listen_port):
        self.proto = proto
        self.listen_if = listen_if
        self.listen_port = listen_port
        self.incoming_buffer = []

    def accept_connection(self): 
        if self.proto == 'tcp':
            socket_family = socket.AF_INET if '.' in self.listen_if else socket.AF_INET6
            self.listen_conn = socket.socket(socket_family, socket.SOCK_STREAM)
            self.listen_conn.bind((self.listen_if, self.listen_port))
            self.listen_conn.listen()
            self.communication_conn = self.listen_conn.accept()[0]
        elif self.proto == 'tls':
            socket_family = socket.AF_INET if '.' in self.listen_if else socket.AF_INET6
            self.listen_conn = socket.socket(socket_family, socket.SOCK_STREAM)
            try:
                _create_unverified_https_context = ssl._create_unverified_context
            except AttributeError:
                pass
            else:
                ssl._create_default_https_context = _create_unverified_https_context
            
            self.listen_conn.bind((self.listen_if, self.listen_port))
            self.listen_conn.listen()
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain('./tests/assets/test-server.pem', './tests/assets/test-server.key')
            self.listen_conn = context.wrap_socket(self.listen_conn, server_side=True)
            self.communication_conn = self.listen_conn.accept()[0]
        elif self.proto == 'udp':
            socket_family = socket.AF_INET if  '.' in self.listen_if else socket.AF_INET6
            self.communication_conn = socket.socket(socket_family, socket.SOCK_DGRAM)
            self.communication_conn.bind((self.listen_if, self.listen_port))
        else: # raw
            proto_num = 0x300 if self.proto == 'L2raw' else PROTO[self.proto]
            self.communication_conn = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, proto_num)
            if self.proto != 'L2raw' and self.proto != 'raw':
                self.communication_conn.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 0)
            print('This is the listening mac address',self.listen_if)
            self.communication_conn.bind((self.listen_if, 0))


    def receive_packet(self, packet_len):
        if self.communication_conn.type == socket.SOCK_STREAM  or self.communication_conn.type == socket.SOCK_RAW:
            self.incoming_buffer.append(bytearray(self.communication_conn.recv(packet_len)))
        else:
            response, self.addr = self.communication_conn.recvfrom(packet_len)
            self.incoming_buffer.append(bytearray(response))


    def send_packet(self, data):
        if self.communication_conn.type == socket.SOCK_STREAM:
            self.communication_conn.send(data)
        else:
            self.communication_conn.sendto(data, self.addr)



class MockClient(object):
    def __init__(self, proto, client_addr, client_port, target_addr, target_port):
        self.proto = proto
        self.client_addr = client_addr
        self.client_port = client_port
        self.target_addr = target_addr
        self.target_port = target_port
        self.incoming_buffer = []

    def connect(self):
        # Client is on it's own thread, but we have to sleep here to let server set up properly
        sleep(1.5)
        if self.proto == 'tcp':

            print('heres where im binding to ',self.client_addr, ' on port ', str(self.client_port))
            print('trying to connect to',self.target_addr, ' on port ', str(self.target_port))
            socket_family = socket.AF_INET if '.' in self.client_addr else socket.AF_INET6
            self.communication_conn = socket.socket(socket_family, socket.SOCK_STREAM)
            self.communication_conn.bind((self.client_addr, self.client_port))
            self.communication_conn.connect((self.target_addr, self.target_port))

            print('Client is Connected!')
        elif self.proto == 'tls':
        
            socket_family = socket.AF_INET if f'.' in self.client_addr else socket.AF_INET6
            try:
                _create_unverified_https_context = ssl._create_unverified_context
            except AttributeError:
            # Legacy Python that doesn't verify HTTPS certificates by default
                pass
            else:
            # Handle target environment that doesn't support HTTPS verification
                ssl._create_default_https_context = _create_unverified_https_context

            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            tcp_connection = socket.socket(socket_family, socket.SOCK_STREAM)

            self.communication_conn = context.wrap_socket(tcp_connection, server_hostname=self.target_addr)
            self.communication_conn.bind((self.client_addr, self.client_port))
            self.communication_conn.settimeout(15.0) 
            try:
                self.communication_conn.connect((self.target_addr, self.target_port))
                print('Client connected with TLS!')
            except Exception as e:
                print(f"Error connecting to {self.target_addr} on port {self.target_port}: {str(e)}")            
        elif self.proto == 'udp':

            socket_family = socket.AF_INET if '.' in self.client_addr else socket.AF_INET6
            self.communication_conn = socket.socket(socket_family, socket.SOCK_DGRAM)
            self.communication_conn.bind((self.client_addr, self.client_port))

        else:
            proto_num = 0x300 if self.proto == 'L2raw' else PROTO[self.proto]
            self.communication_conn = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, proto_num)

    def send_packet(self, data):
        if self.communication_conn.type == socket.SOCK_STREAM:
            self.communication_conn.send(data)
        else:
            print('sending with UDP to ', self.target_addr, " on port ",self.target_port)
            self.communication_conn.sendto(data, (self.target_addr, self.target_port))

    def receive_packet(self, packet_len):
        if self.communication_conn.type == socket.SOCK_STREAM or self.communication_conn.type == socket.SOCK_RAW:
            response = self.communication_conn.recv(packet_len)
            self.incoming_buffer.append(bytearray(response))
            return response
        else:
            response, addr = self.communication_conn.recvfrom(packet_len)
            self.incoming_buffer.append(bytearray(response))

            return response
