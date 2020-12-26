'''
    This file is a client write by qiushi
    just for testing
'''
import time

from rdt import RDTSocket


if __name__ == '__main__':
    s = RDTSocket()
    s.connect(('127.0.0.1', 9999))
    s.send(b'Hello')
    print("message back is: ", s.recv(4096))
    time.sleep(1)
    s.close()
    # s = RDTSocket()
    # s.connect(('127.0.0.1', 12345))
    # s.close()
