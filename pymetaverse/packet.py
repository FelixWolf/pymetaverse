#!/usr/bin/env python3
import struct
import io

# https://wiki.secondlife.com/wiki/Packet_Layout
"""
 +-+-+-+-+----+--------+--------+--------+--------+--------+-----...-----+
 |Z|R|R|A|    |                                   |        |  Extra      |
 |E|E|E|C|    |    Sequence number (4 bytes)      | Extra  |  Header     |
 |R|L|S|K|    |                                   | (byte) | (N bytes)   |
 +-+-+-+-+----+--------+--------+--------+--------+--------+-----...-----+
"""

def zeroEncode(buf):
    output = io.BytesIO()
    count = None
    i = 0
    l = len(buf)
    count = 0
    while i < l:
        if buf[i] == 0:
            count = 0
            while i < l and buf[i] == 0:
                count += 1
                i += 1
                if count == 255:
                    output.write(bytes([0, 0xFF]))
                    count = 0
            if count != 0:
                output.write(bytes([0, count]))
        if i < l:
            output.write(bytes([buf[i]]))
        i += 1
    
    return output.getvalue()

def zeroDecode(buf):
    output = io.BytesIO()
    count = None
    i = 0
    l = len(buf)
    while i < l:
        if buf[i] == 0:
            i += 1
            output.write(bytes(buf[i]))
        else:
            output.write(bytes([buf[i]]))
        i += 1
    
    return output.getvalue()

class Packet:
    MTU = 1400
    
    sPacketHeader = struct.Struct(">BIB")
    sPacketAcks = struct.Struct(">I")
    
    class FLAGS:
        ZEROCODE = 0x80
        RELIABLE = 0x40
        RESENT = 0x20
        ACK = 0x10
    
    def __init__(self, seq, body = None, flags = None, acks = None, extra = None):
        self.sequence = seq
        self.flags = flags or 0
        self.extra = extra or b""
        self.body = body or b""
        self.acks = acks or []
    
    @property
    def reliable(self):
        return bool(self.flags & self.FLAGS.RELIABLE)

    @reliable.setter
    def reliable(self, value):
        if value:
            self.flags |= self.FLAGS.RELIABLE
        else:
            self.flags &= ~self.FLAGS.RELIABLE

    @property
    def resent(self):
        return bool(self.flags & self.FLAGS.RESENT)

    @resent.setter
    def resent(self, value):
        if value:
            self.flags |= self.FLAGS.RESENT
        else:
            self.flags &= ~self.FLAGS.RESENT

    @property
    def zerocode(self):
        return bool(self.flags & self.FLAGS.ZEROCODE)

    @zerocode.setter
    def zerocode(self, value):
        if value:
            self.flags |= self.FLAGS.ZEROCODE
        else:
            self.flags &= ~self.FLAGS.ZEROCODE
    
    def toBytes(self):
        output = io.BytesIO()
        flags = self.flags
        if len(self.acks) > 0:
            flags = flags | self.FLAGS.ACK
        
        output.write(self.sPacketHeader.pack(flags, self.sequence, len(self.extra)))
        output.write(self.extra)
        
        if flags & self.FLAGS.ZEROCODE:
            output.write(zeroEncode(self.body))
        else:
            output.write(self.body)
        
        if flags & self.FLAGS.ACK:
            count = 0
            while len(self.acks):
                size = output.tell()
                if size - 5 >= self.MTU:
                    break
                
                if count >= 255:
                    break
                
                output.write(self.sPacketAcks.pack(self.acks.pop(0)))
                count += 1
            
            output.write(bytes([count]))
        
        return output.getvalue()
    
    def __bytes__(self):
        return self.toByte()
    
    @classmethod
    def fromBytes(cls, data):
        return cls.fromStream(io.BytesIO(data))
    
    @classmethod
    def fromStream(cls, f):
        flags, seq, extra = cls.sPacketHeader.unpack_from(f.read(cls.sPacketHeader.size))
        
        if extra > 0:
            extra = f.read(extra)
        else:
            extra = b""
        
        bodyStart = f.tell()
        
        body = None
        acks = []
        if flags & cls.FLAGS.ACK:
            f.seek(-1, io.SEEK_END)
            ackCount, = f.read(1)
            
            f.seek(-(ackCount * cls.sPacketAcks.size) - 1, io.SEEK_END)
            
            bodyEnd = f.tell()
            
            acks = [None] * ackCount
            for i in range(ackCount):
                acks[i], = cls.sPacketAcks.unpack(f.read(cls.sPacketAcks.size))
            
            f.seek(bodyStart)
            body = f.read(bodyEnd - bodyStart)
            
        else:
            body = f.read()
        
        if flags & cls.FLAGS.ZEROCODE:
            body = zeroDecode(body)
        
        return cls(seq, body, flags = flags, acks = acks, extra = extra)
    
    @classmethod
    def fromBytes(cls, data):
        return cls.fromStream(io.BytesIO(data))
    
