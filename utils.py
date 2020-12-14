

def calc_checksum(payload):
    sum = 0
    for byte in payload:
        sum += byte
    sum = -(sum % 256)
    return sum & 0xFF
