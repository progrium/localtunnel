def encode_data_packet(conn_id, data):
    return ''.join([chr(conn_id), data])

def decode_data_packet(data):
    return data[0], str(data[1:])