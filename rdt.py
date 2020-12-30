import datetime

from USocket import UnreliableSocket
from rdt_message import HEADER_LENGTH, RdtMessage, unpack, make_ack
from utils import make_data_parts
import threading
import time
import random

PAYLOAD_SIZE = 2048
PACKET_SIZE = 8 + HEADER_LENGTH + PAYLOAD_SIZE
MIN_WINDOW = 2


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

    def __init__(self, rate=None, debug=False):
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

        self.tx_buffer = []
        self.send_buffer = []
        self.recv_buffer = []
        # self.sr_buffer = []
        self.rx_buffer = []
        self.recv_num = 5
        self.tx_thread = threading.Thread(target=self.tx_function)
        self.send_thread = threading.Thread(target=self.send_function)
        self.recv_thread = threading.Thread(target=self.recv_function)
        self.rx_thread = threading.Thread(target=self.rx_function)
        self.thread_list = [self.tx_thread, self.send_thread, self.rx_thread, self.recv_thread]
        self.acked_send_message = {}
        self.acked_recv_message = {}
        self.connected = False
        self.closed = False

        self.is_sender = False
        self.mutex = threading.Lock()
        self.con_timer = None
        self.timer_list = {}

        self.time_out = 3000
        self.window_size = MIN_WINDOW
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def accept(self) -> ('RDTSocket', (str, int)):
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

        # 接收对方发来的syn包
        while True:
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
            break

        conn._recv_from = conn._send_to = addr
        self._recv_from = self._send_to = addr

        # 更新seq_ack
        conn.seq_ack = p_syn.seq + 1

        # 第二次握手
        if self.debug:
            print('handshake 2nd')
        # conn.seq = random.randint(0x0001, 0xffff)
        # if self.debug:
        conn.seq = 1
        syn_ack = RdtMessage(flags=0x0, seq=conn.seq, seq_ack=conn.seq_ack, syn=True, ack=True)
        if self.debug:
            print('syn ack: ', syn_ack.to_string())

        self.window['syn_ack'] = syn_ack.to_byte()
        self.sendto(syn_ack.to_byte(), addr)
        self.set_connect_timer(type='syn_ack')

        # 接收ack
        if self.debug:
            print('handshake 3rd')
        while True:
            data, addr = self.recvfrom(PACKET_SIZE)
            if data is None:
                continue
            p_ack, corrupt = unpack(data)
            if corrupt:
                continue
            if not p_ack.is_ack_set():
                if p_ack.seq_ack < 2:
                    continue
            if self.debug:
                print('ack: ', p_ack.to_string())
            if self.con_timer.is_alive():
                self.con_timer.cancel()

            conn.seq = p_ack.seq_ack
            conn.seq_ack = p_ack.seq + 1
            break

        conn.next_seq = conn.seq = conn.seq
        if self.debug:
            print('seq =', conn.seq, 'seq_ack =', conn.seq_ack)
            print('handshake done')

        #####
        myaddr = self.getsockname()
        self.close()
        conn.bind(myaddr)

        conn.rx_thread.start()
        conn.recv_thread.start()
        conn.send_thread.start()
        conn.tx_thread.start()
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

        # 提前连上
        self._send_to = self._recv_from = address

        if self.debug:
            print('handshake 1st')
        # 构造syn包
        self.seq = random.randint(0x0001, 0xffff)
        if self.debug:
            self.seq = 1
        syn = RdtMessage(flags=0x0, seq=self.seq, seq_ack=0, syn=True)
        if self.debug:
            print('syn: ', syn.to_string())

        # 第一次握手, syn=1
        self.window['syn'] = syn.to_byte()
        self.sendto(syn.to_byte(), address)
        self.set_connect_timer(type='syn')

        # 接收对方发来的syn包，只有报文头
        if self.debug:
            print('handshake 2nd')
        while True:
            data, addr = self.recvfrom(8 + HEADER_LENGTH)
            if data is None:
                print('warning: none')
            p_syn_ack, corrupt = unpack(data)
            if corrupt:
                print('Waring: corrupt packet recv')
                continue
            if not (p_syn_ack.is_syn_set() and p_syn_ack.is_ack_set()):
                print('warning: bad')
                continue
            else:
                if self.con_timer.is_alive():
                    self.con_timer.cancel()
                if self.debug:
                    print('syn ack: ', p_syn_ack.to_string())
                    print('data =', data)
                    print('addr =', addr)
                break

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

        self.window['ack'] = ack.to_byte()
        self.sendto(ack.to_byte(), addr)
        self.set_connect_timer(type='ack')

        # 三次握手完成，client进入established状态
        self.next_seq = self.seq = self.seq + 1
        # todo：超时重传

        if self.debug:
            print('seq =', self.seq, 'seq_ack =', self.seq_ack)
            print('handshake done, start Tx Thread')

        self.rx_thread.start()
        self.recv_thread.start()
        self.send_thread.start()
        self.tx_thread.start()
        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################

    def set_connect_timer(self, type):
        timeout = self.gettimeout()
        if timeout is None:
            timeout = self.time_out
        self.con_timer = threading.Timer((timeout / 1000.0), self.connect_timeout, args=[type])
        self.con_timer.start()

    def connect_timeout(self, type):
        if type == 'syn':
            print('resend syn')
            self.mutex.acquire()
            packet = self.window['syn']
            self.mutex.release()
        elif type == 'syn_ack':
            print('resend syn_ack')
            self.mutex.acquire()
            packet = self.window['syn_ack']
            self.mutex.release()
        else:
            print('resend ack')
            self.mutex.acquire()
            packet = self.window['ack']
            self.mutex.release()
        self.sendto(packet, self._send_to)
        self.set_connect_timer(type)

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

        data = bytes()
        self.mutex.acquire()
        waited = False
        while True:
            # if self.debug:
            #     print("recv...")
            if len(self.rx_buffer) != 0 and len(data) + len(self.rx_buffer[0]) <= bufsize:
                raw, eof = self.rx_buffer.pop(0)
                data += raw.encode()
                if eof:
                    break
            elif len(self.rx_buffer) != 0 and len(data) + len(self.rx_buffer[0]) > bufsize:
                break
            elif len(self.rx_buffer) == 0:
                if data:
                    if waited:
                        break
                    else:
                        self.mutex.release()
                        time.sleep(0.005)
                        self.mutex.acquire()
                        waited = True
                else:
                    self.mutex.release()
                    time.sleep(0.005)
                    self.mutex.acquire()
        self.mutex.release()

        #############################################################################
        #                             END OF YOUR CODE                              #
        #############################################################################
        return data

    def _timeout(self, cur_seq):
        if self.debug:
            print('timeout on', cur_seq)
            # print(self.seq, self.next_seq)
            print('resend (', cur_seq, ')', 'at', datetime.datetime.now())
        self.mutex.acquire()
        self.window_size = max(MIN_WINDOW, self.window_size * 0.5)
        data = self.window[cur_seq][0]
        packet = RdtMessage(flags=0x0, seq=cur_seq, seq_ack=self.seq_ack, payload=data.decode())
        self.mutex.release()
        self.sendto(packet.to_byte(), self._send_to)
        if self.debug:
            print('resend packet: ', packet.to_string())
        if self.timer_list[cur_seq].is_alive():
            self.timer_list[cur_seq].cancel()
        timeout = self.gettimeout()
        if timeout is None:
            timeout = self.time_out
        self.timer_list[cur_seq] = threading.Timer((timeout / 1000.0), self._timeout, args=[cur_seq])
        self.timer_list[cur_seq].start()

    def send(self, bytes: bytes):
        """
        Send data to the socket.
        The socket must be connected to a remote socket, i.e. self._send_to must not be none.
        """
        assert self._send_to, "Connection not established yet. Use sendto instead."
        #############################################################################
        # TODO: YOUR CODE HERE                                                      #
        #############################################################################

        parts = make_data_parts(bytes, PAYLOAD_SIZE)
        for part in parts:
            if part == parts[-1]:
                self.tx_buffer.append((part, True))
            else:
                self.tx_buffer.append((part, False))
        if self.debug:
            print("put the data into the tx buffer")
            print("in", len(parts), "parts")

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

        while True:
            time.sleep(0.01)
            self.mutex.acquire()
            if len(self.tx_buffer) == 0 and len(self.send_buffer) == 0:
                self.closed = True
                self.mutex.release()
                break
            self.mutex.release()
        for t in self.thread_list:
            if t.is_alive():
                t.join(timeout=0.05)
        for i in range(20):
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

    # a thread for all packing logic
    def tx_function(self):
        self.mutex.acquire()
        self.next_seq = self.seq = 5
        self.mutex.release()
        if self.debug:
            print("Tx thread start")
        while True:
            if self.closed:
                break
            time.sleep(0.001)
            if len(self.tx_buffer) > 0:
                if self.next_seq < self.seq + self.window_size:
                    if self.debug:
                        print("data get from tx_buffer")
                    self.mutex.acquire()
                    data, eof = self.tx_buffer.pop(0)
                    self.window[self.next_seq] = (data, time.time())
                    self.mutex.release()
                    packet = RdtMessage(0x0, self.next_seq, self.seq_ack, payload=data.decode(), eof=eof)
                    self.mutex.acquire()
                    timeout = self.gettimeout()
                    if timeout is None:
                        timeout = self.time_out
                    self.timer_list[self.next_seq] = threading.Timer((timeout / 1000.0), self._timeout, args=[self.next_seq])
                    self.timer_list[self.next_seq].start()
                    self.send_buffer.append(packet)
                    self.next_seq += 1
                    self.mutex.release()
            # here I should not send empty packet
            # else:
            #     packet = RdtMessage(0x0, self.next_seq-1, self.seq_ack)
            #     self.mutex.acquire()
            #     self.send_buffer.append(packet)
            #     self.mutex.release()
        if self.debug:
            print("Tx thread end")

    # a thread for sending packets
    def send_function(self):
        if self.debug:
            print("Send thread start")
        while True:
            if self.closed:
                break
            time.sleep(0.001)
            if len(self.send_buffer) > 0:
                if self.debug:
                    print("data get from send_buffer")
                self.mutex.acquire()
                packet = self.send_buffer.pop(0)
                self.mutex.release()
                self.sendto(packet.to_byte(), self._send_to)

        if self.debug:
            print("Send thread end")

    # a thread for receiving packet
    def recv_function(self):
        if self.debug:
            print("Recv thread start")
        while True:
            if self.closed:
                break
            time.sleep(0.001)
            try:
                packet, addr = self.recvfrom(PACKET_SIZE)
            except:
                if self.debug:
                    print("Recv thread forced end")
                break
            if packet:
                if self.debug:
                    print("data get from some host")
                if not addr == self._recv_from:
                    if self.debug:
                        print('recv packet from unknown host, aborted')
                    continue
                self.mutex.acquire()
                self.recv_buffer.append(packet)
                self.mutex.release()

        if self.debug:
            print("Recv thread end")

    # a thread for all unpacking logic
    def rx_function(self):
        if self.debug:
            print("Rx thread start")
        while True:
            if self.closed:
                break
            time.sleep(0.001)
            if len(self.recv_buffer) > 0:
                if self.debug:
                    print("data get from recv_buffer")
                self.mutex.acquire()
                packet = self.recv_buffer.pop(0)
                self.window_size += 1 / self.window_size / 8
                print(self.window_size)
                self.mutex.release()
                msg, corrupt = unpack(packet)
                if corrupt:
                    continue
                if msg.is_fin_set():
                    self.mutex.acquire()
                    for timer in self.timer_list:
                        try:
                            if timer.is_alive():
                                timer.cancel()
                        except:
                            continue
                    self.mutex.release()
                if msg.is_ack_set():
                    self.mutex.acquire()
                    try:
                        self.acked_send_message[msg.seq_ack]
                    except KeyError:
                        RTT = (time.time() - self.window[msg.seq_ack][1]) * 1000
                        print("current rtt is ", RTT)
                        self.time_out = self.time_out * 0.75 + RTT * 0.25
                        self.time_out = min(self.time_out, 6000)
                        self.time_out = max(self.time_out, 3000)
                        print("current time out is", self.time_out)
                    self.acked_send_message[msg.seq_ack] = True
                    while True:
                        try:
                            if self.acked_send_message[self.seq]:
                                self.seq += 1
                        except KeyError:
                            break
                    if self.timer_list[msg.seq_ack].is_alive():
                        self.timer_list[msg.seq_ack].cancel()
                    # handle the third handshake
                    if self.con_timer and self.con_timer.is_alive() and msg.seq_ack > 2:
                        self.con_timer.cancel()
                    self.mutex.release()
                else:
                    data = msg.payload  # window size has been taken out! not 8+HEADER_LENGTH
                    eof = msg.is_eof_set()

                    self.acked_send_message[msg.seq_ack] = True
                    while True:
                        time.sleep(0.001)
                        self.mutex.acquire()
                        try:
                            if self.acked_send_message[self.seq]:
                                self.seq += 1
                        except KeyError:
                            break
                        finally:
                            self.mutex.release()
                    self.mutex.acquire()
                    try:
                        if self.timer_list[msg.seq_ack].is_alive():
                            self.timer_list[msg.seq_ack].cancel()
                    except KeyError:
                        pass
                    self.mutex.release()
                    seq_ack = -1
                    if len(data) > 0:
                        self.mutex.acquire()
                        try:
                            if self.acked_recv_message[msg.seq]:
                                self.window_size = max(MIN_WINDOW, self.window_size * 0.8)
                            else:
                                self.acked_recv_message[msg.seq] = (data, eof)
                        except KeyError:
                            self.acked_recv_message[msg.seq] = (data, eof)
                        finally:
                            self.mutex.release()
                        seq_ack = msg.seq
                        if seq_ack == self.recv_num:
                            while True:
                                time.sleep(0.001)
                                self.mutex.acquire()
                                try:
                                    self.rx_buffer.append(self.acked_recv_message[self.recv_num])
                                    self.recv_num += 1
                                except KeyError:
                                    break
                                finally:
                                    self.mutex.release()

                    # if there's no sending data now, just tell him I got it
                    # if len(self.send_buffer) == 0 and len(self.tx_buffer) == 0 and seq_ack != -1:
                    if seq_ack != -1:
                        packet = RdtMessage(0x0, 1, seq_ack, ack=True)
                        self.sendto(packet.to_byte(), self._send_to)

        if self.debug:
            print("Rx thread end")


"""
You can define additional functions and classes to do thing such as packing/unpacking packets, or threading.

"""
