

import json
import struct


class Packet:

    def __init__(self, ack_num, seq, rwnd, length, flags=None, data=None) -> None:
        self.ack_num = ack_num
        self.seq = seq
        self.rwnd = rwnd
        self.flags = flags
        self.data = data
        self.length = length

    def __dict__(self):
        return {
            'ack_num': self.ack_num,
            'seq': self.seq,
            'rwnd': self.rwnd,
            'flags': self.flags,
            'data': self.data,
            'length': self.length
        }

    def __str__(self) -> str:
        return json.dumps(self.__dict__())

    def __repr__(self) -> str:
        return self.__str__

    def to_json(self):
        return json.dumps(self.__dict__())




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

    def pack(self):
        
        if self.data is None:
            self.datalength = 0
            return struct.pack("IIIIII" ,self.version, self.type, self.seqnum, self.datalength, self.ack_num , self.content_len)
        else:
            data = bytes(self.data)
            self.datalength = len(data)
            return struct.pack("IIIIII%ds" % len(data), self.version, self.type, self.seqnum, self.datalength, self.ack_num,self.content_len, data)

    def unpack(self, data):
        self.version, self.type, self.seqnum, self.datalength, self.ack_num,self.content_len = struct.unpack(
            "IIIIII", data[:24])
        if self.datalength > 0:
            (self.data,) = struct.unpack("%ds" % (self.datalength,), data[24:])
        return self

    def __str__(self):  # Override string representation
        return "RudpPacket " + str(self.__dict__)


