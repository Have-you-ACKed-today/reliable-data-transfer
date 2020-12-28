'''
    This file is a client write by qiushi
    just for testing
'''
from rdt import RDTSocket

def test_handshake():
    s = RDTSocket()
    s.connect(('127.0.0.1', 9999))
    s.close()


if __name__ == '__main__':
    test_handshake()
