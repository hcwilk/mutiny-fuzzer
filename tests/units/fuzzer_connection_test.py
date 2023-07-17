from backend.fuzzer_connection import FuzzerConnection
from backend.fuzzer_data import FuzzerData
from tests.assets.mock_targets import MockServer, MockClient
from backend.menu_functions import print_warning
import threading
import ssl
from time import sleep
import unittest
import socket
from getmac import get_mac_address as gma
import platform

class TestFuzzerConnection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.platform = platform.uname().system
        cls.received_data = []

    def setUp(self):
        pass

    def tearDown(self):
        pass

# CONNECTIONS -- CLIENT

    def test_FuzzerConnectionInit_tcp_ipv4(self):
        print('runnings')
        proto = 'tcp'
        mock_if = '127.0.0.1'
        mock_port = 9999
        src_if = '127.0.0.1'
        src_port = 8889
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        if self.platform == 'Darwin':
            print_warning('Skipping Raw Fuzzer Connection Init Test\n Raw Packet\'s are currently unsupported on OSX')
            return
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        self.assertEqual(conn.proto, proto)
        self.assertEqual(conn.host, mock_if)
        self.assertEqual(conn.target_port, mock_port)
        self.assertEqual(conn.source_ip, src_if)
        self.assertEqual(conn.source_port, src_port)
        self.assertEqual(conn.addr, (mock_if, mock_port))
        self.assertEqual(conn.connection.family, socket.AF_INET)
        self.assertEqual(conn.connection.type, socket.SOCK_STREAM)
        listener_thread.join()
        target.communication_conn.close()
        target.listen_conn.close()
        conn.close()
    
    def test_FuzzerConnectionInit_tcp_ipv6(self):
        proto = 'tcp'
        mock_if = '::1'
        mock_port = 9998
        src_if = '::1'
        src_port = 8888
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        self.assertEqual(conn.proto, proto)
        self.assertEqual(conn.host, mock_if)
        self.assertEqual(conn.target_port, mock_port)
        self.assertEqual(conn.source_ip, src_if)
        self.assertEqual(conn.source_port, src_port)
        self.assertEqual(conn.addr, (mock_if, mock_port))
        self.assertEqual(conn.connection.family, socket.AF_INET6)
        self.assertEqual(conn.connection.type, socket.SOCK_STREAM)
        listener_thread.join()
        target.communication_conn.close()
        target.listen_conn.close()
        conn.close()
    
    def test_FuzzerConnectionInit_udp_ipv4(self):
        proto = 'udp'
        mock_if = '127.0.0.1'
        mock_port = 9997
        src_if = '127.0.0.1'
        src_port = 8887
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        self.assertEqual(conn.proto, proto)
        self.assertEqual(conn.host, mock_if)
        self.assertEqual(conn.target_port, mock_port)
        self.assertEqual(conn.source_ip, src_if)
        self.assertEqual(conn.source_port, src_port)
        self.assertEqual(conn.addr, (mock_if, mock_port))
        self.assertEqual(conn.connection.family, socket.AF_INET)
        self.assertEqual(conn.connection.type, socket.SOCK_DGRAM)
        listener_thread.join()
        conn.close()
        target.communication_conn.close()

    def test_FuzzerConnectionInit_udp_ipv6(self):
        proto = 'udp'
        mock_if = '::1'
        mock_port = 9996
        src_if = '::1'
        src_port = 8886
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        self.assertEqual(conn.proto, proto)
        self.assertEqual(conn.host, mock_if)
        self.assertEqual(conn.target_port, mock_port)
        self.assertEqual(conn.source_ip, src_if)
        self.assertEqual(conn.source_port, src_port)
        self.assertEqual(conn.addr, (mock_if, mock_port))
        self.assertEqual(conn.connection.family, socket.AF_INET6)
        self.assertEqual(conn.connection.type, socket.SOCK_DGRAM)
        listener_thread.join()
        target.communication_conn.close()

        conn.close()
    
    def test_FuzzerConnectionInit_tls_ipv4(self):
        proto = 'tls'
        mock_if = '127.0.0.1'
        mock_port = 9995
        src_if = '127.0.0.1'
        src_port = 8885
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server, testing=True)
        conn._get_addr()
        conn._connect_to_tls_socket()
        self.assertEqual(conn.proto, proto)
        self.assertEqual(conn.host, mock_if)
        self.assertEqual(conn.target_port, mock_port)
        self.assertEqual(conn.source_ip, src_if)
        self.assertEqual(conn.source_port, src_port)
        self.assertEqual(conn.addr, (mock_if, mock_port))
        self.assertEqual(conn.connection.family, socket.AF_INET)
        self.assertEqual(conn.connection.type, socket.SOCK_STREAM)
        self.assertIsInstance(conn.connection, ssl.SSLSocket)
        listener_thread.join()
        conn.close()
        target.communication_conn.close()
        target.listen_conn.close()
    
    def test_FuzzerConnectionInit_tls_ipv6(self):
        proto = 'tls'
        mock_if = '::1'
        mock_port = 9994
        src_if = '::1'
        src_port = 8884
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server, testing=True)
        conn._get_addr()
        conn._connect_to_tls_socket()
        self.assertEqual(conn.proto, proto)
        self.assertEqual(conn.host, mock_if)
        self.assertEqual(conn.target_port, mock_port)
        self.assertEqual(conn.source_ip, src_if)
        self.assertEqual(conn.source_port, src_port)
        self.assertEqual(conn.addr, (mock_if, mock_port))
        self.assertEqual(conn.connection.family, socket.AF_INET6)
        self.assertEqual(conn.connection.type, socket.SOCK_STREAM)
        self.assertIsInstance(conn.connection, ssl.SSLSocket)
        listener_thread.join()
        conn.close()
        target.communication_conn.close()
        target.listen_conn.close()
    
    def test_FuzzerConnectionInit_raw(self):
        if self.platform == 'Darwin':
            print_warning('Skipping Raw Fuzzer Connection Init Test\n Raw Packet\'s are currently unsupported on OSX')
            return
        proto = 'L2raw'
        mock_if = gma()
        mock_port = 0
        src_if = gma()
        src_port = 0
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        self.assertEqual(conn.proto, proto)
        self.assertEqual(conn.host, mock_if)
        self.assertEqual(conn.target_port, mock_port)
        self.assertEqual(conn.source_ip, src_if)
        self.assertEqual(conn.source_port, src_port)
        self.assertEqual(conn.addr, (mock_if, mock_port))
        self.assertEqual(conn.connection.family, socket.AF_PACKET)
        self.assertEqual(conn.connection.type, socket.SOCK_RAW)
        listener_thread.join()
        conn.close()
        target.communication_conn.close()


