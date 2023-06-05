#!/usr/bin/env python
#------------------------------------------------------------------
# November 2014, created within ASIG
# Author James Spadaro (jaspadar)
# Co-Author Lilith Wyatt (liwyatt)
#------------------------------------------------------------------
# Copyright (c) 2014-2017 by Cisco Systems, Inc.
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
#
# Copy this file to your project's mutiny classes directory to
# implement a long-running thread to monitor your target
# This is useful for watching files, logs, remote connections,
# PIDs, etc in parallel while mutiny is operating
# This parallel thread can signal Mutiny when it detects a crash
#
#------------------------------------------------------------------

from mutiny_classes.mutiny_exceptions import *
from time import sleep
import socket

class Monitor(object):
    # Set to True to use the monitor
    is_enabled = True
    
    # This function will run asynchronously in a different thread to monitor the host
    def monitor_target(self, target_ip, target_port, signal_main):

        # initialize the socket for the agent to connect to
        socket_family = socket.AF_INET if '.' in target_ip else socket.AF_INET6
        self.listen_conn = socket.socket(socket_family, socket.SOCK_STREAM)
        self.listen_conn.bind((target_ip, target_port-1500))
        self.listen_conn.listen()

        # accepting the agent connection
        self.communication_conn = self.listen_conn.accept()[0]


        while True:
            
            data = self.communication_conn.recv(1024)
            print('received data')
            decoded = data.decode('utf-8')
            if decoded =='crashed':
                print('got crashed')
                exception = LogCrashException('crashed')
                signal_main(LogCrashException(exception))
                signal_main(PauseFuzzingException('Sleeping for 10 seconds'))
                sleep(.05)
                signal_main(ResumeFuzzingException())