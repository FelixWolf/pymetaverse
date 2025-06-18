#!/usr/bin/env python3
"""
Name: llsd.py
Purpose: Parse and serialize LLSD objects

Copyright (c) 2021 Kyler Eastridge

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.
2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.
3. This notice may not be removed or altered from any source distribution.
"""

import uuid
import datetime
import base64
import io
import struct
import xml.etree.ElementTree as ET

class URI(str):
    def __repr__(self):
        return "URI({})".format(super().__repr__())

#Encoders
def llsdEncodeXml(input, destination, *args, optimize = False, encoding = "base64", **kwargs):
    t = type(input)
    if input == None:
        elm = ET.SubElement(destination, "undef")
    elif t == bool:
        elm = ET.SubElement(destination, "boolean")
        if input:
            elm.text = "true"
        elif not optimize:
            elm.text = "false"
    elif t == int:
        elm = ET.SubElement(destination, "integer")
        if input != 0 or not optimize:
            elm.text = str(input)
    elif t == float:
        elm = ET.SubElement(destination, "real")
        if input != 0 or not optimize:
            elm.text = str(input)
    elif t == uuid.UUID:
        elm = ET.SubElement(destination, "uuid")
        if input.bytes != b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0" or not optimize:
            elm.text = str(input)
    elif t == str:
        elm = ET.SubElement(destination, "string")
        if input != "" or not optimize:
            elm.text = input
    elif t == bytes:
        encoder = encoding
        elm = ET.SubElement(destination, "binary")
        if input != b"" or not optimize:
            if encoder == "base64":
                elm.text = base64.b64encode(input).decode()
            elif encoder == "base85":
                elm.text = base64.b85encode(input).decode()
            elif encoder == "base16":
                elm.text = base64.b16encode(input).decode()
            else:
                raise ValueError("Unknown binary encoding {}!".format(encoder))
    elif t == datetime.datetime:
        elm = ET.SubElement(destination, "date")
        elm.text = input.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    elif t == URI:
        elm = ET.SubElement(destination, "uri")
        if input != "" or not optimize:
            elm.text = input
    elif t == dict:
        root = ET.SubElement(destination, "map")
        for key in input:
            if type(key) != str:
                raise ValueError("Dictionary keys must be type str, not {}!".format(type(key)))
            elm = ET.SubElement(root, "key")
            elm.text = key
            llsdEncodeXml(input[key], root, *args, **kwargs)
    elif t == list:
        root = ET.SubElement(destination, "array")
        for value in input:
            llsdEncodeXml(value, root, *args, **kwargs)

def llsdEncode(input, *args, format = "xml", **kwargs):
    if format == "xml":
        root = ET.Element("llsd")
        if "optimize" not in kwargs:
            kwargs["optimize"] = True
        llsdEncodeXml(input, root, *args, **kwargs)
        xml = ET.ElementTree(root)
        f = io.BytesIO()
        xml.write(f, encoding='UTF-8', xml_declaration=True)
        return f.getvalue()

#Decoders
def parseISODate(input):
    try:
        if input[-1] == "Z":
            input = input[:-1]
        date, time = input.split("T", 2)
        year, month, day = date.split("-", 3)
        hour, minute, second = time.split(":", 3)
        if "." in second:
            second, microsecond = second.split(".", 2)
        else:
            microsecond = 0
        return datetime.datetime(*[int(i) for i in [year, month, day, hour, minute, second, microsecond]])
    except ValueError:
        raise ValueError("Invalid timestamp '{}'!".format(input))

