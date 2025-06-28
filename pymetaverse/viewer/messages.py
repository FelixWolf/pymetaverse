#!/usr/bin/env python3
from collections import OrderedDict
from enum import Enum, auto
import ipaddress
import uuid
import struct
import io
import os

# These are shared in various places around the code
sUInt32 = struct.Struct(">I")
sUInt16 = struct.Struct(">H")
sUInt8 = struct.Struct(">B")

def ZeroEncode(buf):
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

def ZeroDecode(buf):
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


class Block:
    class TYPE(Enum):
        NULL = auto()
        FIXED = auto()
        VARIABLE = auto()
        U8 = auto()
        U16 = auto()
        U32 = auto()
        U64 = auto()
        S8 = auto()
        S16 = auto()
        S32 = auto()
        S64 = auto()
        F32 = auto()
        F64 = auto()
        LLVECTOR3 = auto()
        LLVECTOR3D = auto()
        LLVECTOR4 = auto()
        LLQUATERNION = auto()
        LLUUID = auto()
        BOOL = auto()
        IPADDR = auto()
        IPPORT = auto()
        
        #Unused
        U16VEC3 = auto()
        U16QUAT = auto()
        S16ARRAY = auto()
    
    # LL couldn't decide which endianness to use. The different endianness
    # is intentional.
    sVariable1 = struct.Struct("<B")
    sVariable2 = struct.Struct("<H")
    sU8 = struct.Struct("<B")
    sU16 = struct.Struct("<H")
    sU32 = struct.Struct("<I")
    sU64 = struct.Struct("<Q")
    sS8 = struct.Struct("<b")
    sS16 = struct.Struct("<h")
    sS32 = struct.Struct("<i")
    sS64 = struct.Struct("<q")
    sF32 = struct.Struct("<f")
    sF64 = struct.Struct("<d")
    sLLVector3 = struct.Struct("<fff")
    sLLVector3d = struct.Struct("<ddd")
    sLLVector4 = struct.Struct("<ffff")
    
    def __init__(self, name):
        super().__setattr__('name', name)
        super().__setattr__('parameters', OrderedDict())
        super().__setattr__('values', {})
    
    def __repr__(self):
        return f"<{self.__class__.__name__} {self.name}>"
    
    def __getattr__(self, name):
        if name in self.parameters:
            return self.values.get(name)  # Fix incorrect variable name
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name in self.parameters:
            self.values[name] = value  # Fix incorrect variable name
        else:
            super().__setattr__(name, value)  # Prevent infinite recursion
    
    def __bytes__(self):
        res = io.BytesIO()
        self.toStream(res)
        return res.getvalue()
    
    def toStream(self, handle):
        for name, (dType, size) in self.parameters.items():
            if dType == self.TYPE.NULL:
                pass
            
            elif dType == self.TYPE.FIXED:
                data = self.values.get(name, b"")[:size]
                handle.write(data.ljust(size, b'\x00'))
            
            elif dType == self.TYPE.VARIABLE:
                if size == 1:
                    data = self.values.get(name, b"")[:255]
                    handle.write(self.sVariable1.pack(len(data)))
                    handle.write(data)
                    
                elif size == 2:
                    data = self.values.get(name, b"")[:65535]
                    handle.write(self.sVariable2.pack(len(data)))
                    handle.write(data)
                    
                else:
                    raise Exception("Invalid variable size {}".format(size))
            
            elif dType == self.TYPE.U8:
                handle.write(self.sU8.pack(int(self.values.get(name, 0) or 0)))
            
            elif dType == self.TYPE.U16:
                handle.write(self.sU16.pack(int(self.values.get(name, 0) or 0)))
            
            elif dType == self.TYPE.U32:
                handle.write(self.sU32.pack(int(self.values.get(name, 0) or 0)))
            
            elif dType == self.TYPE.U64:
                handle.write(self.sU64.pack(int(self.values.get(name, 0) or 0)))
            
            elif dType == self.TYPE.S8:
                handle.write(self.sS8.pack(int(self.values.get(name, 0) or 0)))
            
            elif dType == self.TYPE.S16:
                handle.write(self.sS16.pack(int(self.values.get(name, 0) or 0)))
            
            elif dType == self.TYPE.S32:
                handle.write(self.sS32.pack(int(self.values.get(name, 0) or 0)))
            
            elif dType == self.TYPE.S64:
                handle.write(self.sS64.pack(int(self.values.get(name, 0) or 0)))
            
            elif dType == self.TYPE.F32:
                handle.write(self.sF32.pack(float(self.values.get(name, 0) or 0)))
                
            elif dType == self.TYPE.F64:
                handle.write(self.sF64.pack(float(self.values.get(name, 0) or 0)))
            
            elif dType == self.TYPE.LLVECTOR3:
                vec = self.values.get(name, (0,0,0)) or (0,0,0)
                handle.write(self.sLLVector3.pack(vec[0], vec[1], vec[2]))
            
            elif dType == self.TYPE.LLVECTOR3D:
                vec = self.values.get(name, (0,0,0)) or (0,0,0)
                handle.write(self.sLLVector3d.pack(vec[0], vec[1], vec[2]))
            
            elif dType == self.TYPE.LLVECTOR4:
                vec = self.values.get(name, (0,0,0,0)) or (0,0,0,0)
                handle.write(self.sLLVector4.pack(vec[0], vec[1], vec[2], vec[3]))
            
            elif dType == self.TYPE.LLQUATERNION:
                vec = self.values.get(name, (0,0,0)) or (0,0,0)
                # NOTE: Quaternions are transmitted as vectors. The W component
                # is missing and is just generated on the fly.
                handle.write(self.sLLVector3.pack(vec[0], vec[1], vec[2]))
            
            elif dType == self.TYPE.LLUUID:
                value = self.values.get(name, "00000000-0000-0000-0000-000000000000") or "00000000-0000-0000-0000-000000000000"
                if type(value) == str:
                    value = uuid.UUID(value)
                handle.write(value.bytes)
            
            elif dType == self.TYPE.BOOL:
                handle.write(b"\1" if bool(self.values.get(name, False) or False) else b"\0")
            
            # NOTE: IPADDR AND IPPORT USE THE BIG ENDIAN sUInt32 AND sUInt16
            # THESE ARE NOT FROM THE MESSAGE CLASS, THEY ARE FROM THE GLOBAL SCOPE!
            # IT IS INTENTIONAL!
            elif dType == self.TYPE.IPADDR:
                handle.write(sUInt32.pack(int(ipaddress.IPv4Address(self.values.get(name, "0.0.0.0") or "0.0.0.0"))))
            
            elif dType == self.TYPE.IPPORT:
                handle.write(sUInt16.pack(int(self.values.get(name, 0) or 0)&0xFFFF))
            
            else:
                raise Exception("Unknown type {}".format(dType))
    
    def fromStream(self, handle):
        for name, (dType, size) in self.parameters.items():
            if dType == self.TYPE.NULL:
                pass
            
            elif dType == self.TYPE.FIXED:
                data = handle.read(size)
            
            elif dType == self.TYPE.VARIABLE:
                if size == 1:
                    dataSize, = self.sVariable1.unpack(handle.read(self.sVariable1.size))
                    data = handle.read(dataSize)
                    
                elif size == 2:
                    dataSize, = self.sVariable2.unpack(handle.read(self.sVariable2.size))
                    data = handle.read(dataSize)
                    
                else:
                    raise Exception("Invalid variable size {}".format(size))
            
            elif dType == self.TYPE.U8:
                data, = self.sU8.unpack(handle.read(self.sU8.size))
            
            elif dType == self.TYPE.U16:
                data, = self.sU16.unpack(handle.read(self.sU16.size))
            
            elif dType == self.TYPE.U32:
                data, = self.sU32.unpack(handle.read(self.sU32.size))
            
            elif dType == self.TYPE.U64:
                data, = self.sU64.unpack(handle.read(self.sU64.size))
            
            elif dType == self.TYPE.S8:
                data, = self.sS8.unpack(handle.read(self.sS8.size))
            
            elif dType == self.TYPE.S16:
                data, = self.sS16.unpack(handle.read(self.sS16.size))
            
            elif dType == self.TYPE.S32:
                data, = self.sS32.unpack(handle.read(self.sS32.size))
            
            elif dType == self.TYPE.S64:
                data, = self.sS64.unpack(handle.read(self.sS64.size))
            
            elif dType == self.TYPE.F32:
                data, = self.sF32.unpack(handle.read(self.sF32.size))
                
            elif dType == self.TYPE.F64:
                data, = self.sF64.unpack(handle.read(self.sF64.size))
            
            elif dType == self.TYPE.LLVECTOR3:
                data = self.sLLVector3.unpack(handle.read(self.sLLVector3.size))
            
            elif dType == self.TYPE.LLVECTOR3D:
                data = self.sLLVector3D.unpack(handle.read(self.sLLVector3D.size))
            
            elif dType == self.TYPE.LLVECTOR4:
                data = self.sLLVector4.unpack(handle.read(self.sLLVector4.size))
            
            elif dType == self.TYPE.LLQUATERNION:
                # NOTE: Quaternions are transmitted as vectors. The W component
                # is missing and is just generated on the fly.
                data = self.sLLVector3.unpack(handle.read(self.sLLVector3.size))
            
            elif dType == self.TYPE.LLUUID:
                data = uuid.UUID(bytes=handle.read(16))
            
            elif dType == self.TYPE.BOOL:
                data = handle.read(1)[0] != 0
            
            # NOTE: IPADDR AND IPPORT USE THE BIG ENDIAN sUInt32 AND sUInt16
            # THESE ARE NOT FROM THE MESSAGE CLASS, THEY ARE FROM THE GLOBAL SCOPE!
            # IT IS INTENTIONAL!
            elif dType == self.TYPE.IPADDR:
                data = ipaddress.IPv4Address(sUInt32.unpack(handle.read(sUInt32.size))[0])
            
            elif dType == self.TYPE.IPPORT:
                data, = sUInt16.unpack(handle.read(sUInt16.size))
            
            else:
                raise Exception("Unknown type {}".format(dType))
            
            self.values[name] = data
    
    def registerParameter(self, name, dType, size):
        self.parameters[name] = (dType, size)
    
    def copy(self):
        block = Block(self.name)
        block.parameters = self.parameters
        
        return block


