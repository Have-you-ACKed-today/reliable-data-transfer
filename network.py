from socket import socket, AF_INET, SOCK_DGRAM, inet_aton, inet_ntoa
import random, time
import threading, queue
from socketserver import ThreadingUDPServer

from rdt_message import RdtMessage, unpack

lock = threading.Lock()


def bytes_to_addr(bytes):
    return inet_ntoa(bytes[:4]), int.from_bytes(bytes[4:8], 'big')


def addr_to_bytes(addr):
    return inet_aton(addr[0]) + addr[1].to_bytes(4, 'big')


def corrupt(data: bytes) -> bytes:
    raw = list(data)
    for _ in range(0, random.randint(0, 3)):
        pos = random.randint(0, len(raw) - 1)
        raw[pos] = random.randint(0, 255)
    return bytes(raw)


class Server(ThreadingUDPServer):
    def __init__(self, addr, rate=None, delay=None, corrupt=None, loss=None):
        super().__init__(addr, None)
        self.rate = rate
        self.buffer = 0
        self.delay = delay
        self.corrupt = corrupt
        self.loss = loss

    def verify_request(self, request, client_address):
        if self.buffer < 100000:
            self.buffer += 1
            return True
        else:
            print("BOOM!!!")
            return False

    def finish_request(self, request, client_address):
        data, socket = request
        lock.acquire()
        if self.rate: time.sleep(len(data) / self.rate)
        self.buffer -= 1
        lock.release()

        to = bytes_to_addr(data[:8])
        print(client_address, to)
        print(unpack(data[8:])[0].to_string())
        print(unpack(data[8:])[0].payload)
        corrupt_data = data[8:]
        if random.random() < self.loss:
            print('loss')
        else:
            if random.random() < self.corrupt:
                print('corrupt')
                corrupt_data = corrupt(corrupt_data)
            socket.sendto(addr_to_bytes(client_address) + corrupt_data, to)


server_address = ('127.0.0.1', 12345)

if __name__ == '__main__':
    with Server(server_address, rate=10240, corrupt=.05, loss=0.1) as server:
        server.serve_forever()
