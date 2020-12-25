import struct
from utils import calc_checksum

# rdt_format is for the struct package to split the bytes easily
rdt_format = '!BLLLB'
HEADER_LENGTH = 14


class RdtMessage(object):
    def __init__(self, flags, seq, seq_ack, length=-1, checksum=-1, payload="", eof=False, syn=False, fin=False, ack=False):

        """
        constructor of RdtMessage
        :param flags: 5 bits reserved, 1 bit syn, 1 bit fin, 1 bit ack, 1 byte
        :param seq: sequence number, 4 bytes
        :param seq_ack: ack number, 4 bytes
        :param checksum: checksum, 1 byte
        :param payload: data to be transfer, LEN bytes (string)
        :returns RdtMessage
        """
        self.flags = flags
        if syn:
            self.set_syn()
        if fin:
            self.set_fin()
        if ack:
            self.set_ack()
        if eof:
            self.set_eof()
        self.seq = seq
        self.seq_ack = seq_ack
        self.payload = payload
        self.length = len(payload) if length == -1 else length
        if checksum != -1:
            self.checksum = checksum
        self.checksum = calc_checksum(struct.pack(rdt_format, self.flags, seq, seq_ack, self.length, 0) + payload.encode())

    def to_byte(self):
        """
        turn the message to bytes
        :return: bytes
        """
        # print('packing: ', self.flags, self.seq, self.seq_ack, self.length, self.checksum)
        # print('payload: ', self.payload)
        return struct.pack(rdt_format, self.flags, self.seq, self.seq_ack, self.length, self.checksum) + self.payload.encode()

    def is_eof_set(self):
        return self.flags & 0b1000 != 0

    def is_syn_set(self):
        return self.flags & 0b0100 != 0

    def is_fin_set(self):
        return self.flags & 0b0010 != 0

    def is_ack_set(self):
        return self.flags & 0b0001 != 0

    def set_eof(self):
        self.flags |= 0b1000

    def set_syn(self):
        self.flags |= 0b0100

    def set_fin(self):
        self.flags |= 0b0010

    def set_ack(self):
        self.flags |= 0b0001

    def to_string(self):
        return 'eof={7}, syn={0}, fin={1}, ack={2}, seq={3}, seq_ack={4}, len={5}, checksum={6}'.format(
            self.is_syn_set(), self.is_fin_set(), self.is_ack_set(), self.seq, self.seq_ack,self.length, self.checksum, self.is_eof_set()
        )


def unpack(bytes_message: bytes):
    """
    unpack receiving message to RdtMessage object
    :param bytes_message: bytes, origin message
    :return: RdtMessage
    :return: corrupt: bool, is message corrupted
    """
    flags, seq, seq_ack, length, checksum = struct.unpack(rdt_format, bytes_message[0:HEADER_LENGTH])
    # print('unpacked:', flags, seq, seq_ack, length, checksum)
    # assert flags < 6

    real_checksum = calc_checksum(struct.pack(rdt_format, flags, seq, seq_ack, length, 0) + bytes_message[HEADER_LENGTH:])
    # assert checksum == real_checksum
    corrupt = not checksum == real_checksum

    if corrupt:
        return RdtMessage(0, 0, 0), corrupt
    else:
        payload = bytes_message[HEADER_LENGTH:].decode()
        # print('payload:', payload)
        # assert len(payload) == length
        return RdtMessage(flags, seq, seq_ack, length, checksum, payload), corrupt


def make_ack(seq_ack):
    return RdtMessage(0x0, 0, seq_ack, ack=True)

# this is just for testing
if __name__ == "__main__":
    b = b'\x04\x00\x00\x00\x10\x00\x00\x00\x11\x00\x00\x00\x05\x62\x48\x45\x4c\x4c\x4f'
    packet = unpack(b)
    if packet.is_syn_set():
        print("syn set")
    if packet.is_ack_set():
        print("ack set")
    if packet.is_fin_set():
        print("fin set")