class BlockArray(Block):
    def __init__(self, name, count = None):
        super().__init__(name)
        self.count = count
        self.blocks = []
    
    def __repr__(self):
        return f"<{self.__class__.__name__} {self.name}[{self.count or len(self.blocks)}]>"
    
    def __getitem__(self, i):
        if self.count != None and i > self.count:
            raise IndexError("block index out of range")
        
        for _ in range(len(self.blocks), i + 1):
            self.blocks.append(Block(self.name))
            self.blocks[-1].parameters = self.parameters
                
        return self.blocks[i]
    
    def __len__(self):
        return self.count if self.count is not None else len(self.blocks)

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]
    
    def toStream(self, handle):
        if self.count != None:
            handle.write(sUInt8.pack(self.count))
        
        for i in range(self.count or len(self.blocks)):
            self[i].toStream(handle)
    
    def fromStream(self, handle):
        count = self.count
        if count == None:
            count, = sUInt8.unpack(handle.read(sUInt8.size))
        
        for i in range(count):
            self[i].fromStream(handle)
    
    def copy(self):
        block = BlockArray(self.name, self.count)
        block.parameters = self.parameters
        
        return block

class Message:
    class FREQUENCY(Enum):
        NULL = 0
        HIGH = 1
        MEDIUM = 2
        LOW = 4
    
    class TRUST(Enum):
        TRUST = auto()
        NOTRUST = auto()
    
    class ENCODING(Enum):
        UNENCODED = auto()
        ZEROCODED = auto()
    
    class DEPRECATION(Enum):
        NOT = 0
        UDPDEPRECATED = 1
        UDPBLACKLISTED = 2
        DEPRECATED = 3
    
    def __init__(self, name, frequency, id, trust = None, encoding = None, deprecation = None):
        self.name = name
        self.frequency = frequency
        self.id = id
        self.trust = trust or self.TRUST.TRUST
        self.encoding = encoding or self.ENCODING.UNENCODED
        self.blocks = OrderedDict()
        self.deprecation = deprecation or self.DEPRECATION.NOT
    
    def __repr__(self):
        return f"<{self.__class__.__name__} {self.name} {self.frequency} {self.id} {self.trust} {self.encoding}>"
    
    def __getattr__(self, name):
        return self.blocks[name]
    
    def __bytes__(self):
        buf = io.BytesIO()
        self.toStream(buf, True)
        return buf.getvalue()
    
    def toStream(self, handle, writeID = False):
        if writeID:
            if self.frequency == self.FREQUENCY.LOW:
                handle.write(sUInt32.pack(self.id))
            elif self.frequency == self.FREQUENCY.MEDIUM:
                handle.write(sUInt16.pack(self.id))
            elif self.frequency == self.FREQUENCY.HIGH:
                handle.write(sUInt8.pack(self.id))
        
        for block in self.blocks.values():
            block.toStream(handle)
    
    def load(self, handle, readID = False):
        if readID:
            # This doesn't do anything.
            # Perhaps we could verify the ID?
            if self.frequency == self.FREQUENCY.LOW:
                handle.read(sUInt32.size)
            elif self.frequency == self.FREQUENCY.MEDIUM:
                handle.read(sUInt16.size)
            elif self.frequency == self.FREQUENCY.HIGH:
                handle.read(sUInt8.size)
        
        for block in self.blocks.values():
            block.fromStream(handle)
    
    def loads(self, data, verifyID = True):
        handle = io.BytesIO(data)
        self.load(handle, verifyID)
    
    def registerBlock(self, block):
        if block.name in self.blocks:
            raise Exception("Block {} already registered in message {}".format(block.name, self.name))
        self.blocks[block.name] = block
    
    def copy(self):
        msg = Message(self.name, self.frequency, self.id, self.trust, self.encoding)
        for block in self.blocks.values():
            msg.registerBlock(block.copy())
        
        return msg