# SENDING PACKETS -- CLIENT
    def test_send_packet_tcp_ipv4(self):
        proto = 'tcp'
        mock_if = '127.0.0.1'
        mock_port = 9993
        src_if = '127.0.0.1'
        src_port = 8883
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        data = bytes('test', 'utf-8')
        sleep(.1) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        listener_thread.join()
        reception_thread = threading.Thread(target=target.receive_packet, args=(len(data),))
        reception_thread.start()
        sleep(.1)
        conn.send_packet(data, 3.0)
        reception_thread.join()
        conn.connection.close()
        target.communication_conn.close()
        target.listen_conn.close()
        self.assertEqual(target.incoming_buffer.pop(), data)


    def test_send_packet_tcp_ipv6(self):
        proto = 'tcp'
        mock_if = '::1'
        mock_port = 9992
        src_if = '::1'
        src_port = 8882
        server = False

        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        data = bytes('test', 'utf-8')
        sleep(.1) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        listener_thread.join()
        reception_thread = threading.Thread(target=target.receive_packet, args=(len(data),))
        reception_thread.start()
        conn.send_packet(data, 3.0)
        reception_thread.join()
        conn.connection.close()
        target.communication_conn.close()
        target.listen_conn.close()
        self.assertEqual(target.incoming_buffer.pop(), data)

    def test_send_packet_udp_ipv4(self):
        proto = 'udp'
        mock_if = '127.0.0.1'
        mock_port = 9991
        src_if = '127.0.0.1'
        src_port = 8881
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        data = bytes('test', 'utf-8')
        sleep(.1)
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        listener_thread.join()
        reception_thread = threading.Thread(target=target.receive_packet, args=(len(data),))
        reception_thread.start()
        conn.send_packet(data, 3.0)
        reception_thread.join()
        conn.connection.close()
        target.communication_conn.close()
        self.assertEqual(target.incoming_buffer.pop(),data)
    
    def test_send_packet_udp_ipv6(self):
        proto = 'udp'
        mock_if = '::1'
        mock_port = 9990
        src_if = '::1'
        src_port = 8880
        server = False

        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        data = bytes('test', 'utf-8')
        sleep(.1)
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        listener_thread.join()
        reception_thread = threading.Thread(target=target.receive_packet, args=(len(data),))
        reception_thread.start()
        conn.send_packet(data, 3.0)
        reception_thread.join()
        conn.connection.close()
        target.communication_conn.close()
        self.assertEqual(target.incoming_buffer.pop(),data)

    def test_send_packet_tls_ipv4(self):
        proto = 'tls'
        mock_if = '127.0.0.1'
        mock_port = 9989
        src_if = '127.0.0.1'
        src_port = 8879
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        data = bytes('test', 'utf-8')
        sleep(.1)
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server, testing=True)
        conn._get_addr()
        conn._connect_to_tls_socket()
        listener_thread.join()
        reception_thread = threading.Thread(target=target.receive_packet, args=(len(data),))
        reception_thread.start()
        conn.send_packet(data, 3.0)
        reception_thread.join()
        conn.connection.close()
        target.communication_conn.close()
        target.listen_conn.close()
        self.assertEqual(target.incoming_buffer.pop(),data)

    def test_send_packet_tls_ipv6(self):
        proto = 'tls'
        mock_if = '::1'
        mock_port = 9988
        src_if = '::1'
        src_port = 8878
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        data = bytes('test', 'utf-8')
        sleep(.1)
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server, testing=True)
        conn._get_addr()
        conn._connect_to_tls_socket()
        listener_thread.join()
        reception_thread = threading.Thread(target=target.receive_packet, args=(len(data),))
        reception_thread.start()
        conn.send_packet(data, 3.0)
        reception_thread.join()
        conn.connection.close()
        target.communication_conn.close()
        target.listen_conn.close()
        self.assertEqual(target.incoming_buffer.pop(),data)

    def test_send_packet_raw(self):
        if self.platform == 'Darwin':
            print_warning('Skipping Raw Send Packet Test\n Raw Packet\'s are currently unsupported on OSX')
            return
        proto = 'L2raw'
        mock_if = gma()
        mock_port = 0
        src_if = gma()
        src_port = 0
        server = False

        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        data = bytes('optimist', 'utf-8')
        sleep(.1)
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        listener_thread.join()
        reception_thread = threading.Thread(target=target.receive_packet, args=(len(data),))
        reception_thread.start()
        conn.send_packet(data, 3.0)
        reception_thread.join()
        conn.connection.close()
        target.communication_conn.close()
        self.assertEqual(target.incoming_buffer.pop(),data)


