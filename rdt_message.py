import struct
from utils import calc_checksum

# rdt_format is for the struct package to split the bytes easily
rdt_format = '!BLLLB'
HEADER_LENGTH = 14


def unpack(bytes_message: bytes):
    """
    unpack receiving message to RdtMessage object
    :param bytes_message: bytes, origin message
    :return: RdtMessage
    """
    flags, seq, seq_ack, length, checksum = struct.unpack(rdt_format, bytes_message[0:HEADER_LENGTH])
    print(flags, seq, seq_ack, length, checksum)
    assert flags < 6

    payload = b[HEADER_LENGTH:].decode()
    print(payload)
    assert len(payload) == length

    real_checksum = calc_checksum(struct.pack(rdt_format, flags, seq, seq_ack, length, 0) + b[HEADER_LENGTH:])
    print(real_checksum)
    assert checksum == real_checksum

    return RdtMessage(flags, seq, seq_ack, length, checksum, payload)


class RdtMessage(object):

    def __init__(self, flags, seq, seq_ack, length=-1, checksum=-1, payload=""):
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
        self.seq = seq
        self.seq_ack = seq_ack
        self.payload = payload
        self.length = len(payload) if length == -1 else length
        if checksum != -1:
            self.checksum = checksum
        self.checksum = calc_checksum(struct.pack(rdt_format, flags, seq, seq_ack, self.length, 0) + b[HEADER_LENGTH:])

    def to_byte(self):
        """
        turn the message to bytes
        :return: bytes
        """
        return struct.pack(rdt_format, self.flags, self.seq, self.seq_ack, self.length, self.checksum) + b[HEADER_LENGTH:]

    def is_syn_set(self):
        return self.flags & 0b100 != 0

    def is_fin_set(self):
        return self.flags & 0b010 != 0

    def is_ack_set(self):
        return self.flags & 0b001 != 0


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
