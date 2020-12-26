'''
    This file is a server write by qiushi
    just for testing
'''
import time

from rdt import RDTSocket


if __name__ == '__main__':
    server = RDTSocket()
    server.bind(('127.0.0.1', 9999))

    passage = bytes()

    while True:
        conn, client_addr = server.accept()
        start = time.perf_counter()
        # while True:
        # print(passage.decode())
        data = conn.recv(4096)
        if data:
            passage += data
            conn.send(data)
        else:
            break
        '''
        make sure the following is reachable
        '''
        conn.close()
        print(f'connection finished in {time.perf_counter() - start}s')
