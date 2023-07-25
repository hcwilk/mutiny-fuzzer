import datetime
import errno
import importlib
import os
import signal
import socket
import queue
import subprocess
import sys
import time
import argparse
import ssl
import platform
import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
import scapy.all
from copy import deepcopy
from backend.proc_director import ProcDirector
from backend.fuzzer_types import Message, MessageCollection, Logger
from backend.packets import PROTO,IP
from mutiny_classes.mutiny_exceptions import *
from mutiny_classes.message_processor import MessageProcessorExtraParams, MessageProcessor
from mutiny_classes.exception_processor import ExceptionProcessor
from backend.fuzzer_data import FuzzerData
from backend.fuzzer_connection import FuzzerConnection
from backend.menu_functions import prompt, prompt_int, prompt_string, validate_number_range, print_warning, print_success, print_error

class Mutiny(object):

    def __init__(self, args):
        self.fuzzer_data = FuzzerData()
        # read data in from .fuzzer file
        self.fuzzer_file_path = args.prepped_fuzz
        print("Reading in fuzzer data from %s..." % (self.fuzzer_file_path))
        self.fuzzer_data.read_from_file(self.fuzzer_file_path)
        self.target_host = args.target_host
        self.sleep_time = args.sleep_time
        self.dump_raw = args.dump_raw # test single seed, dump to dumpraw
        self.quiet = args.quiet # dont log the outputs 
        self.testing = args.testing if args.testing else False
        self.server = args.server
        self.log_all = args.log_all if not self.quiet else False # kinda weird/redundant verbosity flags? 
        self.fuzzer_folder = os.path.abspath(os.path.dirname(self.fuzzer_file_path))
        self.output_data_folder_path = os.path.join("%s_%s" % (os.path.splitext(self.fuzzer_file_path)[0], "logs"), datetime.datetime.now().strftime("%Y-%m-%d,%H%M%S"))
        # retreive the last seed tried by mutiny
        self.min_run_number = 0
        self.max_run_number = -1
        self.seed_loop = []
        self.campaign_mode = args.campaign_mode if 'campaign_mode' in args else False
        if self.campaign_mode:
            self.campaign_event_queue = queue.SimpleQueue()
        self.connected = False

        

        self.channel = getattr(args, 'channel', None) # Add default value None if 'channel' doesn't exist
        self.server_ip = getattr(args, 'server_ip', None) # Add default value None if 'server_ip' doesn't exist
        self.server_port = getattr(args, 'server_port', None) # Add default value None if 'server_port' doesn't exist

        #Assign Lower/Upper bounds on test cases as needed
        if args.range:
            self.min_run_number, self.max_run_number = self._get_run_numbers_from_args(args.range)
        elif args.loop:
            self.seed_loop = validate_number_range(args.loop, flatten_list=True) 
        self.seed = self.min_run_number -1 if self.fuzzer_data.should_perform_test_run else self.min_run_number

        #TODO make it so logging message does not appear if reproducing (i.e. -r x-y cmdline arg is set)
        self.logger = None 
        if not self.quiet:
            print("Logging to %s" % (self.output_data_folder_path))
            self.logger = Logger(self.output_data_folder_path)

        if self.dump_raw:
            if not self.quiet:
                self.dump_dir = self.output_data_folder_path
            else:
                self.dump_dir = "dumpraw"
                try:
                    os.mkdir(self.dump_dir)
                except:
                    print_error("Unable to create dumpraw dir")
                    pass

        self.connection = None # connection to target

        # verify raw socket fuzzing is currently supported on user architecture
        if self.fuzzer_data.proto == 'L2raw':
            if platform.uname().system == 'Darwin':
                print_error('Raw socket fuzzing is currently unsupported on OSX')
                exit(-1)



    def import_custom_processors(self):
        ######## Processor Setup ################
        # The processor just acts as a container #
        # class that will import custom versions #
        # messageProcessor/exceptionProessor/    #
        # monitor, if they are found in the      #
        # process_dir specified in the .fuzzer   #
        # file generated by fuzz_prep.py         #
        ##########################################

        if self.fuzzer_data.processor_directory == "default":
            # Default to fuzzer file folder
            self.fuzzer_data.processor_directory = self.fuzzer_folder
        else:
            # Make sure fuzzer file path is prepended
            self.fuzzer_data.processor_directory = os.path.join(self.fuzzer_folder, self.fuzzer_data.processor_directory)

        #Create class director, which import/overrides processors as appropriate
        proc_director = ProcDirector(self.fuzzer_data.processor_directory)

        ########## Launch child monitor thread
            ### monitor.task = spawned thread
            ### monitor.queue = enqueued exceptions
        self.monitor = proc_director.start_monitor(self.server_ip, self.server_port, self.channel)
        self.exception_processor = proc_director.exception_processor()
        self.message_processor = proc_director.message_processor()


    def fuzz(self):
        '''
        Main fuzzing routine
        '''

        failure_count = 0
        loop_len = len(self.seed_loop) # if --loop
        is_paused = False

        # Sleeping only because of multiple stuff running
        # time.sleep(20)


        if self.server:
            self.connection = FuzzerConnection(self.fuzzer_data.proto, self.target_host, self.fuzzer_data.target_port, self.fuzzer_data.source_ip, self.fuzzer_data.source_port, self.server)
        
        

        while True:

            last_message_collection = deepcopy(self.fuzzer_data.message_collection)
            was_crash_detected = False
            if not is_paused and self.sleep_time > 0.0:
                print("\n** Sleeping for %.3f seconds **" % self.sleep_time)
                time.sleep(self.sleep_time)

            try:
                # Check for any exceptions from Monitor
                # Intentionally do this before and after a run in case we have back-to-back exceptions
                # (Example: Crash, then Pause, then Resume
                self._raise_next_monitor_event_if_any(is_paused)

                if is_paused:
                    # Busy wait, might want to do something more clever with Condition or Event later
                    time.sleep(0.5)
                    continue

                try:
                   # perform test run
                    if self.seed == self.min_run_number - 1:
                        print("\n\nPerforming test run without fuzzing...")
                        self._perform_run(test_run=True) 
                    else:
                        if self.dump_raw:
                            print("\n\nPerforming single raw dump case: %d" % self.dump_raw)
                            self.seed = self.dump_raw
                        elif loop_len:
                            print("\n\nFuzzing with seed %d" % (self.seed_loop[self.seed % loop_len]))
                            self.seed = self.seed = self.seed_loop[self.seed % loop_len]
                        else:
                            print("\n\nFuzzing with seed %d" % (self.seed))
                            self._perform_run()
                    #if --quiet, (logger==None) => AttributeError
                    if self.log_all:
                        try:
                            self.logger.output_log(self.seed, self.fuzzer_data.message_collection, "log_all ")
                        except AttributeError:
                            pass 
                except Exception as e:
                    if self.log_all:
                        try:
                            self.logger.output_log(self.seed, self.fuzzer_data.message_collection, "log_all ")
                        except AttributeError:
                            pass

                    if e.__class__ in MessageProcessorExceptions.all:
                        # If it's a MessageProcessorException, assume the MP raised it during the run
                        # Otherwise, let the MP know about the exception
                        raise e
                    else:
                        # passing  without parenthesis means you're passing the function, not calling it. Good to know
                        self.exception_processor.process_exception(e, self.monitor.signal_crash_detected_on_main)
                        # Will not get here if processException raises another exception
                        print_warning("Exception ignored: %s" % (repr(e)))

                # Check for any exceptions from Monitor
                # Intentionally do this before and after a run in case we have back-to-back exceptions
                # (Example: Crash, then Pause, then Resume
                self._raise_next_monitor_event_if_any(is_paused)
            except PauseFuzzingException as e:
                print_warning('Mutiny received a pause exception, pausing until monitor sends a resume...')
                is_paused = True

            except ResumeFuzzingException as e:
                if is_paused:
                    print_success('Mutiny received a resume exception, continuing to run.')
                    is_paused = False
                else:
                    print_warning('Mutiny received a resume exception but wasn\'t paused, ignoring and continuing.')

            except LogCrashException as e:


                if failure_count == 0:
                    try:
                        print_success("Mutiny detected a crash")
                        self.logger.output_log(self.seed, self.fuzzer_data.message_collection, str(e))
                    except AttributeError:  
                        pass   

                if self.log_all:
                    try:
                        self.logger.output_log(self.seed, self.fuzzer_data.message_collection, "log_all ")
                    except AttributeError:
                        pass

                failure_count = failure_count + 1
                was_crash_detected = True

            except TargetLogFileModifiedException as e:

                try:
                    self.logger.output_log(self.seed, self.fuzzer_data.message_collection, str(e))
                except AttributeError:
                    pass

            except MonitorRecalibrationException as e:

                try:
                    self.logger.output_log(self.seed, self.fuzzer_data.message_collection, str(e))
                except AttributeError:
                    pass


                # add more functionality ehre

            except AbortCurrentRunException as e:
                # Give up on the run early, but continue to the next test
                # This means the run didn't produce anything meaningful according to the processor
                print_warning("Run aborted: %s" % (str(e)))

            except RetryCurrentRunException as e:
                # Same as AbortCurrentRun but retry the current test rather than skipping to next
                print_warning("Retrying current run: %s" % (str(e)))
                # Slightly sketchy - a continue *should* just go to the top of the while without changing i
                continue

            except LogAndHaltException as e:
                if self.logger:
                    self.logger.output_log(self.seed, self.fuzzer_data.message_collection, str(e))
                    print_warning("Received LogAndHaltException, logging and halting")
                else:
                    print_warning("Received LogAndHaltException, halting but not logging (quiet mode)")
                if self.testing: return
                else: exit()

            except LogLastAndHaltException as e:

                if self.logger:
                    if self.seed > self.min_run_number:
                        print_warning("Received LogLastAndHaltException, logging last run and halting")
                        if self.min_run_number == self.max_run_number:
                            #in case only 1 case is run
                            self.logger.output_last_log(self.seed, last_message_collection, str(e))
                            print("Logged case %d" % self.seed)
                        else:
                            self.logger.output_last_log(self.seed-1, last_message_collection, str(e))
                    else:
                        print_warning("Received LogLastAndHaltException, skipping logging (due to last run being a test run) and halting")
                else:
                    print_warning("Received LogLastAndHaltException, halting but not logging (quiet mode)")
                if self.testing: return
                else:

                    exit()

            except HaltException as e:
                print_warning("Received HaltException, halting the fuzzing campaign")
                if self.testing: 
                    return
                else: 
                    exit()

            if was_crash_detected:
                if failure_count < self.fuzzer_data.failure_threshold:
                    print_error("Failure %d of %d allowed for seed %d" % (failure_count, self.fuzzer_data.failure_threshold, self.seed))
                    print("The test run didn't complete, continuing after %d seconds..." % (self.fuzzer_data.failure_timeout))
                    time.sleep(self.fuzzer_data.failure_timeout)
                else:
                    print_warning("Failed %d times, moving to next test." % (failure_count))
                    failure_count = 0
                    self.seed += 1
            else:
                self.seed += 1

            # Stop if we have a maximum and have hit it
            if (self.max_run_number >= 0 and self.seed > self.max_run_number) or self.dump_raw:
                print_success('Completed specified fuzzing range, gracefully shutting down...')
                if self.testing: return
                else: exit()


    def _perform_run(self, test_run = False):
        '''
        Perform a fuzz run.  

        params:
            test_run(bool): whether a test run should be performed
        '''
        # Before doing anything, set up logger
        # Otherwise, if connection is refused, we'll log last, but it will be wrong
        if self.logger:
            self.logger.reset_for_new_run()

        # Call messageprocessor preconnect callback if it exists
        try:
            self.message_processor.pre_connect(self.seed, self.target_host, self.fuzzer_data.target_port) 
        except AttributeError:
            pass

        # create a new connection to the target process ( we only want to do this if we're a client. Doesn't make sense to bind to a random port if we're funcitoning as a server)
        if not self.server:
            self.connection = FuzzerConnection(self.fuzzer_data.proto, self.target_host, self.fuzzer_data.target_port, self.fuzzer_data.source_ip, self.fuzzer_data.source_port, self.server,None)
        

        message_num = 0   
        for message_num in range(0, len(self.fuzzer_data.message_collection.messages)):
            message = self.fuzzer_data.message_collection.messages[message_num]

            # Go ahead and revert any fuzzing or messageprocessor changes before proceeding
            message.reset_altered_message()
            if message.is_outbound():
                self._send_fuzz_session_message(message_num, message, test_run) if not self.server else self._receive_fuzz_session_message(message_num, message)
            else: 
                self._receive_fuzz_session_message(message_num, message) if not self.server else self._send_fuzz_session_message(message_num, message, test_run)

            if self.logger != None:  
                self.logger.set_highest_message_number(message_num)
            message_num += 1

        if not self.server:
            self.connection.close()

    def _receive_fuzz_session_message(self, message_num, message):
        '''
        perform fuzzing subroutine for an inbound message:
        
        1. retrieve message we would expect for this message_num
        2. receive data from connection socket
        3. notify message_processor of the reception of a new message
        4. log information about message if applicable

        params:
            - message_num(int): index of message in self.message_collection we are examining
            - message(bytearray): message we would expect
        '''
        message_byte_array = message.get_altered_message()
        data = self.connection.receive_packet(len(message_byte_array), self.fuzzer_data.receive_timeout)
        
        self.message_processor.post_receive_process(data, MessageProcessorExtraParams(message_num, -1, False, [message_byte_array], [data]))



        # if self.debug:
        print("\tReceived: %s" % (data))
    
        if data == message_byte_array:
            print("\tReceived expected response")
        if self.logger: 
            self.logger.set_received_message_data(message_num, data)
        if self.dump_raw:
            loc = os.path.join(self.dump_dir, "%d-inbound-seed-%d"%(message_num, self.dump_raw))
            with open(loc,"wb") as f:
                f.write(repr(str(data))[1:-1])

    def _send_fuzz_session_message(self, message_num, message, test_run):
        '''
        sends subcomponents to the server during a fuzzing session, using
        subcomponent.is_fuzzed to determine if a given subcomponent should be fuzzed

        params
            message_num(int): index of message to send in message collection
            message(Message): message object to send
            test_run(bool): whether or not we are in a test run, if we are, dont fuzz
        '''
        # Primarily used for deciding how to handle preFuzz/preSend callbacks
        
        message_has_subcomponents = len(message.subcomponents) > 1

        # Get original subcomponents for outbound callback only once
        original_subcomponents = [subcomponent.get_original_byte_array() for subcomponent in message.subcomponents]

        if message_has_subcomponents:
            # For message with subcomponents, call prefuzz on fuzzed subcomponents
            for subcomponent_num in range(0, len(message.subcomponents)):
                subcomponent = message.subcomponents[subcomponent_num] 
                # Note: we WANT to fetch subcomponents every time on purpose
                # This way, if user alters subcomponent[0], it's reflected when
                # we call the function for subcomponent[1], etc
                actual_subcomponents = [subcomponent.get_altered_byte_array() for subcomponent in message.subcomponents]
                pre_fuzz = self.message_processor.pre_fuzz_subcomponent_process(subcomponent.get_altered_byte_array(), MessageProcessorExtraParams(message_num, subcomponent_num, subcomponent.is_fuzzed, original_subcomponents, actual_subcomponents))
                subcomponent.set_altered_byte_array(pre_fuzz)
        else:
            # If no subcomponents, call prefuzz on ENTIRE message
            actual_subcomponents = [subcomponent.get_altered_byte_array() for subcomponent in message.subcomponents]
            pre_fuzz = self.message_processor.pre_fuzz_process(actual_subcomponents[0], MessageProcessorExtraParams(message_num, -1, message.is_fuzzed, original_subcomponents, actual_subcomponents))
            message.subcomponents[0].set_altered_byte_array(pre_fuzz)

        # dont fuzz for test run 
        if not test_run:
            # Now run the fuzzer for each fuzzed subcomponent
            self._fuzz_subcomponents(message)


        # Fuzzing has now been done if this message is fuzzed
        # Always call preSend() regardless for subcomponents if there are any
        if message_has_subcomponents:
            for subcomponent_num in range(0, len(message.subcomponents)):
                subcomponent = message.subcomponents[subcomponent_num] 
                # See preFuzz above - we ALWAYS regather this to catch any updates between
                # callbacks from the user
                actual_subcomponents = [subcomponent.get_altered_byte_array() for subcomponent in message.subcomponents]
                pre_send = self.message_processor.pre_send_subcomponent_process(subcomponent.get_altered_byte_array(), MessageProcessorExtraParams(message_num, subcomponent_num, subcomponent.is_fuzzed, original_subcomponents, actual_subcomponents))
                subcomponent.set_altered_byte_array(pre_send)
                
        # Always let the user make any final modifications pre-send, fuzzed or not
        actual_subcomponents = [subcomponent.get_altered_byte_array() for subcomponent in message.subcomponents]
        byte_array_to_send = self.message_processor.pre_send_process(message.get_altered_message(), MessageProcessorExtraParams(message_num, -1, message.is_fuzzed, original_subcomponents, actual_subcomponents))
        if self.dump_raw:
            loc = os.path.join(self.dump_dir,"%d-outbound-seed-%d"%(message_num, self.dump_raw))
            if message.is_fuzzed:
                loc += "-fuzzed"
            with open(loc, "wb") as f:
                f.write(repr(str(byte_array_to_send))[1:-1])
        self.connection.send_packet(byte_array_to_send, self.fuzzer_data.receive_timeout)

        if self.debug:
            print("\tSent: %s" % (byte_array_to_send))
            print("\tRaw Bytes: %s" % (Message.serialize_byte_array(byte_array_to_send)))



    def _fuzz_subcomponents(self, message):
        '''
        iterates through each subcomponent in a message and uses radamsa to generate fuzzed
        versions of each subcomponent if its .isFuzzed is set to True
        '''
        for subcomponent in message.subcomponents:
            if subcomponent.is_fuzzed:
                radamsa = subprocess.Popen([self.radamsa, "--seed", str(self.seed)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                byte_array = subcomponent.get_altered_byte_array()
                (fuzzed_byte_array, error_output) = radamsa.communicate(input=byte_array)
                fuzzed_byte_array = bytearray(fuzzed_byte_array)
                subcomponent.set_altered_byte_array(fuzzed_byte_array)


    def _raise_next_monitor_event_if_any(self, is_paused):
        # Check the monitor queue for exceptions generated during run
        if not self.monitor.queue.empty():
            print_warning('Monitor event detected')
            exception = self.monitor.queue.get()
            if self.campaign_mode:
                self.campaign_event_queue.put(exception)

            if is_paused:
                if isinstance(exception, PauseFuzzingException):
                    # Duplicate pauses are fine, a no-op though
                    pass
                elif not isinstance(exception, ResumeFuzzingException):
                    # Any other exception besides resume after pause makes no sense
                    print_warning(f'Received exception while Mutiny was paused, can\'t handle properly:')
                    print(repr(exception))
                    print_warning('Exception will be ignored and discarded.')
                    return
            raise exception

    def _get_run_numbers_from_args(self, str_args):
        '''
        Set MIN_RUN_NUMBER and MAX_RUN_NUMBER when provided
        by the user below
        '''
        if "-" in str_args:
            test_numbers = str_args.split("-")
            if len(test_numbers) == 2:
                if len(test_numbers[1]): #e.g. str_args="1-50"
                    # cant have min > max
                    if (int(test_numbers[0]) > int(test_numbers[1])):
                        exit("Invalid test range given: %s" % str_args)
                    return (int(test_numbers[0]), int(test_numbers[1]))
                else:                   #e.g. str_args="3-" (equiv. of --skip-to)
                    return (int(test_numbers[0]),-1)
            else: #e.g. str_args="1-2-3-5.." 
                exit("Invalid test range given: %s" % str_args)
        else:
            # If they pass a non-int, allow this to bomb out
            return (int(str_args),int(str_args)) 