# RECEIVING PACKETS -- CLIENT


    def receive_packet_wrapper(self, conn, bytes_to_read, timeout):
        '''
        wrapper around FuzzerConnection.receive_packet that sets the return value of receive_packet
        to self.received_data so that it can be accessed from the main thread
        '''
        self.received_data.append(conn.receive_packet(bytes_to_read, timeout))

    def test_receive_packet_tcp_ipv4(self):
        proto = 'tcp'
        mock_if = '127.0.0.1'
        mock_port = 9987
        src_if = '127.0.0.1'
        src_port = 8877
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        data = bytes('test', 'utf-8')
        sleep(.1)
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        listener_thread.join()
        reception_thread = threading.Thread(target=self.receive_packet_wrapper, args=(conn, len(data), 3.0))
        reception_thread.start()
        target.addr = (mock_if, mock_port)
        target.send_packet(data)
        reception_thread.join()
        conn.connection.close()
        target.communication_conn.close()
        target.listen_conn.close()
        self.assertEqual(self.received_data.pop(), data)


    def test_receive_packet_tcp_ipv6(self):
        proto = 'tcp'
        mock_if = '::1'
        mock_port = 9986
        src_if = '::1'
        src_port = 8876
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        data = bytes('test', 'utf-8')
        sleep(.1)
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        listener_thread.join()
        reception_thread = threading.Thread(target=self.receive_packet_wrapper, args=(conn, len(data), 3.0))
        reception_thread.start()
        target.addr = (mock_if, mock_port)
        target.send_packet(data)
        reception_thread.join()
        conn.connection.close()
        target.communication_conn.close()
        target.listen_conn.close()
        self.assertEqual(self.received_data.pop(), data)

    def test_receive_packet_udp_ipv4(self):
        proto = 'udp'
        mock_if = '127.0.0.1'
        mock_port = 9985
        src_if = '127.0.0.1'
        src_port = 8875
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        data = bytes('test', 'utf-8')
        sleep(.1)
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        listener_thread.join()
        reception_thread = threading.Thread(target=self.receive_packet_wrapper, args=(conn, len(data), 3.0))
        reception_thread.start()
        target.addr = (src_if, src_port)
        target.send_packet(data)
        reception_thread.join()
        conn.connection.close()
        target.communication_conn.close()
        self.assertEqual(self.received_data.pop(), data)


    def test_receive_packet_udp_ipv6(self):
        proto = 'udp'
        mock_if = '::1'
        mock_port = 9984
        src_if = '::1'
        src_port = 8874
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        data = bytes('test', 'utf-8')
        sleep(.1)
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        listener_thread.join()
        reception_thread = threading.Thread(target=self.receive_packet_wrapper, args=(conn, len(data), 3.0))
        reception_thread.start()
        target.addr = (src_if, src_port)
        target.send_packet(data)
        reception_thread.join()
        conn.connection.close()
        target.communication_conn.close()
        self.assertEqual(self.received_data.pop(), data)


    def test_receive_packet_tls_ipv4(self):
        proto = 'tls'
        mock_if = '127.0.0.1'
        mock_port = 9983
        src_if = '127.0.0.1'
        src_port = 8873
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        data = bytes('test', 'utf-8')
        sleep(.1)
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server, testing=True)
        conn._get_addr()
        conn._connect_to_tls_socket()
        listener_thread.join()
        reception_thread = threading.Thread(target=self.receive_packet_wrapper, args=(conn, len(data), 3.0))
        reception_thread.start()
        target.addr =  (src_if, src_port)
        target.send_packet(data)
        reception_thread.join()
        conn.connection.close()
        target.communication_conn.close()
        target.listen_conn.close()
        self.assertEqual(self.received_data.pop(), data)

    def test_receive_packet_tls_ipv6(self):
        proto = 'tls'
        mock_if = '::1'
        mock_port = 9982
        src_if = '::1'
        src_port = 8872
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        data = bytes('test', 'utf-8')
        sleep(.1)
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server, testing=True)
        conn._get_addr()
        conn._connect_to_tls_socket()
        listener_thread.join()
        reception_thread = threading.Thread(target=self.receive_packet_wrapper, args=(conn, len(data), 3.0))
        reception_thread.start()
        target.addr = (src_if, src_port)
        target.send_packet(data)
        reception_thread.join()
        conn.connection.close()
        target.communication_conn.close()
        target.listen_conn.close()
        self.assertEqual(self.received_data.pop(), data)


    def test_receive_packet_raw(self):
        if self.platform == 'Darwin':
            print_warning('Skipping Raw Fuzzer Connection Init Test\n Raw Packet\'s are currently unsupported on OSX')
            return
        proto = 'L2raw'
        mock_if = gma()
        mock_port = 0
        src_if = gma()
        src_port = 0
        server = False
        
        target = MockServer(proto, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.accept_connection)
        listener_thread.start()
        data = bytes('ayeyoletsgo', 'utf-8')
        sleep(.1)
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        listener_thread.join()
        reception_thread = threading.Thread(target=self.receive_packet_wrapper, args=(conn, len(data), 3.0))
        reception_thread.start()
        # Don't need ports for raw
        target.addr = src_if
        target.send_packet(data)
        reception_thread.join()
        conn.connection.close()
        target.communication_conn.close()
        self.assertEqual(self.received_data.pop(), data)

   

