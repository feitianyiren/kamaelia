#!/usr/bin/env python

from Axon.Component import component
from Axon.ThreadedComponent import threadedcomponent
from Axon.Ipc import producerFinished, shutdownMicroprocess
from Kamaelia.Util.PipelineComponent import pipeline
import time


class Profiler(threadedcomponent):
    """\
    Profiler([samplingrate][,outputrate]) -> new Profiler component.

    Basic code profiler for Axon/Kamaelia systems. Measures the amount of time
    different microproceses are running.
    
    Keyword arguments:
    - samplingrate  -- samples of state taken per second (default=1.0)
    - outputrate    -- times statistics are output per second (default=1.0)
    """
    Inboxes = { "inbox" : "",
                "control" : "",
              }
    Outboxes = { "outbox" : "Raw profiling data",
                 "signal" : "",
               }

    def __init__(self, samplingrate=1.0, outputrate=1.0):
        super(Profiler,self).__init__()
        self.samplestep = 1.0 / samplingrate
        self.outputstep = 1.0 / outputrate

    def shutdown(self):
        while self.dataReady("control"):
            msg = self.recv("control")
            self.send(msg,"signal")
            if isinstance(msg, (shutdownMicroprocess, producerFinished)):
                return True
        return False

    def main(self):
        microprocesses = {}
        
        now = time.time()
        nextsample = now
        nextoutput = now
        scheduler = self.scheduler
        
        while not self.shutdown():
            
            nexttime = min(nextsample,nextoutput)
            time.sleep(nexttime-now)
            
            now=time.time()
            if now >= nextsample:
                nextsample = now+self.samplestep
                
                for mprocess in scheduler.listAllThreads():
                    name=mprocess.name
                    running,active = microprocesses.get(name, (0,0))
                    running+=1
                    if not scheduler.isThreadPaused(mprocess):
                        active+=1
                    microprocesses[name] = running,active
                
            if now >= nextoutput:
                nextoutput = now+self.outputstep
                
                print "-----Run----Active--Name-----------------"
                for name,(running,active) in microprocesses.iteritems():
                    print "%8d  %8d  %s" % (running,active,name)
                print "------------------------------------------"


class ProfilerOutputFormatter(component):
    def shutdown(self):
        while self.dataReady("control"):
            msg = self.recv("control")
            self.send(msg,"signal")
            if isinstance(msg, (shutdownMicroprocess, producerFinished)):
                return True
        return False

    def main(self):
        while not self.shutdown():
        
            while self.dataReady("inbox"):
                profile = self.recv("inbox")
                output = "-----Run----Active--Name-----------------\n"
                for name in profile:
                    running,active = profile[name]
                    output += "%8d  %8d  %s" % (running,active,name)
                output += "------------------------------------------"
                self.send(output,"outbox")
        
            yield 1
            self.pause()    

def FormattedProfiler(*largs,**kargs):
    return pipeline( Profiler(*largs,**kargs), 
                     ProfilerOutputFormatter()
                   )

if __name__=="__main__":
    from Kamaelia.Util.Console import ConsoleEchoer

    class BusyComponent(component):
        def main(self):
            while 1:
                yield 1
    
    BusyComponent().activate()
    
    pipeline( FormattedProfiler(10.0,1.0),
              ConsoleEchoer(),
            ).run()
    