class MessageTemplate:
    def __init__(self):
        self.messages = {}
        self.ids = {}
    
    def registerMessage(self, message):
        self.messages[message.name] = message
        self.messages[message.id] = message
    
    def getMessage(self, name):
        return self.messages[name].copy()
    
    def loadMessage(self, message):
        if message[0] == 0xFF:
            if message[1] == 0xFF:
                mid, = sUInt32.unpack_from(message[0:4])
            
            else:
                mid, = sUInt16.unpack_from(message[0:2])
            
        else:
            mid = message[0]
        
        msg = self.getMessage(mid)
        msg.loads(message)
        return msg
    
    @classmethod
    def load(cls, handle):
        templates = parseTemplateAbstract(handle.read())
        return cls.loadAst(templates)
    
    @classmethod
    def loadAst(cls, templates):
        self = cls()
        if not templates:
            raise ValueError("Empty template specified!")
        
        if templates.pop(0) != "version":
            raise Exception("Expected version as first parameter to message template!")
        
        tVersion = float(templates.pop(0))
        
        counters = {"High": 0, "Medium": 0, "Low": 0, "Fixed": 0}
        
        for template in templates:
            if type(template) != list:
                raise Exception("Expected {} in template abstract, got {}!".format(type(list), type(template)))
            
            mName = template.pop(0)
            if type(mName) != str:
                raise Exception("Expected name to be string")
            
            mFrequency = template.pop(0)
            if type(mFrequency) != str:
                raise Exception("Expected frequency to be string")
            
            if mFrequency not in counters.keys():
                raise Exception("Unknown frequency type {}".format(mFrequency))
            
            mID = 0
            
            # Version 2.0 and onward requires explicit message IDs
            counters[mFrequency] += 1
            if mFrequency == "Fixed" or tVersion >= 2.0:
                mID = template.pop(0)
                if type(mID) != str:
                    raise Exception("Expected ID to be string")
                
                if mID.startswith("0x"):
                    mID = int(mID, 16)
                else:
                    mID = int(mID)
            
            else:
                mID = counters[mFrequency]
            
            mTrust = template.pop(0)
            if type(mTrust) != str:
                raise Exception("Expected Trust to be string")
            
            if mTrust not in ("Trusted", "NotTrusted"):
                raise Exception("Unknown trust type {}".format(mTrust))
            
            mEncoding = "Unencoded"
            
            if tVersion >= 2.0:
                mEncoding = template.pop(0)
                if type(mEncoding) != str:
                    raise Exception("Expected Encoding to be string")
            
            if mEncoding not in ("Unencoded", "Zerocoded"):
                raise Exception("Unknown encoding type {}".format(mEncoding))
            
            # --- Start message construction ---
            
            # Idk, this is how message.cpp does it
            if mFrequency == "Fixed":
                mFrequency = Message.FREQUENCY.LOW
                
            elif mFrequency == "Low":
                if mID > 0xFFFF:
                    raise Exception("Too many Low frequency messages")
                
                mFrequency = Message.FREQUENCY.LOW
                mID = (0xFFFF << 16) | mID
                
            elif mFrequency == "Medium":
                if mID > 0xFF:
                    raise Exception("Too many Medium frequency messages")
                
                mFrequency = Message.FREQUENCY.MEDIUM
                mID = (0xFF << 8) | mID
            
            elif mFrequency == "High":
                mFrequency = Message.FREQUENCY.HIGH
                if mID > 0xFF:
                    raise Exception("Too many high frequency messages")
            
            
            if mTrust == "Trusted":
                mTrust = Message.TRUST.TRUST
            
            elif mTrust == "NotTrusted":
                mTrust = Message.TRUST.NOTRUST
            
            
            if mEncoding == "Unencoded":
                mEncoding = Message.ENCODING.UNENCODED
            
            elif mEncoding == "Zerocoded":
                mEncoding = Message.ENCODING.ZEROCODED
            
            mDeprecation = Message.DEPRECATION.NOT
            
            if len(template):
                if template[0] == "UDPDeprecated":
                    mDeprecation = Message.DEPRECATION.UDPDEPRECATED
                    template.pop(0)
                elif template[0] == "UDPBlackListed":
                    mDeprecation = Message.DEPRECATION.UDPBLACKLISTED
                    template.pop(0)
                elif template[0] == "Deprecated":
                    mDeprecation = Message.DEPRECATION.DEPRECATED
                    template.pop(0)
            
            message = Message(mName, mFrequency, mID, mTrust, mEncoding, mDeprecation)
            
            # --- End message construction ---
            
            # All that should remain now is blocks!
            for block in template:
                if len(block) < 2:
                    raise Exception("Block must contain at least a name and quantity")
                
                if type(block) != list:
                    raise Exception("Expected block to be a list")
                
                bName = block.pop(0)
                if type(bName) != str:
                    raise Exception("Expected block name to be string")
                
                bQuantity = block.pop(0)
                if type(bQuantity) != str:
                    raise Exception("Expected quantity name to be string")
                
                bCount = None
                if bQuantity == "Multiple":
                    if len(block) < 1:
                        raise Exception("Multiple quantity specified without count")
                    
                    bCount = block.pop(0)
                    if type(bQuantity) != str:
                        raise Exception("Expected block count to be string")
                    
                    bCount = int(bCount)
                
                # --- Start block construction ---
                
                mBlock = None
                if bQuantity in ("Multiple", "Variable"):
                    mBlock = BlockArray(bName, bCount)
                elif bQuantity == "Single":
                    mBlock = Block(bName)
                else:
                    raise Exception("Unknown quantity {}".format(bQuantity))
                
                # --- End block construction ---
                
                # All that should remain now is parameters!
                for parameter in block:
                    if len(parameter) < 2:
                        raise Exception("Parameter must contain at least a name and type")
                    
                    if type(parameter) != list:
                        raise Exception("Expected parameter to be a list")
                    
                    pName = parameter.pop(0)
                    if type(pName) != str:
                        raise Exception("Expected parameter name to be string")
                    
                    pType = parameter.pop(0)
                    if type(pType) != str:
                        raise Exception("Expected parameter type to be string")
                    
                    pSize = None
                    if pType in ("Fixed", "Variable"):
                        if len(parameter) < 1:
                            raise Exception("Parameter specified Fixed or Variable without size")
                        
                        pSize = parameter.pop(0)
                        if type(pType) != str:
                            raise Exception("Expected parameter size to be string")
                        pSize = int(pSize)
                    
                    pType = mBlock.TYPE[pType.upper()]
                    
                    # --- Start parameter construction ---
                    mBlock.registerParameter(pName, pType, pSize)
                    # --- End parameter construction ---
                    
                
                message.registerBlock(mBlock)
                
            self.registerMessage(message)
        return self


