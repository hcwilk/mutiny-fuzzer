#!/usr/bin/env python3
#------------------------------------------------------------------
# November 2014, created within ASIG
# Author James Spadaro (jaspadar)
# Co-Author Lilith Wyatt (liwyatt)
#------------------------------------------------------------------
# Copyright (c) 2014-2023 by Cisco Systems, Inc.
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
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS 'AS IS' AND ANY
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
# Creates and deploys a CampaignManager object
#
# The CampaignManager object is responsible for adding the following
# capabilities to provide persistent fuzzing campaign management
#
# - ability to spawn multiple mutiny objects in child threads, optionally in network namespaces
# - ability to target multiple hosts/endpoints
# - coordination of target monitoring across fuzzers
# - exposure of a curses-based UI that allows the user to view campaign statistics, as well
#   as send pause/resume/halt commands to all threads via the UI
#------------------------------------------------------------------
import os
import sys
import argparse
import signal
import datetime
import curses
import yaml
from backend.mutiny import Mutiny
from backend.menu_functions import print_warning, print_error, print_success
from mutiny_classes.mutiny_exceptions import *
import time
import logging
import threading
import json




class CampaignManager(object):
    class CampaignMode:
        Vanilla = 'Single Fuzzer Host'
        SockDistributed =  'Distributed over Sockets'
        NameSpaceDistributed = 'Distributed over Namespaces'
        UnixSocketDistributed = 'Distributed over Unix Sockets'
        VanillaRR = 'Round Robin Single Fuzzer Host'
        SocketDistributedRR = 'Round Robin Distributed over Sockets'
        NameSpaceDistributedRR = 'Round Robin Distributed over Namespaces'
        UnixSocketDistributedRR = 'Round Robin Distributed over Unix Sockets'

    class CampaignStatus:
        Initializing = 'initializing'
        Paused = 'paused'
        Running = 'running'
        ShuttingDown = 'shutting down'

    class TextColors:
        White  = 1
        Green = 2
        Yellow = 3
        Red =  4
        Cyan = 5
        Magenta = 6
        Inverted = 7

    def __init__(self, config_file, log_pad_max_lines, seeds, testing=False):

        # determine configuration of campaign
        self.process_config(config_file)
        

        self.fuzzers = {} # key=mutiny object, val=thread
        self.execs = 0 # number of fuzz cases tried 
        self.crashes = 0 
        self.run_time = 0
        self.start_time = time.time()
        self.status = self.CampaignStatus.Initializing
        self.status_bar = ''
        self.screen = None # curses screen
        self.screen_height = 0
        self.screen_width = 0
        self.log_pad = None # scrollable curses pad for displaying logs/events
        self.log_pad_max_lines = log_pad_max_lines
        self.seeds = seeds
        self.log_pad_view_y = 0 # for tracking cursor when scrolling log pad
        self.log_pad_write_y = 0 # for tracking cursor when writing to log pad
        self.log_pad_write_x = 0 # for tracking cursor when writing to log pad
        self.determine_campaign_mode() # set campaign mode

        # check for dependencies
        if not os.path.exists(self.radamsa):
            exit('Could not find radamsa in %s... did you build it?' % config['radamsa'])


    def determine_campaign_mode(self):
        '''
        based upon the campaign mode configuration values
        parsed by self.process_config, sets the mode for display
        in the curses status bar
        '''
        if self.distributed:
            if self.distributed_type == 'net-sockets':
                self.mode = self.CampaignMode.SocketDistributedRR if self.round_robin else self.CampaignMode.SocketDistributed
            elif self.distributed_type == 'namespaces':
                self.mode = self.CampaignMode.NameSpaceDistributedRR if self.round_robin else self.CampaignMode.NameSpaceDistributed
            elif self.distributed_type == 'unix-sockets':
                self.mode = self.CampaignMode.UnixSocketDistributedRR if self.round_robin else self.CampaignMode.UnixSocketDistributed
            else:
                print_error('Unrecognized distributed fuzzing type, valid types: [\'namespaces\', \'unix-sockets\', \'net-sockets\']')
                exit(-1)
        else:
            self.mode = self.CampaignMode.VanillaRR if self.round_robin else self.CampaignMode.Vanilla

    def process_config(self, config_file):
        '''
        takes a configuration file and saves the
        relevant variables to the campaign manager instance
        using pyyaml to process the config
        '''
        config = yaml.safe_load(config_file)
        self.radamsa = config['radamsa']
        self.testing = config['testing']
        self.workers = config['workers']
        self.debug = config['debug']
        self.server_mode = config['server_mode']
        self.round_robin = config['round_robin']
        if self.round_robin:
            self.round_robin_cases = config['round_robin_cases']
        self.distributed = config['distributed']
        if self.distributed:
            self.distributed_type = config['distributed_type']
        

    def start_campaign(self, stdscr):

        '''
        begins the fuzzing campaign by starting threads and initializing the
        curses window

        should be called using curses.wrapper(campaign_manager.start_campaign)
        to take care of setting up terminal for curses

        params:
            - stdscr(curses window): window object representing the entire
            terminal screen
        '''
        self.screen = stdscr
        # initialize pad, create title, subtitle, and help menu
        self.setup_curses()


        for i, (fuzz_file, target) in enumerate(self.workers):
            self.block_print()
            # initialize a child mutiny thread for each worker
            fuzzer_args = argparse.Namespace(prepped_fuzz = fuzz_file, target_host = target, sleep_time = 0, range = None, loop = None, dump_raw = None, quiet = False, log_all = False, server = self.server_mode, testing = False, campaign_mode = True, channel=str(i), server_ip = '127.0.0.1', server_port = 9876)
            fuzzer = Mutiny(fuzzer_args)
            if seeds and str(i) in seeds:
                fuzzer.seed = seeds[str(i)]
            fuzzer.radamsa = self.radamsa
            fuzzer.debug = self.debug
            fuzzer.import_custom_processors()
            thread = threading.Thread(target=fuzzer.fuzz)
            self.fuzzers[fuzzer] = thread
            thread.start()
            timestamp = datetime.datetime.now()
            timestamp = timestamp.strftime("%d-%m-%y %H:%M:%S")
            # write timestamp
            self.log_pad.attron(curses.color_pair(self.TextColors.Cyan))
            self.log_pad.addstr(self.log_pad_write_y, 0, timestamp)
            self.log_pad.attron(curses.color_pair(self.TextColors.White))
            self.log_pad.addstr(':')
            # write fuzzer file to identify worker
            self.log_pad.attron(curses.A_BOLD)
            self.log_pad.addstr('[{}] '.format(fuzz_file.split('/')[-1]))
            self.log_pad.attroff(curses.A_BOLD)
            self.log_pad.attron(curses.color_pair(self.TextColors.Yellow))
            self.log_pad.addstr(f'Fuzzer {i} Initialized on seed {fuzzer.seed}!')
            self.log_pad_write_y += 1
        self.status = self.CampaignStatus.Running
        quit_requested = False

        # poll for user input in seperate thread
        while not quit_requested:
            try:
                quit_requested = self.poll_user_input()
                self.refresh_display()
                self.update_campaign_information()
                self.refresh_display()
            except curses.error as e:
                print('terminal too small to display UI, please resize')
        self.graceful_shutdown()

    def setup_curses(self):
        '''
        initialize curses environment
        '''
        self.screen_height, self.screen_width = self.screen.getmaxyx()
        # setup colors 
        self.setup_curses_colors()
        # TODO: make assertions about min window sizes 
        self.render_title(self.screen_width, self.screen_height)
     
        # render status bar
        self.render_status_window()


           # Render help window on rightmost quarter of screen
        self.render_help_window()

                # create scrollable pad for event output
        log_pad = self.create_log_pad()
        self.screen.nodelay(True) # make getkey nonblocking
        curses.curs_set(0) # hide cursor
        self.refresh_display() # start display
        self.screen.keypad(True)

    
    def setup_curses_colors(self):
        '''
        initializes colors and defines color pair
        to be used with curses
        '''
        # setup colors
        curses.start_color()
        curses.init_pair(self.TextColors.White, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(self.TextColors.Cyan, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(self.TextColors.Red, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(self.TextColors.Green, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(self.TextColors.Magenta, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(self.TextColors.Yellow, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(self.TextColors.Inverted, curses.COLOR_BLACK, curses.COLOR_WHITE)

    def render_title(self, width, height):
        '''
        renders the title and subtitle on the first two lines
        in the center of the screen
        '''
        # Rendering title
        
      
        title = 'The Mutiny Fuzzing Framework' 
        start_x_title = int((self.screen_width // 2) - (len(title) // 2) - len(title) % 2)
        self.screen.attron(curses.color_pair(self.TextColors.Green))
        self.screen.attron(curses.A_BOLD)
        self.screen.addstr(0, start_x_title, title)
        self.screen.attron(curses.color_pair(self.TextColors.White))
        self.screen.attroff(curses.A_BOLD)

        # Rendering subtitle
        subtitle = 'Campaign Mode'
        start_x_subtitle = int((self.screen_width // 2) - (len(subtitle) // 2) - len(subtitle) % 2)
        self.screen.attron(curses.color_pair(self.TextColors.Red))
        self.screen.addstr(1, start_x_subtitle, subtitle)
        self.screen.attron(curses.color_pair(self.TextColors.White))
        self.screen.refresh()

    def render_status_window(self):
        '''
        create a window for the status bar and set colors to inverted
        '''
        self.status_win = curses.newwin(1, self.screen_width, self.screen_height - 1, 0)
        self.status_win.attron(curses.color_pair(self.TextColors.Inverted))

    def render_help_window(self):
        '''
        renders the help window at the top of the 
        screen, providing information about valid commands
        '''
        # This block is for large screens sizes
        try:
            self.help_y= 6
            begin_x = 4
            begin_y = 2
            help_height = self.screen_height - 4
            help_width = self.screen_width - 8
            self.help_win = curses.newwin(help_height, help_width, begin_y, begin_x)
            self.help_win.attron(curses.A_BOLD)
            self.help_win.attron(curses.color_pair(self.TextColors.Green))
            command_title = 'Key Commands'
            command_start_x = (help_width // 2) - (len(command_title) // 2)
            self.help_win.addstr(0, command_start_x, command_title)
            self.help_win.attron(curses.color_pair(self.TextColors.White))
            self.help_win.addstr(1, 0, '-' * help_width)
            x = 2
            self.help_win.attron(curses.A_BOLD)
            self.help_win.addch(2, x, 'p')
            self.help_win.attroff(curses.A_BOLD)
            self.help_win.addstr(2, x+2, ': pause campaign')
            x += 20
            self.help_win.attron(curses.A_BOLD)
            self.help_win.addch(2, x, 'r')
            self.help_win.attroff(curses.A_BOLD)
            self.help_win.addstr(2, x+2, ': resume campaign')
            x += 20
            self.help_win.attron(curses.A_BOLD)
            self.help_win.addch(2, x, 's')
            self.help_win.attroff(curses.A_BOLD)
            self.help_win.addstr(2, x+2, ': save campaign state to disk and quit')
            x += 42
            self.help_win.attron(curses.A_BOLD)
            self.help_win.addch(2, x, 'q')
            self.help_win.attroff(curses.A_BOLD)
            self.help_win.addstr(2, x+2, ': quit campaign')
            x += 20
            self.help_win.attron(curses.A_BOLD)
            self.help_win.addstr(2, x, '{}/{}'.format(chr(8593), chr(8595)))
            self.help_win.attroff(curses.A_BOLD)
            self.help_win.addstr(2, x+2, ': navigate campaign logs')
            self.help_win.refresh()
        except:
            # This block is for small screens sizes
            self.help_y = 14
            begin_x = 4
            begin_y = 2
            help_height = self.screen_height - 4
            help_width = self.screen_width - 8
            self.help_win = curses.newwin(help_height, help_width, begin_y, begin_x)
            self.help_win.attron(curses.A_BOLD)
            self.help_win.attron(curses.color_pair(self.TextColors.Green))
            command_title = 'Key Commands'
            command_start_x = (help_width // 2) - (len(command_title) // 2)
            self.help_win.addstr(0, command_start_x, command_title)
            self.help_win.attron(curses.color_pair(self.TextColors.White))
            self.help_win.addstr(1, 0, '-' * help_width)
            y = 2
            self.help_win.attron(curses.A_BOLD)
            self.help_win.addch(y, 0, 'p')
            self.help_win.attroff(curses.A_BOLD)
            self.help_win.addstr(y, 1, ': pause campaign')
            y += 2
            self.help_win.attron(curses.A_BOLD)
            self.help_win.addch(y, 0, 'r')
            self.help_win.attroff(curses.A_BOLD)
            self.help_win.addstr(y, 1, ': resume campaign')
            y += 2
            self.help_win.attron(curses.A_BOLD)
            self.help_win.addch(y, 0, 's')
            self.help_win.attroff(curses.A_BOLD)
            self.help_win.addstr(y, 1, ': save campaign state to disk and quit')
            y += 2
            self.help_win.attron(curses.A_BOLD)
            self.help_win.addch(y, 0, 'q')
            self.help_win.attroff(curses.A_BOLD)
            self.help_win.addstr(y, 1, ': quit campaign')
            y += 2
            self.help_win.attron(curses.A_BOLD)
            self.help_win.addstr(y, 0, '{}/{}'.format(chr(8593), chr(8595)))
            self.help_win.attroff(curses.A_BOLD)
            self.help_win.addstr(y, 3, ': navigate campaign logs')
            self.help_win.refresh()


    def create_log_pad(self):
        '''
        creates the scrollable log pad for displaying events received
        from monitors 
        '''
        # create log pad 
        pad_width = self.screen_width
        self.log_pad = curses.newpad(self.log_pad_max_lines, pad_width)
        # position on screen it should be displayed
        top_left_y = self.help_y
        top_left_x = 0
        bottom_right_y = self.screen_height - 3
        bottom_right_x = pad_width
        self.log_pad_pos = [top_left_y, top_left_x, bottom_right_y, bottom_right_x]
        # allow pad to be scrolled
        self.log_pad.scrollok(True)
        self.log_pad.keypad(True)

    def poll_user_input(self):
        '''
        takes curses user input and dispatches
        appropriate functionality
        
        returns:
            bool: true if a quit was requested, else false
        '''
        quit_requested = False
        try:
            cmd = self.screen.getch()
        except curses.error:
            return quit_requested
        if cmd == curses.KEY_RESIZE:
            # # get the new screen size
            h, w = self.screen.getmaxyx()

            self.screen_height = h
            self.screen_width = w

            curses.resizeterm(h, w)

            self.screen.clear()
            self.screen.refresh() 

            # re-render the title and subtitle
            self.render_title(w,h)
            
            # resize and reposition the status window
            self.status_win.resize(1, w)
            self.status_win.mvwin(h - 1, 0)
            self.status_win.refresh()

            # Get the current size of the log pad
            pad_height, pad_width = self.log_pad.getmaxyx()

            # Update the size and position of the log pad
            top_left_y = self.help_y
            top_left_x = 0
            bottom_right_y = h - 3
            bottom_right_x = pad_width
            self.log_pad_pos = [top_left_y, top_left_x, bottom_right_y, bottom_right_x]

            # Calculate the first line of the log pad that should be displayed
            pad_start_line = max(0, pad_height - (bottom_right_y - top_left_y))

            # Display the appropriate part of the log pad in the terminal window
            self.log_pad.resize(self.log_pad_max_lines,w)
            self.log_pad.refresh(pad_start_line, 0, top_left_y, top_left_x, h-1, w-1)

            self.render_help_window()



        elif cmd == ord('q'):
            quit_requested = True
        elif cmd == ord('s'):
            quit_requested = True
            self.save_and_quit()
        elif cmd == ord('p'):
            self.pause()
        elif cmd == ord('r'):
            self.resume()
        elif cmd == curses.KEY_DOWN:
            self.log_pad.scroll(1)
            self.log_pad_view_y += 1
        elif cmd == curses.KEY_UP:
            self.log_pad.scroll(-1)
            self.log_pad_view_y -= 1
        return quit_requested

    def update_campaign_information(self):
        '''
        polls mutiny log files for new events and aggregates 
        them into a single log file as well as displays important
        events on the UI
        '''
        execs = 0
        for fuzzer in self.fuzzers:
            while not fuzzer.campaign_event_queue.empty():
                exception = fuzzer.campaign_event_queue.get()
                self.parse_event(exception, fuzzer.fuzzer_file_path, fuzzer.output_data_folder_path)
            # update statistics
            execs += fuzzer.seed



        # Render Status bar
        elapsed_time = datetime.timedelta(seconds=round(time.time() - self.start_time))
        new_status_bar = 'workers: {} | fuzzed executions: {} | crashes found: {} | time elapsed: {} | mode: {} | status: {}'.format(len(self.workers), execs, self.crashes, elapsed_time, self.mode, self.status)

        # only update when theres something new to display
        if self.status_bar != new_status_bar:
            self.status_win.erase()
            self.status_win.addstr(0, 0, new_status_bar)
            self.status_win.addstr(" " * (self.screen_width - len(new_status_bar) -1))
            self.status_win.refresh()
            self.status_bar = new_status_bar

    def parse_event(self, exception, fuzz_file, log_file):

        '''
        parses mutiny event and displays 
        relevant information to self.log_pad

        params:
            - exception(MutinyException): exception passed to campaign manager
            from a mutiny instance
            - fuzz_file(string): name of fuzzer file used by the worker that raised
            - log_file(string): name of fuzzer log file 
            the exception
        '''

        timestamp = datetime.datetime.now()
        timestamp = timestamp.strftime("%d-%m-%y %H:%M:%S")
        # write timestamp
        self.log_pad.attron(curses.color_pair(self.TextColors.Cyan))
        self.log_pad.addstr(self.log_pad_write_y, self.log_pad_write_x, timestamp)
        self.log_pad.attron(curses.color_pair(self.TextColors.White))
        self.log_pad.addstr(':')
        # write fuzzer file to identify worker
        self.log_pad.attron(curses.A_BOLD)
        self.log_pad.addstr('[{}] '.format(fuzz_file.split('/')[-1]))
        self.log_pad.attroff(curses.A_BOLD)

        # This shouldn't be anywhere in the 'help.txt' file now
        if isinstance(exception, LogCrashException):
            print('Campaign Mode Received Log Crash Exception', file=sys.stderr)
            self.crashes += 1
            self.log_pad.attron(curses.color_pair(self.TextColors.Green))
            exception = str(exception) + ' see {} for details'.format(log_file)

        # Probably need to include the regex stuff here as well
        if isinstance(exception, TargetLogFileModifiedException):
            print('Campaign Mode Received Target Log File Modified Exception', file=sys.stderr)
            self.crashes += 1
            self.log_pad.attron(curses.color_pair(self.TextColors.Green))
            exception = str(exception) + ' see {} for details'.format(log_file)
        if isinstance(exception, ConnectionClosedException):
            self.log_pad.attron(curses.color_pair(self.TextColors.Red))

        # Now this hits whenver a connection refused error comes in
        if isinstance(exception, HaltException) or \
                isinstance(exception, LogLastAndHaltException) or \
                isinstance(exception, LogAndHaltException):
            print('Campaign mode got halt after connection refused', file=sys.stderr)
            
            self.log_pad.attron(curses.color_pair(self.TextColors.Green))
        self.log_pad.addstr(str(exception))
        self.log_pad.attron(curses.color_pair(self.TextColors.White))
        self.log_pad_write_y, _ = self.log_pad.getyx()
        self.log_pad_write_y += 1
        self.log_pad_view_y = self.log_pad_write_y - self.screen_height + 4
        self.log_pad_write_x = 0


    def refresh_display(self):
        '''
        refreshes the log pad 
        '''
        # log_pad_pos has the following elements:
        # [upperleft y, upperleft x, lowerright y, lowerright x]
        self.log_pad.refresh(self.log_pad_view_y, 0, \
                self.log_pad_pos[0], self.log_pad_pos[1], \
                self.log_pad_pos[2], self.log_pad_pos[3])

    def pause(self):
        '''
        sends a pause signal to all of the fuzzers
        '''
        self.status = self.CampaignStatus.Paused
        for fuzzer in self.fuzzers:
            exception = PauseFuzzingException('User Requested Pause')

            fuzzer.monitor.signal_crash_detected_on_main(exception)

    def resume(self):
        '''
        sends a resume signal to all of the fuzzers
        '''
        self.status = self.CampaignStatus.Running
        for fuzzer in self.fuzzers:
            exception = ResumeFuzzingException('User Requested Resume')
            fuzzer.monitor.signal_crash_detected_on_main(exception)

    def save_and_quit(self):
        '''
        saves the state of all fuzzers to disk so that
        a future campaign can pick off where this one ended
        '''
        seeds = {}
        for i, fuzzer in enumerate(self.fuzzers):
            seeds[i] = fuzzer.seed

        with open('fuzzer_seeds.json', 'w') as f:
            json.dump(seeds, f)

        self.graceful_shutdown()


    def graceful_shutdown(self):
        '''
        destroys curses window and signals to all threads to stop execution
        '''
        # signals all threads
        for fuzzer in self.fuzzers:
            # unpause if paused since mutiny will ignore other exceptions while paused
            if self.status == self.CampaignStatus.Paused:
                exception = ResumeFuzzingException('User Requested Shutdown')
                fuzzer.monitor.signal_crash_detected_on_main(exception)
            exception = HaltException('Shutting Down')
            fuzzer.monitor.signal_crash_detected_on_main(exception)
        self.status = self.CampaignStatus.ShuttingDown
        # join all threads
        for fuzzer in self.fuzzers:
            self.fuzzers[fuzzer].join()
        exit()
    

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

if __name__ == '__main__':
    # Just to debug incase you need somewhere to dump output
    logging.basicConfig(filename='logfile.log', level=logging.DEBUG)
    desc =  '======== The Mutiny Fuzzing Framework ==========' 
    epi = '==' * 24 + '\n'
    parser = argparse.ArgumentParser(prog='./campaign_mode.py', description=desc,epilog=epi)
    parser.add_argument('config_file', help='path to campaign_conf.yml file')
    parser.add_argument('-l', '--lines', help='number of maximum lines in event output', default=1000)
    parser.add_argument('-r', '--resume', help='path to file from previous run to resume campaign', default=None)

    # Usage case
    if len(sys.argv) < 2:
        sys.argv.append('-h')

    seeds = None

    # process resume file (if user specified)
    args = parser.parse_args()
    if args.resume:
        with open(args.resume, 'r') as resume_file:
            seeds = json.load(resume_file)

    # process configuration file
    with open(args.config_file, 'r') as config_file:
        manager = CampaignManager(config_file, args.lines, seeds) 
    
    # begin campaign with curses interface
    curses.wrapper(manager.start_campaign)
