#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010 British Broadcasting Corporation and Kamaelia Contributors(1)
#
# (1) Kamaelia Contributors are listed in the AUTHORS file and at
#     http://www.kamaelia.org/AUTHORS - please extend this file,
#     not this notice.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# -------------------------------------------------------------------------
"""\
=====================
General 3D Object
=====================
Methods to be overridden:
    draw()
    handleEvents()
    setup()
    frame()
"""


import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

import Axon
from Util3D import *
from Display3D import Display3D

class SimpleTranslationInteractor(Axon.Component.component):
    Inboxes = {
       "inbox": "Input events",
       "control": "ignored",
       "callback": "for the response after a displayrequest",
    }
    
    Outboxes = {
        "outbox": "used for sending relative tranlational movement",
        "display_signal" : "Outbox used for communicating to the display surface",
    }
    
    def __init__(self, **argd):
        super(SimpleTranslationInteractor, self).__init__()

        # get display service
        displayservice = Display3D.getDisplayService()
        # link display_signal to displayservice
        self.link((self,"display_signal"), displayservice)
                                         
        self.grabbed = False
        
        self.translationfactor = argd.get("translationfactor", 10.0)
        
        self.victim = id(argd.get("victim"))
                    
            
    def main(self):

        # create display request
        self.eventspyrequest = { "EVENTSPYREQUEST" : True,
                                                   "objectid" : id(self),
                                                   "victim": self.victim,
                                                   "callback" : (self,"callback"),
                                                   "events" : (self, "inbox")  }
    
        # send display request
        self.send(self.eventspyrequest, "display_signal")

        # setup function from derived objects
        self.setup()        

        # wait for response on displayrequest
        while not self.dataReady("callback"): yield 1
        self.ogl_name = self.recv("callback")

        while 1:
            yield 1
            self.handleEvents()
            # frame function from derived objects
            self.frame()

    ##
    # Methods to be used by derived objects
    ##

    def addListenEvents(self, events):
#        print ("addlistenevent sending")
        for event in events:
#            print event
            self.send({"ADDLISTENEVENT":event, "objectid":id(self)}, "display_signal")

    
    def removeListenEvents(self, events):
        for event in events:
            self.send({"REMOVELISTENEVENT":event, "objectid":id(self)}, "display_signal")


    ##
    # Method stubs to be overridden by derived objects
    ##

    def setup(self):
        self.addListenEvents( [pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP ])

    def handleEvents(self):
        while self.dataReady("inbox"):
            event = self.recv("inbox")
            if event.type == pygame.MOUSEBUTTONDOWN and self.ogl_name in event.hitobjects:
                if event.button == 1:
                    self.grabbed = True
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.grabbed = False
            if event.type == pygame.MOUSEMOTION:
                if self.grabbed == True:
                    amount = (float(event.rel[0])/self.translationfactor, -float(event.rel[1])/self.translationfactor)
                    self.send(amount, "outbox")

    def frame(self):
        """ Method stub """
        pass


from SimpleCube import *

if __name__=='__main__':
    o1 = SimpleCube(pos=Vector(0, 0,-25), name="center").activate()
    interactor = SimpleTranslationInteractor(victim=o1).activate()
    
    interactor.link( (interactor, "outbox"), (o1, "rel_position"))
    
    Axon.Scheduler.scheduler.run.runThreads()  
