import asyncio
from ..eventtarget import EventTarget
from . import packet

class Circuit(asyncio.Protocol, EventTarget):
    def __init__(self):
        super().__init__()
        self.transport = None
        self.sequence = 0
        self.unackd = {}
        self.acks = []
    
    def nextSequence(self):
        seq = self.sequence
        self.sequence += 1
        return seq
    
    def acknowledge(self, sequences):
        for ack in sequences:
            if ack in self.unackd:
                self.unackd.pop(ack)
    
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        pkt = packet.Packet.fromBytes(data)
        if pkt.reliable:
            self.acks.append(pkt.sequence)
        
        # Has acks, acknowledge them!
        if pkt.flags & pkt.FLAGS.ACK:
            self.acknowledge(pkt.acks)
        
        asyncio.create_task(self.fire("message", addr, pkt.body))

    def error_received(self, exc):
        asyncio.create_task(self.fire("error", exc))

    def connection_lost(self, exc):
        if not self.transport:
            return
        
        self.transport = None
        asyncio.create_task(self.fire("close", exc))
    
    def close(self):
        if not self.transport:
            return
        
        self.transport.close()
        self.transport = None
        asyncio.create_task(self.fire("close", None))
    
    def send(self, message, reliable = False):
        if not self.transport:
            return
        
        pkt = packet.Packet(self.nextSequence(), bytes(message), acks=self.acks)
        if reliable:
            pkt.reliable = True
            self.unackd[pkt.sequence] = pkt
        
        self.transport.sendto(pkt.toBytes())
    
    def resend(self, distance = 100):
        if not self.transport:
            return
        
        cutoff = self.sequence - distance
        for pkt in self.unackd.values():
            if pkt.sequence < cutoff:
                pkt.resent = True
                self.transport.sendto(pkt.toBytes())
    
    @classmethod
    async def create(cls, host, loop = None):
        loop = loop or asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: cls(),
            remote_addr=host)
        return protocol