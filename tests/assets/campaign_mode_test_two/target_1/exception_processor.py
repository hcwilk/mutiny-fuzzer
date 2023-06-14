import errno
import socket
import traceback
from mutiny_classes.mutiny_exceptions import *
import logging
import time
import sys

class ExceptionProcessor(object):


    def process_exception(self, exception, signal_main = None):

        if isinstance(exception, socket.error):
            if exception.errno == errno.ECONNREFUSED:
                # Default to assuming this means server is crashed so we're done

                # Sleep for a bit to give the server time to write the log file
                time.sleep(.1)

                # 'Signaling main' here is what allows the Campaign Mode UI to show and log the error right after it happens
                # There was no handling for if a target crashes before this, and now this helps for sure
                new_exception = LogLastAndHaltException("Connection refused: Assuming we crashed the server, logging previous run and halting")
                signal_main(LogLastAndHaltException(new_exception))


                # Don't need to raise it if we're signaling main

                # raise LogLastAndHaltException('Connection refused: Assuming we crashed the server, logging previous run and halting')
                pass
            elif "timed out" in str(exception):
                raise AbortCurrentRunException("Server closed the connection")
            else:
                if exception.errno:
                    raise AbortCurrentRunException("Unknown socket error: %d" % (exception.errno))
                else:
                    raise AbortCurrentRunException("Unknown socket error: %s" % (str(exception)))
        elif isinstance(exception, ConnectionClosedException):
            raise AbortCurrentRunException("Server closed connection: %s" % (str(exception)))
        elif exception.__class__ not in MessageProcessorExceptions.all:
            # Default to logging a crash if we don't recognize the error
            print('Unknown exception received - not Mutiny exception or socket error, backtrace:')
            traceback.print_exc()
            raise LogCrashException(str(exception))
