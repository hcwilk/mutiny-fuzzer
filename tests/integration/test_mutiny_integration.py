from argparse import Namespace
import time
import shutil
import traceback
import os
import threading
import sys

sys.path.append('../mutiny-fuzzer')
from tests.assets.mock_targets import MockServer
from getmac import get_mac_address as gma
from tests.assets.integration_test_1.target import Target1
from tests.assets.integration_test_2.target import Target2
from tests.assets.integration_test_3.target import Target3
from tests.assets.integration_test_4.target import Target4
from tests.assets.integration_test_4.agent import Agent
from backend.mutiny import Mutiny
# Integration test to simulate a complete interaction between a target 
# and mutiny in order to evaluate the stability of the fuzzer as a whole.

# To debug, comment out the block_print() calls at the start of each test.
class IntegrationSuite(object):

    def __init__(self):
        self.passed_tests = 0
        self.total_tests = 0


    def test_1(self, target_port, proto, prepped_fuzzer_file):
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
        # self.block_print() 
        # populate args

        if proto=='L2raw':
            self.target_if = gma()
        else:
            self.target_if = '127.0.0.1'


        args = Namespace(prepped_fuzz = prepped_fuzzer_file, target_host = self.target_if, sleep_time = 0, range = '0-10', loop = None, dump_raw = None, quiet = False, log_all = False, testing = True, server = False)

        log_dir = prepped_fuzzer_file.split('.')[0] + '_logs'
        # stand up target server
        target = Target1(proto, self.target_if, target_port)
        if proto=='L2raw':
            target.addr = self.target_if
        # run mutiny
        fuzzer = Mutiny(args)
        fuzzer.radamsa = os.path.abspath( os.path.join(__file__, '../../../radamsa-0.6/bin/radamsa'))
        fuzzer.import_custom_processors()
        fuzzer.debug = False
        # start listening for the fuzz sessions
        target_thread = threading.Thread(target=target.accept_fuzz, args=())
        target_thread.start()
        fuzz_thread = threading.Thread(target=fuzzer.fuzz, args=())
        fuzz_thread.start() # connect to target and begin fuzzing
        target_thread.join()
        fuzz_thread.join()

        print('threads')
        for thread in threading.enumerate():
            print(thread)
        if target.communication_conn:
            target.communication_conn.close()
        else:
            target.listen_conn.close()
        shutil.rmtree(log_dir)
        self.enable_print()
        self.passed_tests += 1
        print('ok')

    def test_2(self, target_port, proto, prepped_fuzzer_file):
        time.sleep(2)
        '''
        test details:
            - prepped_fuzz: ./tests/assets/integration_test_2/<proto>_prepped.fuzzer
            - target_host: 127.0.0.1
            - sleep_time: 0
            - range: None
            - loop: None
            - dump_raw: 0
            - quiet: False
            - log_all: False
            - processor_dir: ./tests/assets/integration_test_2/
            - failure_threshold: 3
            - failure_timeout: 5.0
            - receive_timeout: 3.0
            - should_perform_test_run 1
            - port: 7768-7771, unique for each test to avoid 'Address already in use OSError'
            - source_port: -1
            - source_ip: 0.0.0.0

            Fuzzes a target until it finds a 'crash' at seed=10, using a single
            outbound line to test against regression on the bug described in issue #11,
            upon reception of the crash, the monitor sends a HaltException to mutiny to halt execution
        '''
        self.total_tests += 1
        print('test 2: {}'.format(proto))


        if proto=='L2raw':
            self.target_if = gma()
        else:
            self.target_if = '127.0.0.1'
        #self.block_print() 
        # populate args
        args = Namespace(prepped_fuzz = prepped_fuzzer_file, target_host = self.target_if, sleep_time = 0, range = '0-', loop = None, dump_raw = None, quiet = False, log_all = False, testing = True, server=False)

        log_dir = prepped_fuzzer_file.split('.')[0] + '_logs'
        # stand up target server
        target = Target2(proto, self.target_if, target_port)
        # run mutiny
        fuzzer = Mutiny(args)
        fuzzer.radamsa = os.path.abspath( os.path.join(__file__, '../../../radamsa-0.6/bin/radamsa'))
        fuzzer.import_custom_processors()
        fuzzer.debug = False
        time.sleep(.5)
        # start listening for the fuzz sessions
        target_thread = threading.Thread(target=target.accept_fuzz, args=())
        target_thread.start()
        time.sleep(.5) # avoid race with connection to socket
        fuzz_thread = threading.Thread(target=fuzzer.fuzz, args=())
        time.sleep(.5)
        fuzz_thread.start() # connect to target and begin fuzzing
        target_thread.join()
        if target.communication_conn:
            target.communication_conn.close()
        else:
            target.listen_conn.close()
        shutil.rmtree(log_dir)
        self.enable_print()
        self.passed_tests += 1
        print('ok')


    def test_3(self, target_port, cli_port, proto, prepped_fuzzer_file):
        '''
        test details:
            - prepped_fuzz: ./tests/assets/integration_test_3/<proto>_prepped.fuzzer
            - target_host: 127.0.0.1
            - sleep_time: 0
            - range: None
            - loop: None
            - dump_raw: 0
            - quiet: False
            - log_all: False
            - processor_dir: ./tests/assets/integration_test_3/
            - failure_threshold: 3
            - failure_timeout: 5.0
            - receive_timeout: 3.0
            - should_perform_test_run 1
            - port: 7768-7771, unique for each test to avoid 'Address already in use OSError'
            - source_port: -1
            - source_ip: 0.0.0.0

            Integration test to validate correctness of --server mode, i.e., fuzzing of a client rather
            than a server
        '''
        self.total_tests += 1
        print('test 3: {}'.format(proto))
        #self.block_print() 
        # populate args

        if proto=='L2raw':
            self.target_if = gma()
            cli_if = gma()
        else:
            self.target_if = '127.0.0.1'
            cli_if = '127.0.0.1'

        
        args = Namespace(prepped_fuzz = prepped_fuzzer_file, source_ip = cli_if, source_port = cli_port, target_host = self.target_if, sleep_time = 0, range = '0-10', loop = None, dump_raw = None, quiet = False, log_all = False, testing = True, server = True)
        log_dir = prepped_fuzzer_file.split('.')[0] + '_logs'
        # stand up target client
        target = Target3(proto, cli_if, cli_port, self.target_if, target_port)
        # run mutiny
        fuzzer = Mutiny(args)
        fuzzer.radamsa = os.path.abspath( os.path.join(__file__, '../../../radamsa-0.6/bin/radamsa'))
        fuzzer.import_custom_processors()
        fuzzer.debug = False
        fuzz_thread = threading.Thread(target=fuzzer.fuzz, args=())
        fuzz_thread.start() # connect to target and begin fuzzing
        time.sleep(.5) # avoid race with connection to socket
        target_thread = threading.Thread(target=target.connect_fuzz, args=())
        target_thread.start()
        time.sleep(.5) # avoid race with connection to socket
        # This should probbaly send the first packet
        time.sleep(1)
        target_thread.join()
        if target.communication_conn:
            target.communication_conn.close()
        else:
            target.listen_conn.close()
        shutil.rmtree(log_dir)
        self.enable_print()
        self.passed_tests += 1
        print('ok')

    def test_4(self, target_port, proto, prepped_fuzzer_file):

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
        print('test 4: {}'.format(proto))
        self.total_tests += 1
        # self.block_print() 
        # populate args

        # set IP to loopback if L2raw, else set to localhost
        if proto=='L2raw':
            self.target_if = gma()
        else:
            self.target_if = '127.0.0.1'

        # initialize args for Fuzzing
        args = Namespace(prepped_fuzz = prepped_fuzzer_file, target_host = self.target_if, sleep_time = 0, range = '0-10', loop = None, dump_raw = None, quiet = False, log_all = False, testing = True, server = False)
        
        # set up log file
        log_dir = prepped_fuzzer_file.split('.')[0] + '_logs'
        # stand up target server
        target1 = Target4(proto, self.target_if, target_port)
        target2 = Target4(proto, self.target_if, target_port-100)
        target3 = Target4(proto, self.target_if, target_port-200)
        target4 = Target4(proto, self.target_if, target_port-300)
    
        # run mutiny
        fuzzer = Mutiny(args)
        fuzzer.radamsa = os.path.abspath( os.path.join(__file__, '../../../radamsa-0.6/bin/radamsa'))
        fuzzer.import_custom_processors()
        fuzzer.debug = False

        # start listening for the fuzz sessions
        target_thread = threading.Thread(target=target1.accept_fuzz, args=())
        target_thread.start()
        target_thread = threading.Thread(target=target2.accept_fuzz, args=())
        target_thread.start()
        target_thread = threading.Thread(target=target3.accept_fuzz, args=())
        target_thread.start()
        target_thread = threading.Thread(target=target4.accept_fuzz, args=())
        target_thread.start()
        time.sleep(1)

        # start the agent
        agent1 = Agent(self.target_if, target_port, pid = target1.pid, host='127.0.0.1', port=4321)
        agent_thread_1 = threading.Thread(target=agent1.start, args=())
        agent_thread_1.start()

        agent2 = Agent(self.target_if, target_port, pid = target2.pid, host='127.0.0.1', port=4321)
        agent_thread_2 = threading.Thread(target=agent2.start, args=())
        agent_thread_2.start()

        agent = Agent(self.target_if, target_port, pid = target.pid, host='127.0.0.1', port=4321)
        agent_thread = threading.Thread(target=agent.start, args=())
        agent_thread.start()

        agent = Agent(self.target_if, target_port, pid = target.pid, host='127.0.0.1', port=4321)
        agent_thread = threading.Thread(target=agent.start, args=())
        agent_thread.start()
        time.sleep(2)

        # start the fuzzer
        fuzz_thread = threading.Thread(target=fuzzer.fuzz, args=())
        fuzz_thread.start() # connect to target and begin fuzzing
        target_thread.join()
        fuzz_thread.join()
        # agent_thread.join()
        print('threads')
        for thread in threading.enumerate():
            print(thread)


        if target.communication_conn:
            target.communication_conn.close()
        else:
            target.listen_conn.close()
        shutil.rmtree(log_dir)
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
        suite.test_1(target_port= 7772, proto = 'tcp', prepped_fuzzer_file = 'tests/assets/integration_test_1/tcp.fuzzer')
        # # udp 
        # suite.test_1(target_port= 7773, proto = 'udp', prepped_fuzzer_file = 'tests/assets/integration_test_1/udp.fuzzer')
        # # tls
        # suite.test_1(target_port= 7774, proto = 'tls', prepped_fuzzer_file = 'tests/assets/integration_test_1/tls.fuzzer')
        # raw
        # suite.test_1(target_port= -1, proto = 'L2raw', prepped_fuzzer_file = 'tests/assets/integration_test_1/raw.fuzzer')
    except Exception as e:
        print(repr(e))
        traceback.print_exc()

    # try: # SINGLE OUTBOUND LINE -> CRASH -> HALT
    #     #tcp
    #     suite.test_2(target_port= 7775, proto = 'tcp', prepped_fuzzer_file = 'tests/assets/integration_test_2/tcp.fuzzer')
    #     # udp 
    #     suite.test_2(target_port= 7776, proto = 'udp', prepped_fuzzer_file = 'tests/assets/integration_test_2/udp.fuzzer')
    #     # tls 
    #     suite.test_2(target_port= 7777, proto = 'tls', prepped_fuzzer_file = 'tests/assets/integration_test_2/tls.fuzzer')
    #     # raw
    #     suite.test_2(target_port = -1, proto = 'L2raw', prepped_fuzzer_file = 'tests/assets/integration_test_2/raw.fuzzer')
    # except Exception as e:
    #     print(repr(e))
    #     traceback.print_exc()

    # try: # SINGLE OUTBOUND LINE -> CRASH -> HALT
    #     # tcp
    #     suite.test_3(target_port= 7778, cli_port=52954, proto = 'tcp', prepped_fuzzer_file = 'tests/assets/integration_test_3/tcp.fuzzer')
    #     # udp 
    #     suite.test_3(target_port= 7779, cli_port=52955, proto = 'udp', prepped_fuzzer_file = 'tests/assets/integration_test_3/udp.fuzzer')
    #     # tls 
    #     suite.test_3(target_port= 7780, cli_port=52956, proto = 'tls', prepped_fuzzer_file = 'tests/assets/integration_test_3/tls.fuzzer')
    #     # raw
    #     suite.test_3(target_port = -1, cli_port=-1, proto = 'L2raw', prepped_fuzzer_file = 'tests/assets/integration_test_3/raw.fuzzer')
    # except Exception as e:
    #     print(repr(e))
    #     traceback.print_exc()


    try: # SINGLE CRASH -> PAUSE -> RESUME -> FINISH SPECIFIED RANGE
        # #tcp
        suite.test_4(target_port= 7781, proto = 'tcp', prepped_fuzzer_file = 'tests/assets/integration_test_4/tcp.fuzzer')
        # # udp 
        # suite.test_1(target_port= 7782, proto = 'udp', prepped_fuzzer_file = 'tests/assets/integration_test_4/udp.fuzzer')
        # # tls
        # suite.test_1(target_port= 7783, proto = 'tls', prepped_fuzzer_file = 'tests/assets/integration_test_4/tls.fuzzer')
        # raw
        # suite.test_1(target_port= -1, proto = 'L2raw', prepped_fuzzer_file = 'tests/assets/integration_test_4/raw.fuzzer')
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
