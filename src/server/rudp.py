import struct


class RudpPacket:
    """ RUDP packet class"""
    TYPE_DATA = 1
    TYPE_SYN = 2
    TYPE_SYN_ACK = 3
    TYPE_ACK = 4
    TYPE_NACK = 5
    TYPE_FIN = 6
    TYPE_FINACK = 7

    #
    # Feilds:
    # vesion:
    # length
    # sequence number
    #
    #
    def __init__(self):
        self.version = 1
        self.type = None
        self.seqnum = 0
        self.datalength = None
        self.data = None
        self.ack_num = 0
        self.content_len = 0
        self.recv_wnd = 0
        self.check_sum = 0
        self.is_sent = False

    def __str__(self):
        return f'{{ seq : {self.seqnum} , ack_num :{self.ack_num}}}'

    def __repr__(self):
        return f'{{ seq : {self.seqnum} , ack_num :{self.ack_num}}}'

    def add_check_sum(self, bytes):
        total = 0
        for bit in bytes:
            total += bit
        self.check_sum = total

    def is_valid(self):
        if self.data is None:
            return True

        total = 0
        for bit in self.data:
            total += bit
        return total == self.check_sum

    def pack(self):

        if self.data is None:
            self.datalength = 0
            return struct.pack("IIIIIIII", self.version, self.type, self.seqnum, self.datalength, self.ack_num,
                               self.content_len, self.recv_wnd, self.check_sum)
        else:
            data = bytes(self.data)
            self.datalength = len(data)
            self.add_check_sum(data)
            return struct.pack("IIIIIIII%ds" % len(data), self.version, self.type, self.seqnum, self.datalength,
                               self.ack_num, self.content_len, self.recv_wnd, self.check_sum, data)

    def unpack(self, data):
        self.version, self.type, self.seqnum, self.datalength, self.ack_num, self.content_len, self.recv_wnd, self.check_sum = struct.unpack(
            "IIIIIIII", data[:32])
        if self.datalength > 0:
            (self.data,) = struct.unpack("%ds" % (self.datalength,), data[32:])
        return self
