#!/usr/bin/env python

# dynamic audio downmixer

# this component takes in raw 1 channel S16_LE audio chunks
# each chunk must be framed with a unique source identifier
#     (srcId, audiodata)
#
#
# this component maintains buffering buckets for each source
# it mixes together all sources for which it has data at the time
# if a given buffer bucket overflows, then the oldest data is dropped

# a buffering bucket doesn't start to be read from until it has reached a minimum
# threshold amount of data; after which it remains 'active' until it empties


from Axon.Ipc import shutdownMicroprocess, producerFinished
import time as _time

# want pausing capability in threadedcomponent
import sys
sys.path.append("../Timer/")
from ThreadedComponent import threadedcomponent


class AudioBuffer(object):
    """\
    AudioBuffer(activationThreshold, sizeLimit) -> new AudioBuffer component.
    
    Doesn't 'activate' until threshold amount of data arrives
    
    
    Keyword arguments:
    -- activationThreshold  - Point at which the buffer is deemed activated
    -- sizeLimit            - Filling the buffer beyond this causes samples to be dropped
    """
    def __init__(self, activationThreshold, sizeLimit):
        super(AudioBuffer,self).__init__()
        self.size = 0
        self.sizeLimit = sizeLimit
        self.activationThreshold = activationThreshold
        self.buffer = []
        self.active = False

    def __len__(self):
        # return how much data there is
        return self.size

    def append(self, newdata):
        # add new data to the buffer, if there is too much, drop the oldest data
        
        self.buffer.append(newdata)
        self.size += len(newdata)

        if self.size >= self.activationThreshold:
            self.active = True

        if self.size > self.sizeLimit:
            self.drop(self.size - self.sizeLimit)


    def drop(self,amount):
        self.size -= amount
        while amount > 0:
            fragment = self.buffer[0]
            if len(fragment) <= amount:
                amount -= len(fragment)
                del self.buffer[0]
            else:
                self.buffer[0] = fragment[amount:]
                amount = 0
        self.size -= amount

    def pop(self, amount):
        if not self.active:
            return ""
        
        data = []

        padding_silence = ""
        if amount > self.size:
            padding_silence = chr(0) * (amount-self.size)
            amount = self.size

        self.size -= amount
        
        while amount > 0:
            fragment = self.buffer[0]
            if len(fragment) <= amount:
                data.append(fragment)
                amount -= len(fragment)
                del self.buffer[0]
            else:
                data.append(fragment[:amount])
                self.buffer[0] = fragment[amount:]
                amount = 0

        data.append(padding_silence)
        
        if self.size==0:
            self.active = False
        
        return "".join(data)



class RawAudioMixer(threadedcomponent):
    """Assuming mono signed 16 bit Little endian audio"""
    def __init__(self, sample_rate=8000, readThreshold=1.0, bufferingLimit=2.0, readInterval=0.1):
        super(RawAudioMixer,self).__init__()
        self.sample_rate = sample_rate
        self.bufferingLimit = bufferingLimit
        self.readThreshold = readThreshold
        self.readInterval = readInterval

    def checkForShutdown(self):
        while self.dataReady("control"):
            msg=self.recv("control")
            self.send(msg,"signal")
            if isinstance(msg, (producerFinished,shutdownMicroprocess)):
                return True
        return False
        
    def main(self):
        buffers = {}
        
        self.MAXBUFSIZE = int(self.sample_rate*self.bufferingLimit*2)    # 2 = bytes per sample
        self.BUFTHRESHOLD = int(self.sample_rate*self.readThreshold*2)   # 2 = bytes per sample
        
        READCHUNKSIZE = int(self.sample_rate*self.readInterval)*2

        shutdown = False
        while not shutdown:
            
            # whilst none of the buffers are active (ie. full enough to start reading out data)
            anyActive=False
            while not anyActive and not shutdown:
            
                while self.dataReady("inbox") and not anyActive:
                    activated = self.fillBuffer(buffers, self.recv("inbox"))
                    anyActive = anyActive or activated

                shutdown = shutdown or self.checkForShutdown()
                if shutdown:
                    break
                
                if not anyActive:
                    self.pause()
                    
            # switch to reading from buffers (active) mode
            nextReadTime = _time.time()
            
            # dump out audio until all buffers are empty
            while len(buffers) and not shutdown:
                
                while self.dataReady("inbox") and _time.time() < nextReadTime:
                    reading = self.fillBuffer(buffers, self.recv("inbox"))
                
                now = _time.time()
                if now >= nextReadTime:
                    
                    # read from all buffers (only active ones output samples)
                    audios = []
                    for buf in buffers.keys():
                        audio = buffers[buf].pop(READCHUNKSIZE)
                        if audio:
                            audios.append(audio)
                            
                        # delete any empty buffers
                        if not len(buffers[buf]):
                            del buffers[buf]
                            
                    # assuming we've got something, mix it and output it
                    if audios:
                        self.send(self.mixAudio(audios, READCHUNKSIZE), "outbox")
                
                    nextReadTime += self.readInterval
                    
                shutdown = shutdown or self.checkForShutdown()
                if shutdown:
                    break
                
                if len(buffers) and not self.dataReady("inbox"):
                    self.pause( nextReadTime - _time.time() )
                
            # now there are no active buffers, go back to reading mode
            
    def fillBuffer(self, buffers, data):
        srcId, audio = data
        
        try:
            buf = buffers[srcId]
        except KeyError:
            buf = AudioBuffer(self.BUFTHRESHOLD,self.MAXBUFSIZE)
            buffers[srcId] = buf
            
        buf.append(audio)
        
        return buf.active
        
    
    def mixAudio(self,sources, amount):
        output = []
        for i in xrange(0,amount,2):
            sum=0
            for src in sources:
                value = ord(src[i]) + (ord(src[i+1]) << 8)
#                sum += value - ((value&0x8000) and 65536)
                if value & 0x8000:
                    value -= 65536
                sum += value
            output.append( chr(sum & 255)+chr((sum>>8) & 255) )
        return "".join(output)


