import errno
import socket
import traceback
from mutiny_classes.mutiny_exceptions import *
import logging
import sys

class ExceptionProcessor(object):

    logging.basicConfig(filename='debug2.log', level=logging.DEBUG)

    print('Comeing from exception', file=sys.stderr)

    def process_exception(self, exception):
        print(f'Inside function {str(exception)}', file=sys.stderr)

        if isinstance(exception, socket.error):
            print(f'Socket error: {exception.errno}', file=sys.stderr)
            if exception.errno == errno.ECONNREFUSED:
                # Default to assuming this means server is crashed so we're done
                print(f'Probably crashed, logging LogLastAndHalt: {exception.errno}', file=sys.stderr)
                raise LogLastAndHaltException("Connection refused: Assuming we crashed the server, logging previous run and halting")
                pass
            elif "timed out" in str(exception):
                raise AbortCurrentRunException("Server closed the connection")
            else:
                print(f'Unknown socket error: {exception.errno}', file=sys.stderr)
                if exception.errno:
                    raise AbortCurrentRunException("Unknown socket error: %d" % (exception.errno))
                else:
                    raise AbortCurrentRunException("Unknown socket error: %s" % (str(exception)))
        elif isinstance(exception, ConnectionClosedException):
            raise AbortCurrentRunException("Server closed connection: %s" % (str(exception)))
        elif exception.__class__ not in MessageProcessorExceptions.all:
            print(f'Unknown exception received - not Mutiny exception or socket error : {str(exception)}', file=sys.stderr)    
            # Default to logging a crash if we don't recognize the error
            print('Unknown exception received - not Mutiny exception or socket error, backtrace:')
            traceback.print_exc()
            raise LogCrashException(str(exception))