# CONNECTIONS -- SERVER

    def test_FuzzerConnectionInit_tcp_ipv4_server(self):
        proto = 'tcp'
        # target (where it's being hosted)
        mock_if = '127.0.0.1'
        # target (where it's being hosted)
        mock_port = 9981
        src_if = '127.0.0.1'
        src_port = 8871
        server= True

        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        self.assertEqual(conn.proto, proto)
        self.assertEqual(conn.host, mock_if)
        self.assertEqual(conn.target_port, mock_port)
        self.assertEqual(conn.source_ip, src_if)
        self.assertEqual(conn.source_port, src_port)
        self.assertEqual(conn.addr, (src_if, src_port))
        self.assertEqual(conn.list_connection.family, socket.AF_INET)
        self.assertEqual(conn.list_connection.type, socket.SOCK_STREAM)
        self.assertEqual(target.client_addr,src_if)
        self.assertEqual(target.client_port,src_port)
        listener_thread.join()
        target.communication_conn.close()
        conn.close()


    def test_FuzzerConnectionInit_tcp_ipv6_server(self):
        proto = 'tcp'
        mock_if = '::1'
        mock_port = 9980
        src_if = '::1'
        src_port = 8870
        server=True
        
        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        self.assertEqual(conn.proto, proto)
        self.assertEqual(conn.host, mock_if)
        self.assertEqual(conn.target_port, mock_port)
        self.assertEqual(conn.source_ip, src_if)
        self.assertEqual(conn.source_port, src_port)
        self.assertEqual(conn.addr, (src_if, src_port))
        self.assertEqual(conn.list_connection.family, socket.AF_INET6)
        self.assertEqual(conn.list_connection.type, socket.SOCK_STREAM)
        self.assertEqual(target.client_addr,src_if)
        self.assertEqual(target.client_port,src_port)
        listener_thread.join()
        target.communication_conn.close()
        conn.close()
    
    def test_FuzzerConnectionInit_udp_ipv4_server(self):
        proto = 'udp'
        mock_if = '127.0.0.1'
        mock_port = 9979
        src_if = '127.0.0.1'
        src_port = 8869
        server= True
        
        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        self.assertEqual(conn.proto, proto)
        self.assertEqual(conn.host, mock_if)
        self.assertEqual(conn.target_port, mock_port)
        self.assertEqual(conn.source_ip, src_if)
        self.assertEqual(conn.source_port, src_port)
        self.assertEqual(conn.addr, (src_if, src_port))
        self.assertEqual(conn.connection.family, socket.AF_INET)
        self.assertEqual(conn.connection.type, socket.SOCK_DGRAM)
        listener_thread.join()
        target.communication_conn.close()
        conn.close()

    def test_FuzzerConnectionInit_udp_ipv6_server(self):
        proto = 'udp'
        mock_if = '::1'
        mock_port = 9978
        src_if = '::1'
        src_port = 8868
        server = True
        
        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        self.assertEqual(conn.proto, proto)
        self.assertEqual(conn.host, mock_if)
        self.assertEqual(conn.target_port, mock_port)
        self.assertEqual(conn.source_ip, src_if)
        self.assertEqual(conn.source_port, src_port)
        self.assertEqual(conn.addr, (src_if, src_port))
        self.assertEqual(conn.connection.family, socket.AF_INET6)
        self.assertEqual(conn.connection.type, socket.SOCK_DGRAM)
        listener_thread.join()
        target.communication_conn.close()
        conn.close()
    
    def test_FuzzerConnectionInit_tls_ipv4(self):
        proto = 'tls'
        mock_if = '127.0.0.1'
        mock_port = 9977
        src_if = '127.0.0.1'
        src_port = 8867
        server = True
        
        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server, testing=True)
        conn._get_addr()
        conn._connect_to_tls_socket()
        self.assertEqual(conn.proto, proto)
        self.assertEqual(conn.host, mock_if)
        self.assertEqual(conn.target_port, mock_port)
        self.assertEqual(conn.source_ip, src_if)
        self.assertEqual(conn.source_port, src_port)
        self.assertEqual(conn.list_connection.family, socket.AF_INET)
        self.assertEqual(conn.list_connection.type, socket.SOCK_STREAM)
        self.assertIsInstance(conn.list_connection, ssl.SSLSocket)
        listener_thread.join()
        conn.close()
        target.communication_conn.close()

    def test_FuzzerConnectionInit_tls_ipv6(self):
        proto = 'tls'
        mock_if = '::1'
        mock_port = 9976
        src_if = '::1'
        src_port = 8866
        server = True
        
        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server, testing=True)
        conn._get_addr()
        conn._connect_to_tls_socket()
        self.assertEqual(conn.proto, proto)
        self.assertEqual(conn.host, mock_if)
        self.assertEqual(conn.target_port, mock_port)
        self.assertEqual(conn.source_ip, src_if)
        self.assertEqual(conn.source_port, src_port)
        self.assertEqual(conn.addr, (src_if, src_port))
        self.assertEqual(conn.connection.family, socket.AF_INET6)
        self.assertEqual(conn.connection.type, socket.SOCK_STREAM)
        self.assertIsInstance(conn.connection, ssl.SSLSocket)
        listener_thread.join()
        target.communication_conn.close()
        conn.close()
    
    def test_FuzzerConnectionInit_raw_server(self):
        if self.platform == 'Darwin':
            print_warning('Skipping Raw Fuzzer Connection Init Test\n Raw Packet\'s are currently unsupported on OSX')
            return
        proto = 'L2raw'
        mock_if = gma()
        mock_port = 0
        src_if = gma()
        src_port = 0
        server = True
        
        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        self.assertEqual(conn.proto, proto)
        self.assertEqual(conn.host, mock_if)
        self.assertEqual(conn.target_port, mock_port)
        self.assertEqual(conn.source_ip, src_if)
        self.assertEqual(conn.source_port, src_port)
        self.assertEqual(conn.addr, (mock_if, mock_port))
        self.assertEqual(conn.connection.family, socket.AF_PACKET)
        self.assertEqual(conn.connection.type, socket.SOCK_RAW)
        listener_thread.join()
        conn.close()
        target.communication_conn.close()


