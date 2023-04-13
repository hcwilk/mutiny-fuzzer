from tests.assets.mock_target import MockClient
import socket
import time


class Target3(MockClient):

    def connect_fuzz(self):
        #TODO: make message_processor.preconnect available, assert its being called
        # accept initial connection (commented out because it already should do this)
        # self.accept_connection()
        print('heres where im binding to ',self.client_addr, ' on port ', str(self.client_port))
        print('trying to connect to',self.target_addr, ' on port ', str(self.target_port))
        self.connect()

        print('Client is Connected!')
        while True:
            self.send_packet(bytearray('hi', 'utf-8'))
            print('client sent hi, now waiting to receive server stuff!')
            self.receive_packet(4096)
            
            # send hello, addr not required since tcp
            result = self.incoming_buffer.pop()
            print('Client received packet of length: ',len(result))
            if len(result) == 539:
                print('CRASHED THE CLIENT')
                # 7th iteration should cause a crash
                # write to file that monitor_target is reading
                assert result == bytearray(b'magic phrase:passworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassword')
                with open('./tests/assets/integration_test_3/crash.log', 'w') as file:
                    file.write('crashed')
                    self.communication_conn.close()
                return
            self.send_packet(bytearray('incorrect magic phrase, try again!', 'utf-8'))
            print('sent error packet!')
            time.sleep(1.25)
    