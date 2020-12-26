from rdt import RDTSocket


if __name__ == '__main__':
    s = RDTSocket()
    s.connect(('127.0.0.1', 9999))
    s.send(b'Hello')
    # print("message back is: ", s.recv(1024))
    s.close()
    # s = RDTSocket()
    # s.connect(('127.0.0.1', 12345))
    # s.close()
