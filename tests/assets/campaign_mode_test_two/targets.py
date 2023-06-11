# Targets server's accept_fuzz implementation for 
# campaign mode tests
from tests.assets.mock_targets import MockServer
import socket

class Target1(MockServer):
    
    def accept_fuzz(self):
        self.accept_connection()
        # accept initial connection
        while True:
            # receive hi
            self.receive_packet(2)
            # send hello, addr not required since tcp
            self.send_packet(bytearray('hello', 'utf-8'))
            self.receive_packet(4096)
            result = self.incoming_buffer.pop()
            if len(result) > 114 and len(result) < 120:
                # 15th iteration should cause a crash
                # write to file that monitor_target is reading
                with open('./tests/assets/campaign_mode_test_two/target_1/crash.log', 'w') as file:
                    file.write('crashed')
                print('[target 1] crash inducing input: {}'.format(result))
                print('[target 1] error: illegal memory access')
                if(len(result) == 118):
                    print('[target 1] error: will now crash')    
                    if self.communication_conn.type == socket.SOCK_STREAM:
                        self.listen_conn.close()
                    self.communication_conn.close()
                    return
            self.send_packet(bytearray('incorrect magic phrase, try again!', 'utf-8'))
            self.communication_conn = self.listen_conn.accept()[0]

class Target2(MockServer):
    
    def accept_fuzz(self):
        self.accept_connection()
        # accept initial connection
        while True:
            # receive hi
            self.receive_packet(2)
            # send hello, addr not required since tcp
            self.send_packet(bytearray('hello', 'utf-8'))
            self.receive_packet(4096)
            result = self.incoming_buffer.pop()
            if len(result) > 120 and len(result) < 160:

                with open('./tests/assets/campaign_mode_test_two/target_2/crash.log', 'w') as file:
                    file.write('crashed')
                print('[target 2] crash inducing input: {}'.format(result))
                print('[target 2] error: illegal memory access')
              
            self.send_packet(bytearray('incorrect magic phrase, try again!', 'utf-8'))
            self.communication_conn = self.listen_conn.accept()[0]

class Target3(MockServer):
    
    def accept_fuzz(self):
        self.accept_connection()
        # accept initial connection
        while True:
            # receive hi
            self.receive_packet(2)
            # send hello, addr not required since tcp
            self.send_packet(bytearray('hello', 'utf-8'))
            self.receive_packet(4096)
            result = self.incoming_buffer.pop()
            if len(result) > 80 and len(result) < 100:

                with open('./tests/assets/campaign_mode_test_two/target_3/crash.log', 'w') as file:
                    file.write('crashed')
                print('[target 3] crash inducing input: {}'.format(result))
                print('[target 3] error: illegal memory access')
            
            self.send_packet(bytearray('incorrect magic phrase, try again!', 'utf-8'))
            self.communication_conn = self.listen_conn.accept()[0]

