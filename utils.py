
def calc_checksum(payload):
    sum = 0
    for i in range(len(payload)):
        byte = payload[i]
        if i % 2 == 0:
            sum += (byte << 8)
        else:
            sum += byte
    sum = -(sum % 65536)
    return sum & 0xFFFF


def make_data_parts(data, part_size):
    parts = []
    total = len(data)
    curr = 0

    while curr < total:
        part = data[curr:min(total, curr + part_size)]
        parts.append(part)
        curr += part_size

    return parts

