from tests.assets.mock_target import MockTarget
import socket
import time

class Target2(MockTarget):

    def accept_fuzz(self):
        #TODO: make message_processor.preconnect available, assert its being called
        # accept initial connection
        self.accept_connection()
        while True:
            # receive 'greetings <fuzzzed subcomponent>'
            self.receive_packet(4096)
            result = self.incoming_buffer.pop()
            if len(result) > 100 and len(result) < 120:
                
                expected_result = bytearray('greetings dartearteartearteartearteartearteartearteartearteartearteartearteartearteartearthearthrthlings', 'utf-8')
                assert result == expected_result
                with open('./tests/assets/integration_test_2/crash.log', 'w') as file:
                    file.write('crashed')
                    self.communication_conn.close()
                    if self.communication_conn.type == socket.SOCK_STREAM:
                        self.listen_conn.close()
                return
            if self.communication_conn.type == socket.SOCK_STREAM:
                self.communication_conn = self.listen_conn.accept()[0]
