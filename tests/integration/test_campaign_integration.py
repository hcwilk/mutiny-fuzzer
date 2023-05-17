#!/usr/bin/env python3
from argparse import Namespace
import time
import shutil
import traceback
import os
import threading
import sys
sys.path.append('../mutiny-fuzzer')
from tests.assets.campaign_mode_test.targets import Target1, Target2, Target3
from backend.mutiny import Mutiny

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

        ports = []
        targets = []
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

        targets.append(Target1(proto, '127.0.0.1', ports[0]))
        targets.append(Target2(proto, '127.0.0.1', ports[1]))
        targets.append(Target3(proto, '127.0.0.1', ports[2]))
        for i in range(0, len(targets)):
            thread = threading.Thread(target=targets[i].accept_fuzz, args=())
            thread.start()
            print('[target {}] listening'.format(i),'on port',ports[i])


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
