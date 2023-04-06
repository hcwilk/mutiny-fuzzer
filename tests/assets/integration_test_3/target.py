from tests.assets.mock_target import MockClient
import socket
import ssl


class Target3(MockClient):

    def connect_fuzz(self):
        #TODO: make message_processor.preconnect available, assert its being called
        # accept initial connection (commented out because it already should do this)
        # self.accept_connection()
        print('heres where im binding to ',self.client_addr, ' on port ', str(self.client_port))
        print('trying to connect to',self.target_addr, ' on port ', str(self.target_port))
        socket_family = socket.AF_INET if '.' in self.client_addr else socket.AF_INET6
        self.communication_conn = socket.socket(socket_family, socket.SOCK_STREAM)
        self.communication_conn.bind((self.client_addr, self.client_port))
        self.communication_conn.connect((self.target_addr, self.target_port))

        print('Client is Connected!')
        while True:
            self.send_packet(bytearray('hi', 'utf-8'))
            # receive 'greetings <fuzzzed subcomponent>'
            # receive hi
            print('client waiting to receive server stuff!')
            self.receive_packet(5)
            print('received packet, i am client')
            # send hello, addr not required since tcp
            result = self.incoming_buffer.pop()
            if len(result) == 539:
                print('this shouldnt be hitting irght now')
                # 7th iteration should cause a crash
                # write to file that monitor_target is reading
                assert result == bytearray(b'magic phrase:passworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassworpassword')
                with open('./tests/assets/integration_test_1/crash.log', 'w') as file:
                    file.write('crashed')
                    if self.communication_conn.type == socket.SOCK_STREAM:
                        self.listen_conn.close()
                    self.communication_conn.close()
                return
            self.send_packet(bytearray('incorrect magic phrase, try again!', 'utf-8'))
            print('sent error packet!')
    