def llsdDecodeXml(input):
    if input.tag == "undef":
        return None
    elif input.tag == "boolean":
        value = input.text
        if value == None:
            return False
        value = value.lower()
        if value in ["1", "true"]:
            return True
        elif value in ["", "0", "false"]:
            return False
        else:
            raise ValueError("Unexpected value '{}' for boolean!".format(value))
    elif input.tag == "integer":
        if input.text == None:
            return 0
        return int(input.text)
    elif input.tag == "real":
        if input.text == None:
            return 0
        return float(input.text)
    elif input.tag == "uuid":
        if input.text == None:
            return uuid.UUID(bytes=b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0")
        return uuid.UUID(input.text)
    elif input.tag == "string":
        if input.text == None:
            return ""
        return input.text
    elif input.tag == "binary":
        if input.text == None:
            return b""
        encoding = input.attrib.get("encoding", "base64").lower()
        if encoding == "base64":
            return base64.b64decode(input.text)
        elif encoding == "base85":
            return base64.b85decode(input.text)
        elif encoding == "base16":
            return base64.b16decode(input.text)
        else:
            raise ValueError("Unknown encoding {} for binary element!".format(encoding))
    elif input.tag == "date":
        if input.text == None:
            return datetime.datetime.fromtimestamp(0)
        return parseISODate(input.text)
    elif input.tag == "uri":
        if input.text == None:
            return URI("")
        return URI(input.text)
    elif input.tag == "map":
        result = {}
        for i in range(0, len(input), 2):
            if input[i].tag != "key":
                raise ValueError("Unexpected {} element in map, expected key!".format(input[i].tag))
            result[input[i].text] = llsdDecodeXml(input[i+1])
        return result
    elif input.tag == "array":
        result = [None]*len(input)
        for i in range(0, len(input)):
            result[i] = llsdDecodeXml(input[i])
        return result
    else:
        raise ValueError("Unexpected {} element in LLSD!".format(input.tag))

def llsdDecode(input, *args, format = None, maxHeaderLength = 128, **kwargs):
    if format == None:
        isBytes = type(input) == bytes
        i = 0
        l = len(input)
        while i < l and i < maxHeaderLength:
            if isBytes:
                c = chr(input[i])
            else:
                c = input[i]
            if c == '"' or c == "'":
                quoteChar = c
                while i < l and i < maxHeaderLength:
                    i += 1
                    if isBytes:
                        c = chr(input[i])
                    else:
                        c = input[i]
                    if c == quoteChar:
                        break
                    elif c == "\\":
                        #Assuming the file is valid, no unicode should be in the
                        #header
                        i += 1
                i += 1
            i += 1
            if c == ">":
                break
        header = input[2:i-2].strip().lower()
        if header == "llsd/notation":
            format = "notation"
        elif header == "llsd/binary":
            format = "binary"
        else:
            tmp = header[0:3]
            if type(tmp) == bytes:
                tmp = tmp.decode()
            if tmp == "xml":
                format = "xml"
            else:
                raise ValueError("Unable to detect serialization format!")
    
    if format == "xml":
        input = ET.fromstring(input)
        if input.tag != "llsd":
            raise ValueError("Unexpected tag {} in LLSD+XML!".format(input.tag))
        return llsdDecodeXml(input[0])
    else:
        raise ValueError("Unknown serialization format {}!".format(format))
        

if __name__ == "__main__":
    source_test = {
        "undef": [None],
        "boolean": [True, False],
        "integer": [289343, -3, 0],
        "real": [-0.28334, 2983287453.3848387, 0.0],
        "uuid": [
            uuid.UUID("d7f4aeca-88f1-42a1-b385-b9db18abb255"),
            uuid.UUID("00000000-0000-0000-0000-000000000000")
        ],
        "string": [
            "The quick brown fox jumped over the lazy dog.",
            "540943c1-7142-4fdd-996f-fc90ed5dd3fa",
            ""
        ],
        "binary": [
            b"The quick brown fox jumped over the lazy dog."
        ],
        "date": [
            datetime.datetime.now()
        ],
        "uri": [
            URI("http://sim956.agni.lindenlab.com:12035/runtime/agents")
        ]
    }
    llsd_xml_test = """<?xml version="1.0" encoding="UTF-8"?>
<llsd>
  <map>
    <key>undef</key>
      <array>
        <undef />
      </array>
    <key>boolean</key>
      <array>
        <!-- true -->
        <boolean>1</boolean>
        <boolean>true</boolean>
        
        <!-- false -->
        <boolean>0</boolean>
        <boolean>false</boolean>
        <boolean />
      </array>
    <key>integer</key>
      <array>
        <integer>289343</integer>
        <integer>-3</integer>
        <integer /> <!-- zero -->
      </array>
    <key>real</key>
      <array>
        <real>-0.28334</real>
        <real>2983287453.3848387</real>
        <real /> <!-- exactly zero -->
      </array>
    <key>uuid</key>
      <array>
        <uuid>d7f4aeca-88f1-42a1-b385-b9db18abb255</uuid>
        <uuid /> <!-- null uuid '00000000-0000-0000-0000-000000000000' -->
      </array>
    <key>string</key>
      <array>
        <string>The quick brown fox jumped over the lazy dog.</string>
        <string>540943c1-7142-4fdd-996f-fc90ed5dd3fa</string>
        <string /> <!-- empty string -->
      </array>
    <key>binary</key>
      <array>
        <binary encoding="base64">cmFuZG9t</binary> <!-- base 64 encoded binary data -->
        <binary>dGhlIHF1aWNrIGJyb3duIGZveA==</binary> <!-- base 64 encoded binary data is default -->
        <binary encoding="base85">YISXJWn>_4c4cxPbZBJ</binary>
        <binary encoding="base16">6C617A7920646F67</binary>
        <binary /> <!-- empty binary blob -->
      </array>
    <key>date</key>
      <array>
        <date>2006-02-01T14:29:53.43Z</date>
        <date /> <!-- epoch -->
      </array>
    <key>uri</key>
      <array>
        <uri>http://sim956.agni.lindenlab.com:12035/runtime/agents</uri>
        <uri /> <!-- an empty link -->
      </array>
  </map>
</llsd>"""
    
    llsd_notation_test = """<?llsd/notation?>
{
  'undef':
  [
    !
  ],
  'boolean':
  [
    1,
    t,
    T,
    true,
    TRUE,
    0
    f,
    F,
    false,
    FALSE
  ],
  'integer':
  [
    i289343,
    i-3
  ],
  'real':
  [
    r-0.28334,
    r2983287453.3848387
  ]
  'uuid':
  [
    ud7f4aeca-88f1-42a1-b385-b9db18abb255
  ]
  'string';
    'The quick brown fox jumped over the lazy dog.'
    "540943c1-7142-4fdd-996f-fc90ed5dd3fa",
    s(10)'0123456789',
    s(10)"0123456789"
  ]
  'binary':
  [
      b64"cmFuZG9t",
      b64'dGhlIHF1aWNrIGJyb3duIGZveA==',
      b85"YISXJWn>_4c4cxPbZBJ",
      b16'6C617A7920646F67',
      b(10)'0123456789'
  ]
  'date':
  [
    d"2006-02-01T14:29:53.43Z"
  ]
  'uri':
  [
    l"http://sim956.agni.lindenlab.com:12035/runtime/agents"
  ]
}"""