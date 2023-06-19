from argparse import Namespace
import time
import shutil
import traceback
import os
import threading
from multiprocessing import Process
import sys


sys.path.append('../mutiny-fuzzer')
from getmac import get_mac_address as gma
from tests.assets.monitor_test_1.target import Target4
from tests.assets.monitor_test_1.agent import Agent
from tests.assets.monitor_test_1.agent import FileMonitor
from tests.assets.monitor_test_1.agent import ProcessMonitor
from tests.assets.monitor_test_1.agent import StatsMonitor
from tests.assets.monitor_test_1.server import Server
from backend.mutiny import Mutiny
# Integration test to simulate a complete interaction between a target 
# and mutiny in order to evaluate the stability of the fuzzer as a whole.

# To debug, comment out the block_print() calls at the start of each test.
class IntegrationSuite(object):

    def __init__(self):
        self.passed_tests = 0
        self.total_tests = 0

   
    def test_1(self, target_port, proto):

        ## DOES NOT HAVE RAW SOCKET SUPPORT AT THE MOMENT
        ## OR SERVER-SIDE FUNCTIONALITY
        '''
        test details:
            - prepped_fuzz: ./tests/assets/integration_test_1/<proto>_prepped.fuzzer
            - target_host: 127.0.0.1
            - sleep_time: 0
            - range: 0-19
            - loop: None
            - dump_raw: 0
            - quiet: False
            - log_all: False
            - processor_dir: ./tests/assets/integration_test_1/
            - failure_threshold: 3
            - failure_timeout: 5.0
            - receive_timeout: 3.0
            - should_perform_test_run 1
            - port: 7772-7776, unique for each test to avoid 'Address already in use OSError'
            - source_port: -1
            - source_ip: 0.0.0.0

            Fuzzes a target until it finds a 'crash' at seed=7, then sends a pause, 
            sleeps, then sends a resume. Fuzzing stops on seed 10, since a
            range of 0-10 was specified
        '''

        print('test 1: {}'.format(proto))
        self.total_tests += 1


        server_ip = '127.0.0.1'
        server_port = 4321

        prepped_fuzzer_files = ['tests/assets/monitor_test_1/tcp.fuzzer1', 'tests/assets/monitor_test_1/tcp.fuzzer2', 'tests/assets/monitor_test_1/tcp.fuzzer3', 'tests/assets/monitor_test_1/tcp.fuzzer4']

        # set IP to loopback if L2raw, else set to localhost
     
        self.target_if = '127.0.0.1'

        # initialize args for Fuzzing
        
        # set up log file
        fuzz_threads = []
        targets = []
        target_processes = []
        agent_threads = []


        # create Montitor Server object
        server = Server(server_ip, server_port)
        server_thread = threading.Thread(target=server.run)
        server_thread.start()

        number_of_targets = 4

        for i in range(number_of_targets):
            port_decrement = 100 * i
            target = Target4(proto, self.target_if, target_port - port_decrement)
            targets.append(target)


            
            # Start target.accept_fuzz() in new process instead of thread
            target_process = Process(target=target.accept_fuzz)

            target_processes.append(target_process)
            target_process.start()
            print('started')


       # Stand up agents
        for i in range(number_of_targets):

            agent = Agent(server_ip, server_port, str(i), False)
            process = ProcessMonitor(agent.monitor_callback, agent.kill_callback, f'Target {str(i)}', target_processes[i].pid, time_interval = 1)
            file = FileMonitor(agent.monitor_callback, 'tests/assets/monitor_test_1/crash.log')
            stats = StatsMonitor(agent.monitor_callback, f'Target {str(i)}', target_processes[i].pid, self.target_if, 1)
            agent.modules.append(process)
            agent.modules.append(file)
            agent.modules.append(stats)

            agent_thread = threading.Thread(target=agent.start)
            agent_thread.start()
            agent_threads.append(agent_thread)


        # Imitate campaign mode and integrate X amount of targets with different PIDs
        for i in range(number_of_targets):
            args = Namespace(prepped_fuzz = prepped_fuzzer_files[i], target_host = self.target_if, sleep_time = 0, range = '0-10', loop = None, dump_raw = None, quiet = False, log_all = False, testing = True, server = False, channel = str(i), server_ip = server_ip, server_port = server_port)

            fuzzer = Mutiny(args)
            fuzzer.radamsa = os.path.abspath(os.path.join(__file__, '../../../radamsa-0.6/bin/radamsa'))
            fuzzer.import_custom_processors()
            fuzzer.debug = False

            fuzz_thread = threading.Thread(target=fuzzer.fuzz)
            fuzz_thread.start()
            fuzz_threads.append(fuzz_thread)
       

        for target_process in target_processes:
            target_process.join()

        server_thread.join()
        server.shutdown()

        # shutil.rmtree(log_dir)
        # self.enable_print()
        self.passed_tests += 1
        print('ok')

    def block_print(self):
        '''
        Redirect mutiny stdout to /dev/null 
        '''
        sys.stdout = open(os.devnull, 'w')

    def enable_print(self):
        '''
        Restores stdout
        '''
        sys.stdout = sys.__stdout__

def main():
    # create mock target, accept connections in a child thread
    # connect to target using fuzzer
    
    print('\nINTEGRATION TESTING RESULTS')
    print('-' * 53)
    start_time = time.perf_counter()
    suite = IntegrationSuite()

    try: # SINGLE CRASH -> PAUSE -> RESUME -> FINISH SPECIFIED RANGE
        # #tcp
        suite.test_1(target_port= 7781, proto = 'tcp')
        # # udp 
        # suite.test_1(target_port= 7782, proto = 'udp', prepped_fuzzer_file = 'tests/assets/monitor_test_1/udp.fuzzer')
        # # tls
        # suite.test_1(target_port= 7783, proto = 'tls', prepped_fuzzer_file = 'tests/assets/monitor_test_1/tls.fuzzer')
        # raw
        # suite.test_1(target_port= -1, proto = 'L2raw', prepped_fuzzer_file = 'tests/assets/monitor_test_1/raw.fuzzer')
    except Exception as e:
        print(repr(e))
        traceback.print_exc()
    elapsed_time = time.perf_counter() - start_time
    print(f'Ran {suite.total_tests} tests in {elapsed_time:0.3f}s\n')

    if suite.passed_tests == suite.total_tests:
        print('OK')
    else:
        print(f'{suite.total_tests-suite.passed_tests} Failed tests')


if __name__ == '__main__':
    main()
