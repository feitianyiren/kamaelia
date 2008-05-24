#!/usr/bin/env python
#-*-*- encoding: utf-8 -*-*-
# 
# (C) 2008 British Broadcasting Corporation and Kamaelia Contributors(1)
#     All Rights Reserved.
#
# You may only modify and redistribute this under the terms of any of the
# following licenses(2): Mozilla Public License, V1.1, GNU General
# Public License, V2.0, GNU Lesser General Public License, V2.1
#
# (1) Kamaelia Contributors are listed in the AUTHORS file and at
#     http://kamaelia.sourceforge.net/AUTHORS - please extend this file,
#     not this notice.
# (2) Reproduced in the COPYING file, and at:
#     http://kamaelia.sourceforge.net/COPYING
# Under section 3.5 of the MPL, we are using this text since we deem the MPL
# notice inappropriate for this file. As per MPL/GPL/LGPL removal of this
# notice is prohibited.
#
# Please contact us via: kamaelia-list-owner@lists.sourceforge.net
# to discuss alternative licensing.
# -------------------------------------------------------------------------
# Licensed to the BBC under a Contributor Agreement: PO

import Axon
import feedparser
from Kamaelia.Protocol.HTTP.HTTPClient import SimpleHTTPClient
from Kamaelia.Chassis.Pipeline import Pipeline
from Kamaelia.Util.Splitter import Plug, PlugSplitter
from Kamaelia.Util.OneShot import OneShot
from Axon.Ipc import producerFinished, shutdownMicroprocess

from ForwarderComponent import Forwarder

class Feedparser(Axon.Component.component):
    def __init__(self, feedUrl):
        super(Feedparser, self).__init__()
        self.feedUrl = feedUrl
        
    def main(self):
        while True:
            while self.dataReady("inbox"):
                data = self.recv("inbox")
                parseddata = feedparser.parse(data)
                parseddata.href = self.feedUrl
                self.send(parseddata, "outbox")

            while self.dataReady("control"):
                data = self.recv("control")
                self.send(data,"signal")
                return

            if not self.anyReady():
                self.pause()
            yield 1

def makeFeedParser(feedUrl):
    return Pipeline(
            OneShot(feedUrl), 
            SimpleHTTPClient(), #TODO: SimpleHTTPClient doesn't seem to have proxy support
            Feedparser(feedUrl)
        )

class FeedParserFactory(Axon.Component.component):
    Inboxes = {
        "inbox"          : "Information coming from the socket",
        "control"        : "From component...",
        "_parsed-feeds"  : "Feedparser drops here the feeds", 
    }
    Outboxes = {
        "outbox"         : "From component...", 
        "signal"         : "From component...", 
        "_signal"        : "To the internal parsers", 
    }
    def __init__(self, **argd):
        super(FeedParserFactory, self).__init__(**argd)
        self.mustStop         = None
        self.providerFinished = False

    def checkControl(self):
        while self.dataReady("control"):
            msg = self.recv("control")
            if isinstance(msg,producerFinished):
                self.providerFinished = True
            elif isinstance(msg,shutdownMicroprocess):
                self.mustStop = msg
        return self.mustStop, self.providerFinished

    def handleChildTerminations(self): #taken from Carousel.py
        for child in self.childComponents():
            if child._isStopped():
                self.removeChild(child)
                
    def initiateInternalSplitter(self):
        self.internalSplitter = PlugSplitter()
        self.link((self,'_signal'), (self.internalSplitter, 'control'))
        self.addChildren(self.internalSplitter)
        self.internalSplitter.activate()
        
    def linkChildToInternalSplitter(self, child):
        forwarder = Forwarder()
        plug = Plug(self.internalSplitter,  forwarder)
        plug.activate()
        outsideForwarder = Forwarder()
        plug.link((plug, 'signal'), (outsideForwarder, 'secondary-control'))
        child.link((outsideForwarder, 'signal'),  (child, 'control'))
        
    def createChild(self, feed):
        child = makeFeedParser(feed.url)
        self.link( (child, 'outbox'), (self, '_parsed-feeds') )
        self.linkChildToInternalSplitter(child)
        return child
        
    def waitForChildren(self, signalMessage):
        self.send(signalMessage,"_signal")
        while len(self.childComponents()) > 0:
            self.handleChildTerminations()
            yield 1
        
    def main(self):
        self.initiateInternalSplitter()
        yield 1
        
        while True:
            mustStop, providerFinished = self.checkControl()
            if mustStop:
                for _ in self.waitForChildren(mustStop):
                    yield 1
                self.send(mustStop,"signal")
                return
            
            self.handleChildTerminations()
            
            while self.dataReady("inbox"):
                feed = self.recv("inbox")
                child = self.createChild(feed)
                self.addChildren(child)
                child.activate()
            
            while self.dataReady("_parsed-feeds"):
                parseddata = self.recv("_parsed-feeds")
                self.send(parseddata,"outbox")
            
            if providerFinished and len(self.childComponents()) == 1:
                # It's actually only waiting for the plugsplitter
                for _ in self.waitForChildren(producerFinished(self)):
                    yield 1
                self.send(producerFinished(self),"signal")
                return
            
            if not self.anyReady():
                self.pause()
            yield 1
