'''
    This file is a server write by qiushi
    just for testing
'''
from rdt import RDTSocket

def test_handshake():
    server = RDTSocket()
    server.bind(('127.0.0.1', 9999))
    conn, client_addr = server.accept()
    conn.close()


if __name__ == '__main__':
    test_handshake()
