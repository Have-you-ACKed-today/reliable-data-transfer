from socket import socket, AF_INET, SOCK_STREAM
from rdt import RDTSocket
import pysnooper
import time


@pysnooper.snoop()
def main():
    server = RDTSocket()
    # server = socket(AF_INET, SOCK_STREAM) # check what python socket does
    server.bind(('127.0.0.1', 9999))
    # server.listen(0) # check what python socket does

    passage = bytes()

    while True:
        conn, client_addr = server.accept()
        start = time.perf_counter()
        while True:
            print(passage.decode())
            data = conn.recv(2048)
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


if __name__ == '__main__':
    main()