# RECEIVING PACKETS -- SERVER

    def test_receive_packet_tcp_ipv4_server(self):
        proto = 'tcp'
        mock_if = '127.0.0.1'
        mock_port = 9975
        src_if = '127.0.0.1'
        src_port = 8865
        server = True

        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        data = bytes('this should say 24 bytes', 'utf-8')
        listener_thread.join()
        reception_thread = threading.Thread(target=self.receive_packet_wrapper, args=(conn,len(data),3.0))
        reception_thread.start()
        target.send_packet(data)
        reception_thread.join()
        sleep(1)
        conn.list_connection.close()
        conn.connection.close()
        target.communication_conn.close()
        self.assertEqual(self.received_data.pop(), data)


    def test_receive_packet_tcp_ipv6_server(self):
        proto = 'tcp'
        mock_if = '::1'
        mock_port = 9974
        src_if = '::1'
        src_port = 8864
        server = True

        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        data = bytes('this should say 24 bytes', 'utf-8')
        listener_thread.join()
        reception_thread = threading.Thread(target=self.receive_packet_wrapper, args=(conn,len(data),3.0))
        reception_thread.start()
        target.send_packet(data)
        reception_thread.join()
        sleep(1)
        conn.list_connection.close()
        conn.connection.close()
        target.communication_conn.close()
        self.assertEqual(self.received_data.pop(), data)


    def test_receive_packet_udp_ipv4_server(self):
        proto = 'udp'
        mock_if = '127.0.0.1'
        mock_port = 9973
        src_if = '127.0.0.1'
        src_port = 8863
        server = True

        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        data = bytes('this should say 24 bytes', 'utf-8')
        listener_thread.join()
        reception_thread = threading.Thread(target=self.receive_packet_wrapper, args=(conn,len(data),3.0))
        reception_thread.start()
        target.send_packet(data)
        reception_thread.join()
        sleep(1)
        conn.close()
        target.communication_conn.close()
        self.assertEqual(self.received_data.pop(), data)


    def test_receive_packet_udp_ipv6_server(self):
        proto = 'udp'
        mock_if = '::1'
        mock_port = 9972
        src_if = '::1'
        src_port = 8862
        server = True

        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        data = bytes('this should say 24 bytes', 'utf-8')
        listener_thread.join()
        reception_thread = threading.Thread(target=self.receive_packet_wrapper, args=(conn,len(data),3.0))
        reception_thread.start()
        target.send_packet(data)
        reception_thread.join()
        sleep(1)
        conn.close()
        target.communication_conn.close()
        self.assertEqual(self.received_data.pop(), data)

    def test_receive_packet_tls_ipv4_server(self):
        proto = 'tls'
        mock_if = '127.0.0.1'
        mock_port = 9971
        src_if = '127.0.0.1'
        src_port = 8861
        server = True
        
        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server, testing=True)
        conn._get_addr()
        conn._connect_to_tls_socket()
        listener_thread.join()
        data = bytes('this should say 24 bytes', 'utf-8')
        reception_thread = threading.Thread(target=self.receive_packet_wrapper, args=(conn,len(data),3.0))
        reception_thread.start()
        target.send_packet(data)
        reception_thread.join()
        sleep(1)
        conn.close()
        target.communication_conn.close()
        self.assertEqual(self.received_data.pop(), data)


    def test_receive_packet_tls_ipv6_server(self):
        proto = 'tls'
        mock_if = '::1'
        mock_port = 9970
        src_if = '::1'
        src_port = 8860
        server = True
        
        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server, testing=True)
        conn._get_addr()
        conn._connect_to_tls_socket()
        listener_thread.join()
        data = bytes('this should say 24 bytes', 'utf-8')
        reception_thread = threading.Thread(target=self.receive_packet_wrapper, args=(conn,len(data),3.0))
        reception_thread.start()
        target.send_packet(data)
        reception_thread.join()
        sleep(1)
        conn.close()
        target.communication_conn.close()
        self.assertEqual(self.received_data.pop(), data)

    def test_receive_packet_raw(self):
        if self.platform == 'Darwin':
            print_warning('Skipping Raw Fuzzer Connection Init Test\n Raw Packet\'s are currently unsupported on OSX')
            return
        proto = 'L2raw'
        mock_if = gma()
        mock_port = 0
        src_if = gma()
        src_port = 0
        server = True
        
        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        listener_thread.join()
        data = bytes('this should say 24 bytes', 'utf-8')
        reception_thread = threading.Thread(target=self.receive_packet_wrapper, args=(conn,len(data),3.0))
        reception_thread.start()
        target.send_packet(data)
        reception_thread.join()
        sleep(1)
        conn.close()
        target.communication_conn.close()
        self.assertEqual(self.received_data.pop(), data)


