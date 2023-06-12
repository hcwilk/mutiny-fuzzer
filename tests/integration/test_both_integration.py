#!/usr/bin/env python3
from argparse import Namespace
import time
import shutil
import traceback
import os
import threading
import sys
sys.path.append('../mutiny-fuzzer')
from tests.assets.campaign_mode_test_two.targets import Target1, Target2, Target3
from backend.mutiny import Mutiny
from tests.assets.campaign_mode_test_two.server import Server
from tests.assets.campaign_mode_test_two.agent import FileMonitor
from tests.assets.campaign_mode_test_two.agent import ProcessMonitor
from tests.assets.campaign_mode_test_two.agent import StatsMonitor
from tests.assets.campaign_mode_test_two.agent import Agent
import multiprocessing


class CampaignIntegrationSuite(object):

    def __init__(self):
        self.target_if = '127.0.0.1'
        self.passed_tests = 0
        self.total_tests = 0


    def test_1(self, proto):
        '''
        test details:
            target1: 
            target2:
            target3: 
        '''

        server_ip = '127.0.0.1'
        server_port = 9876

        health_config = {
            'cpu_multiplier': 1.5,
            'ping_multiplier': 2.5,
            'memory_multiplier': 1.3,
            'disk_multiplier': 1.2
        }


        ports = []
        targets = []
        agent_threads = []
        if proto == 'tcp':
            ports = [6660,6661,6662]
        elif proto == 'udp':
            ports = [6663,6664,6665]
        elif proto == 'raw':
            ports = [6666,6667,6668]
        elif proto == 'ssl':
            ports = [6669,6670,6671]
        else:
            print('unrecognized protocol')
            exit(-1)

                # create Montitor Server object
        server = Server(server_ip, server_port)
        server_thread = threading.Thread(target=server.run)
        server_thread.start()

        targets.append(Target1(proto, '127.0.0.1', ports[0]))
        targets.append(Target2(proto, '127.0.0.1', ports[1]))
        targets.append(Target3(proto, '127.0.0.1', ports[2]))
        processes = []
        for i in range(0, len(targets)):
            process = multiprocessing.Process(target=targets[i].accept_fuzz, args=())
            processes.append(process)
            process.start()
            print('[target {}] listening'.format(i),'on port',ports[i])

        time.sleep(4)

        for i in range(0, len(targets)):

            agent = Agent(server_ip, server_port, str(i), False)
            print('init with pid',processes[i].pid)
            process = ProcessMonitor(agent.monitor_callback, agent.kill_callback, f'Target {str(i)}', processes[i].pid, time_interval = 1)
            file = FileMonitor(agent.monitor_callback, f'tests/assets/campaign_mode_test_two/target_{i+1}/crash.log')
            stats = StatsMonitor(agent.monitor_callback, f'Target {str(i)}', processes[i].pid, '127.0.0.1', 1, health_config)
            agent.modules.append(process)
            agent.modules.append(file)
            agent.modules.append(stats)

            agent_thread = threading.Thread(target=agent.start)
            agent_thread.start()
            agent_threads.append(agent_thread)
            print('[agent {}] started'.format(i))

        
        for i in range(0, len(targets)):
            #joining targets
            processes[i].join()


        


def main():
    
    print('\nCAMPAIGN MODE TARGET SERVERS')
    print('-' * 53)
    suite = CampaignIntegrationSuite()
    try: # SINGLE CRASH -> PAUSE -> RESUME -> FINISH SPECIFIED RANGE
        #tcp
        suite.test_1(proto='tcp')
        # udp 
        #suite.test_1(proto='udp')
        # ssl
        #suite.test_1(proto='ssl')
        # raw
        #suite.test_1(proto='raw')
    except Exception as e:
        print(repr(e))
        traceback.print_exc()




if __name__ == '__main__':
    main()
