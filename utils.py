
def calc_checksum(payload):
    sum = 0
    for byte in payload:
        sum += byte
    sum = -(sum % 256)
    return sum & 0xFF


def make_data_parts(data, part_size):
    parts = []
    total = len(data)
    curr = 0

    while curr < total:
        part = data[curr:min(total, curr + part_size)]
        parts.append(part)
        curr += part_size

    return parts