def parseTemplateAbstract(text):
    parsed = []
    stack = [parsed]
    strbuf = ""
    comment = 0
    for c in text:
        if c == "/":
            comment += 1
            continue
        
        elif comment >= 2:
            if c == "\n":
                comment = 0
            else:
                continue
        
        elif comment == 1:
            raise Exception("Unexpected /")
            
        if c in (" ", "\t", "{", "}", "\n"):
            if strbuf != "":
                stack[-1].append(strbuf)
                strbuf = ""
        
        if c == "{":
            stack.append([])
        
        elif c == "}":
            tmp = stack.pop()
            stack[-1].append(tmp)
        
        elif not c in (" ", "\t", "\n"):
            strbuf += c
    
    return parsed

__templateCache = None

def getDefaultTemplate():
    global __templateCache
    if not __templateCache:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(script_dir, "message_template.msg")
        with open(template_path, "r") as f:
            __templateCache = MessageTemplate.load(f)
    return __templateCache

def unitTest():
    with open("message_template.msg", "r") as f:
        template = MessageTemplate.load(f)
        msg = template.getMessage("TestMessage")
        msg.TestBlock1.Test1 = 4
        
        for i in range(0, 4):
            msg.NeighborBlock[i].Test0 = i * 3
            msg.NeighborBlock[i].Test1 = i * 3 + 1
            msg.NeighborBlock[i].Test2 = i * 3 + 2
        print(msg)
        print(ZeroEncode(bytes(msg)))
        print(ZeroDecode(ZeroEncode(bytes(msg))))
        print(bytes(msg) == ZeroDecode(ZeroEncode(bytes(msg))))
        msg2 = template.getMessage("TestMessage")
        msg2.loads(bytes(msg))
        print(msg2.TestBlock1.Test1)


if __name__ == "__main__":
    unitTest()