# SENDING PACKETS -- SERVER


    def test_send_packet_tcp_ipv4_server(self):
        proto = 'tcp'
        mock_if = '127.0.0.1'
        mock_port = 9968
        src_if = '127.0.0.1'
        src_port = 8858
        server = True
        
        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        data = bytes('again', 'utf-8')
        listener_thread.join()
        reception_thread = threading.Thread(target=target.receive_packet, args=(len(data),))
        reception_thread.start()
        conn.send_packet(data,3.0)
        reception_thread.join()
        sleep(1)
        conn.close()
        target.communication_conn.close()
        self.assertEqual(target.incoming_buffer.pop(), data)


    def test_send_packet_tcp_ipv6_server(self):
        proto = 'tcp'
        mock_if = '::1'
        mock_port = 9967
        src_if = '::1'
        src_port = 8857
        server = True
        
        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        data = bytes('again', 'utf-8')
        listener_thread.join()
        
        reception_thread = threading.Thread(target=target.receive_packet, args=(len(data),))
        reception_thread.start()
        conn.send_packet(data,3.0)
        reception_thread.join()
        sleep(1)
        conn.close()
        target.communication_conn.close()
        self.assertEqual(target.incoming_buffer.pop(), data)


    def test_send_packet_udp_ipv4_server(self):
        proto = 'udp'
        mock_if = '127.0.0.1'
        mock_port = 9966
        src_if = '127.0.0.1'
        src_port = 8856
        server = True
        
        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        data = bytes('again', 'utf-8')
        listener_thread.join()
        reception_thread = threading.Thread(target=target.receive_packet, args=(len(data),))
        reception_thread.start()
        sleep(.5)
        conn.send_packet(data,3.0)
        reception_thread.join()
        conn.close()
        target.communication_conn.close()
        self.assertEqual(target.incoming_buffer.pop(), data)

    def test_send_packet_udp_ipv6_server(self):
        proto = 'udp'
        mock_if = '::1'
        mock_port = 9965
        src_if = '::1'
        src_port = 8855
        server = True
        
        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        data = bytes('again', 'utf-8')
        listener_thread.join()
        reception_thread = threading.Thread(target=target.receive_packet, args=(len(data),))
        reception_thread.start()
        sleep(.5)
        conn.send_packet(data,3.0)
        reception_thread.join()
        conn.close()
        target.communication_conn.close()
        self.assertEqual(target.incoming_buffer.pop(), data)


    def test_send_packet_tls_ipv4_server(self):
        proto = 'tls'
        mock_if = '127.0.0.1'
        mock_port = 9964
        src_if = '127.0.0.1'
        src_port = 8854
        server = True
        
        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server, testing=True)
        conn._get_addr()
        conn._connect_to_tls_socket()
        listener_thread.join()
        data = bytes('tls baby', 'utf-8')
        reception_thread = threading.Thread(target=target.receive_packet, args=(len(data),))
        reception_thread.start()
        conn.send_packet(data,3.0)
        reception_thread.join()
        sleep(1)
        conn.close()
        target.communication_conn.close()
        self.assertEqual(target.incoming_buffer.pop(), data)
    

    def test_send_packet_tls_ipv6_server(self):
        proto = 'tls'
        mock_if = '::1'
        mock_port = 9963
        src_if = '::1'
        src_port = 8853
        server = True
        
        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server, testing=True)
        conn._get_addr()
        conn._connect_to_tls_socket()
        listener_thread.join()
        data = bytes('tls baby', 'utf-8')
        reception_thread = threading.Thread(target=target.receive_packet, args=(len(data),))
        reception_thread.start()
        conn.send_packet(data,3.0)
        reception_thread.join()
        sleep(1)
        conn.close()
        target.communication_conn.close()
        self.assertEqual(target.incoming_buffer.pop(), data)

           
    def test_send_packet_raw(self):
        if self.platform == 'Darwin':
            print_warning('Skipping Raw Fuzzer Connection Init Test\n Raw Packet\'s are currently unsupported on OSX')
            return
        proto = 'L2raw'
        mock_if = gma()
        mock_port = 0
        src_if = gma()
        src_port = 0
        server = True
        
        target = MockClient(proto, src_if, src_port, mock_if, mock_port)
        listener_thread = threading.Thread(target=target.connect)
        listener_thread.start()
        sleep(.5) # avoid race, allow handle_connections to bind and listen
        conn = FuzzerConnection(proto, mock_if, mock_port, src_if, src_port, server)
        listener_thread.join()
        data = bytes('tls baby', 'utf-8')
        reception_thread = threading.Thread(target=target.receive_packet, args=(len(data),))
        reception_thread.start()
        conn.send_packet(data,3.0)
        reception_thread.join()
        sleep(1)
        conn.close()
        target.communication_conn.close()
        self.assertEqual(target.incoming_buffer.pop(), data)
