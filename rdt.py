from USocket import UnreliableSocket
from rdt_message import HEADER_LENGTH, RdtMessage, unpack, make_ack
from utils import make_data_parts
import threading
import time
import random

PAYLOAD_SIZE = 1024
WINDOW_SIZE = 8
PACKET_SIZE = 8 + HEADER_LENGTH + PAYLOAD_SIZE
TIME_OUT = 2000

## our socket rdt
class RDTSocket(UnreliableSocket):
    """
    The functions with which you are to build your RDT.
    -   recvfrom(bufsize)->bytes, addr
    -   sendto(bytes, address)
    -   bind(address)

    You can set the mode of the socket.
    -   settimeout(timeout)
    -   setblocking(flag)
    By default, a socket is created in the blocking mode.
    https://docs.python.org/3/library/socket.html#socket-timeouts

    """

    def __init__(self, rate=None, debug=True):
        super().__init__(rate=rate)
        self._rate = rate
        self._send_to = None
        self._recv_from = None
        self.debug = debug
        #############################################################################
        # TODO: ADD YOUR NECESSARY ATTRIBUTES HERE
        #############################################################################
        self.seq = 0  # base
        self.seq_ack = 0  # expected num
        self.next_seq = 0
        self.window = {}
        self.is_sender = False
        self.mutex = threading.Lock()
        self.timer = threading.Timer((TIME_OUT / 1000.0), self._timeout)
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def accept(self):
        """
        Accept a connection. The socket must be bound to an address and listening for
        connections. The return value is a pair (conn, address) where conn is a new
        socket object usable to send and receive data on the connection, and address
        is the address bound to the socket on the other end of the connection.

        This function should be blocking.
        """
        conn, addr = RDTSocket(self._rate), None
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################

        while True:
            # 接收对方发来的syn包

            data, addr = self.recvfrom(PACKET_SIZE)
            if data is None:
                continue
            p_syn, corrupt = unpack(data)
            if corrupt:
                continue
            if not p_syn.is_syn_set():
                continue
            if self.debug:
                print('handshake 1st')
                print('syn: ', p_syn.to_string())
                print('data =', data[:20])
                print('addr =', addr)

            # 更新seq_ack
            conn.seq_ack = p_syn.seq + 1

            # 第二次握手
            if self.debug:
                print('handshake 2st')
            conn.seq = random.randint(0x0001, 0xffff)
            if self.debug:
                conn.seq = 1
            syn_ack = RdtMessage(flags=0x0, seq=conn.seq, seq_ack=conn.seq_ack, syn=True, ack=True)
            self.sendto(syn_ack.to_byte(), addr)
            if self.debug:
                print('syn ack: ', syn_ack.to_string())

            # 接收ack
            if self.debug:
                print('handshake 3rd')
            while True:
                data, addr = self.recvfrom(PACKET_SIZE)
                if data is None:
                    continue
                p_ack, corrupt = unpack(data)
                if not p_ack.is_ack_set():
                    continue
                if self.debug:
                    print('ack: ', p_ack.to_string())

                conn.seq = p_ack.seq_ack
                conn.seq_ack = p_ack.seq + 1
                break

            conn._recv_from = conn._send_to = addr
            conn.next_seq = conn.seq = conn.seq
            if self.debug:
                print('seq =', conn.seq, 'seq_ack =', conn.seq_ack)
                print('handshake done')
            break

        #####
        myaddr = self.getsockname()
        self.close()
        conn.bind(myaddr)
        #####

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return conn, addr

    def connect(self, address: (str, int)):
        """
        Connect to a remote socket at address.
        Corresponds to the process of establishing a connection on the client side.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        # raise NotImplementedError()

        if self.debug:
            print('handshake 1st')
        # 构造syn包
        self.seq = random.randint(0x0001, 0xffff)
        if self.debug:
            self.seq = 1
        syn = RdtMessage(flags=0x0, seq=self.seq, seq_ack=0, syn=True)
        if self.debug:
            print('syn: ', syn.to_string())

        # 第一次握手, fin=1
        self.sendto(syn.to_byte(), address)

        # 接收对方发来的syn包，只有报文头
        if self.debug:
            print('handshake 2nd')
        data, addr = self.recvfrom(8 + HEADER_LENGTH)
        if data is None:
            print('warning: none')
        p_syn_ack, corrupt = unpack(data)
        if not (p_syn_ack.is_syn_set() and p_syn_ack.is_ack_set()):
            print('warning: bad')
        if self.debug:
            print('syn ack: ', p_syn_ack.to_string())
            print('data =', data)
            print('addr =', addr)

        # 拆包，更新序列号
        self.seq = p_syn_ack.seq_ack
        self.seq_ack = p_syn_ack.seq + 1
        # ?recv?

        # 第三次握手, ack=1
        if self.debug:
            print('handshake 3rd')
        ack = RdtMessage(flags=0x0, seq=self.seq, seq_ack=self.seq_ack, ack=True)
        if self.debug:
            print('ack: ', ack.to_string())
        self.sendto(ack.to_byte(), address)

        # 三次握手完成，client进入established状态
        self._send_to = self._recv_from = addr
        self.next_seq = self.seq = self.seq + 1
        # todo：超时重传

        if self.debug:
            print('seq =', self.seq, 'seq_ack =', self.seq_ack)
            print('handshake done')
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def _recv(self):
        data = None
        eof = None
        while True:
            packet, addr = self.recvfrom(PACKET_SIZE)
            # 判断来源，忽略其他主机的数据
            if not addr == self._recv_from:
                if self.debug:
                    print('someone else')
                continue
            # 解析
            msg, corrupt = unpack(packet)
            print('msg: ', msg.to_string(), 'corrupt: ', corrupt, '', 'expect: ', self.seq_ack)
            # 如果未受损且是期待的序号，则提交数据
            if not corrupt and msg.seq == self.seq_ack:
                # data = msg.payload[:min(msg.length, bufsize)]
                data = packet[8 + HEADER_LENGTH:]
                eof = msg.is_eof_set()
                ack = make_ack(self.seq_ack)
                print('make ack =', self.seq_ack)
                self.sendto(ack.to_byte(), self._send_to)
                self.seq_ack += 1
                break
            elif not corrupt and msg.is_fin_set():
                return None, None
            else:
                print('make ack =', self.seq_ack - 1)
                ack = make_ack(self.seq_ack - 1)
                self.sendto(ack.to_byte(), self._send_to)
        return data, eof

    def recv(self, bufsize: int) -> bytes:
        """
        Receive data from the socket.
        The return value is a bytes object representing the data received.
        The maximum amount of data to be received at once is specified by bufsize.

        Note that ONLY data send by the peer should be accepted.
        In other words, if someone else sends data to you from another address,
        it MUST NOT affect the data returned by this function.
        """
        data = None
        assert self._recv_from, "Connection not established yet. Use recvfrom instead."
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################

        buffer = bytes()
        while True:
            part, eof = self._recv()
            if part is None and eof is None:
                self.close()
                return None
            buffer += part
            if len(buffer) >= bufsize:
                data = buffer[:bufsize]
                break
            if eof:
                data = buffer
                break

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return data

    def _set_timer(self):
        if self.timer.is_alive():
            self.timer.cancel()

        timeout = self.gettimeout()
        if timeout is None:
            timeout = TIME_OUT
        self.timer = threading.Timer((timeout / 1000.0), self._timeout)
        self.timer.start()

    def _timeout(self):
        if self.debug:
            print('timeout')

        self.mutex.acquire()
        if self.seq < self.next_seq:
            print('resend (', self.seq, self.next_seq, ')')
            for i in range(self.seq, self.next_seq):
                packet = self.window[i]
                self.sendto(packet.to_byte(), self._send_to)
                print('resend packet: ', packet.to_string())
            self._set_timer()
        self.mutex.release()

    def _recv_ack(self):
        while self.is_sender:
            print('recv running')
            packet, addr = self.recvfrom(PACKET_SIZE)
            if not addr == self._recv_from:
                if self.debug:
                    print('someone else')
                continue
            msg, corrupt = unpack(packet)
            print('msg: ', msg.to_string(), 'corrupt: ', corrupt, 'base: ', self.seq, 'next seq: ', self.next_seq)
            if not corrupt and msg.is_ack_set() and msg.seq_ack >= self.seq:
                self.mutex.acquire()
                self.seq = msg.seq_ack + 1
                print('update seq =', self.seq, 'next seq =', self.next_seq)
                if self.seq == self.next_seq:
                    self.timer.cancel()
                else:
                    self._set_timer()
                self.mutex.release()

    def send(self, bytes: bytes):
        """
        Send data to the socket.
        The socket must be connected to a remote socket, i.e. self._send_to must not be none.
        """
        assert self._send_to, "Connection not established yet. Use sendto instead."
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        if self.debug:
            print('-------------')
            print('begin to send')
        self.is_sender = True
        threading.Thread(target=self._recv_ack).start()

        parts = make_data_parts(bytes, PAYLOAD_SIZE)
        if self.debug:
            print('get', len(parts))
        for part in parts:
            while True:
                self.mutex.acquire()
                # if self.debug:
                #     print('seq =', self.seq, 'next_seq =', self.next_seq)
                if self.next_seq < self.seq + WINDOW_SIZE:
                    packet = RdtMessage(0x0, self.next_seq, 0, payload=part.decode(), eof=(part == parts[-1]))
                    self.window[self.next_seq] = packet
                    self.sendto(packet.to_byte(), self._send_to)
                    if self.debug:
                        print('send pkt: ', packet.to_string())
                    if self.seq == self.next_seq:
                        self._set_timer()
                    self.next_seq += 1
                    self.mutex.release()
                    break
                else:
                    self.mutex.release()
                    time.sleep(1)

        while True:
            self.mutex.acquire()
            if self.seq == self.next_seq:
                self.is_sender = False
                self.mutex.release()
                break
            self.mutex.release()
            time.sleep(1)

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def close(self):
        """
        Finish the connection and release resources. For simplicity, assume that
        after a socket is closed, neither futher sends nor receives are allowed.
        """
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################
        if self._send_to:
            fin = RdtMessage(0x0, self.seq, self.seq_ack, fin=True)
            self.sendto(fin.to_byte(), self._send_to)
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        super().close()

    def set_send_to(self, send_to):
        self._send_to = send_to

    def set_recv_from(self, recv_from):
        self._recv_from = recv_from


"""
You can define additional functions and classes to do thing such as packing/unpacking packets, or threading.

"""

