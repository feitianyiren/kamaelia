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
#

import os
import sys
import Axon
import pygame

from Axon.Component import component
from Axon.Ipc import WaitComplete, producerFinished, shutdownMicroprocess

from Kamaelia.Chassis.Graphline import Graphline
from Kamaelia.Chassis.Pipeline import Pipeline
from Kamaelia.Chassis.ConnectedServer import SimpleServer
from Kamaelia.Internet.TCPClient import TCPClient

from Kamaelia.Util.Console import ConsoleEchoer
from Kamaelia.Visualisation.PhysicsGraph.chunks_to_lines import chunks_to_lines
from Kamaelia.Visualisation.PhysicsGraph.lines_to_tokenlists import lines_to_tokenlists as text_to_tokenlists
from Kamaelia.Util.NullSink import nullSinkComponent

from Kamaelia.Util.Backplane import Backplane, PublishTo, SubscribeTo
from Kamaelia.Util.Detuple import SimpleDetupler
from Kamaelia.Util.Console import ConsoleEchoer

# Ticker
from Kamaelia.UI.Pygame.Ticker import Ticker

# OpenGL (EEEEK)
from Kamaelia.UI.OpenGL.OpenGLDisplay import OpenGLDisplay
from Kamaelia.UI.PygameDisplay import PygameDisplay

#
# The following application specific components will probably be rolled
# back into the repository.
#
from Kamaelia.Apps.Whiteboard.TagFiltering import TagAndFilterWrapper, FilterAndTagWrapper
from Kamaelia.Apps.Whiteboard.TagFiltering import TagAndFilterWrapperKeepingTag, FilterAndTagWrapperKeepingTag
from Kamaelia.Apps.Whiteboard.Tokenisation import tokenlists_to_lines, lines_to_tokenlists
from Kamaelia.Apps.Whiteboard.Canvas import Canvas
from Kamaelia.Apps.Whiteboard.Painter import Painter
from Kamaelia.Apps.Whiteboard.SingleShot import OneShot
from Kamaelia.Apps.Whiteboard.CheckpointSequencer import CheckpointSequencer
from Kamaelia.Apps.Whiteboard.Entuple import Entuple
from Kamaelia.Apps.Whiteboard.Routers import Router, TwoWaySplitter, ConditionalSplitter
from Kamaelia.Apps.Whiteboard.Palette import buildPalette, colours
from Kamaelia.Apps.Whiteboard.Options import parseOptions
from Kamaelia.Apps.Whiteboard.UI import PagingControls, LocalPagingControls, Eraser, ClearPage, SaveDeck, LoadDeck, ClearScribbles
from Kamaelia.Apps.Whiteboard.CommandConsole import CommandConsole
from Kamaelia.Apps.Whiteboard.SmartBoard import SmartBoard
from Kamaelia.Apps.Whiteboard.Webcam import Webcam

try:
    from Kamaelia.Codec.Speex import SpeexEncode,SpeexDecode
except Exception, e:
    print "Speex not available, using null components instead"
    SpeexEncode = nullSinkComponent
    SpeexDecode = nullSinkComponent

try:
    from Kamaelia.Apps.Whiteboard.Audio import SoundInput
except ImportError:
    print "SoundInput not available, using NullSink instead"
    SoundInput = nullSinkComponent

try:
    from Kamaelia.Apps.Whiteboard.Audio import SoundOutput
except ImportError:
    print "SoundOutput not available, using NullSink instead"
    SoundOutput = nullSinkComponent

try:
    from Kamaelia.Apps.Whiteboard.Audio import RawAudioMixer
except ImportError:
    print "RawAudioMixer not available, using NullSink instead"
    RawAudioMixer = nullSinkComponent
    
    
notepad = None
if len(sys.argv) >1:
    if os.path.exists(sys.argv[1]):
        if os.path.isdir(sys.argv[1]):
            notepad = sys.argv[1]
            
if (notepad is None) and os.path.exists("Scribbles"):
    if os.path.isdir("Scribbles"):
        notepad = "Scribbles"

if (notepad is None):
   N = os.path.join(os.path.expanduser("~"),"Scribbles")
   if not os.path.exists(N):
       os.makedirs(N)
   if os.path.isdir(N):
       notepad = N

if (notepad is None):
    print "Can't figure out what to do with piccies. Exitting"
    sys.exit(0)



#
# Misplaced encapsulation --> Kamaelia.Apps.Whiteboard.Palette
#
colours_order = [ "black", "red", "orange", "yellow", "green", "turquoise", "blue", "purple", "darkgrey", "lightgrey" ]

num_pages = 0
for x in os.listdir(notepad):
    if (os.path.splitext(x)[1] == ".png"):
        num_pages += 1
#num_pages = len(os.listdir(notepad))
if (num_pages < 1):
    num_pages = 1

def FilteringPubsubBackplane(backplaneID,**FilterTagWrapperOptions):
  """Sends tagged events to a backplane. Emits events not tagged by this pubsub."""
  return FilterAndTagWrapper(
            Pipeline(
                PublishTo(backplaneID),
                # well, should be to separate pipelines, this is lazier!
                SubscribeTo(backplaneID),
            ),
            **FilterTagWrapperOptions
         )


def clientconnector(whiteboardBackplane="WHITEBOARD", audioBackplane="AUDIO", port=1500):
    return Pipeline(
        chunks_to_lines(),
        lines_to_tokenlists(),
        Graphline(
            ROUTER = Router( ((lambda T : T[0]=="SOUND"), "audio"),
                             ((lambda T : T[0]!="SOUND"), "whiteboard"),
                           ),
            WHITEBOARD = FilteringPubsubBackplane(whiteboardBackplane),
            AUDIO = Pipeline(
                        SimpleDetupler(1),     # remove 'SOUND' tag
                        SpeexDecode(3),
                        FilteringPubsubBackplane(audioBackplane, dontRemoveTag=True),
                        RawAudioMixer(),
                        SpeexEncode(3),
                        Entuple(prefix=["SOUND"],postfix=[]),
                    ),
            linkages = {
                # incoming messages go to a router
                ("", "inbox") : ("ROUTER", "inbox"),
                # distribute messages to appropriate destinations
                ("ROUTER",      "audio") : ("AUDIO",      "inbox"),
                ("ROUTER", "whiteboard") : ("WHITEBOARD", "inbox"),
                # aggregate all output
                ("AUDIO",      "outbox") : ("", "outbox"),
                ("WHITEBOARD", "outbox") : ("", "outbox"),
                # shutdown routing, not sure if this will actually work, but hey!
                ("", "control") : ("ROUTER", "control"),
                ("ROUTER", "signal") : ("AUDIO", "control"),
                ("AUDIO", "signal") : ("WHITEBOARD", "control"),
                ("WHITEBOARD", "signal") : ("", "signal")
                },
            ),
        tokenlists_to_lines(),
        )

#/-------------------------------------------------------------------------
# Server side of the system
#

def LocalEventServer(whiteboardBackplane="WHITEBOARD", audioBackplane="AUDIO", port=1500):
    def configuredClientConnector():
        return clientconnector(whiteboardBackplane=whiteboardBackplane,
                               audioBackplane=audioBackplane,
                               port=port)
    return SimpleServer(protocol=clientconnector, port=port)

#/-------------------------------------------------------------------------
# Client side of the system
#
def EventServerClients(rhost, rport, 
                       whiteboardBackplane="WHITEBOARD",
                       audioBackplane="AUDIO"):
    # plug a TCPClient into the backplane

    loadingmsg = "Fetching sketch from server..."

    return Graphline(
            # initial messages sent to the server, and the local whiteboard
            GETIMG = Pipeline(
                        OneShot(msg=[["GETIMG"]]),
                        tokenlists_to_lines()
                    ),
            BLACKOUT =  OneShot(msg="CLEAR 0 0 0\r\n"
                                    "WRITE 100 100 24 255 255 255 "+loadingmsg+"\r\n"),
            NETWORK = TCPClient(host=rhost,port=rport),
            APPCOMMS = clientconnector(whiteboardBackplane=whiteboardBackplane,
                                       audioBackplane=audioBackplane),
            linkages = {
                ("GETIMG",   "outbox") : ("NETWORK",    "inbox"), # Single shot out
                ("APPCOMMS", "outbox") : ("NETWORK", "inbox"), # Continuous out

                ("BLACKOUT", "outbox") : ("APPCOMMS", "inbox"), # Single shot in
                ("NETWORK", "outbox") : ("APPCOMMS", "inbox"), # Continuous in
            } 
        )

#/-------------------------------------------------------------------------

class LocalPageEventsFilter(ConditionalSplitter): # This is a data tap/siphon/demuxer
    def condition(self, data):
        return (data == [["prev"]]) or (data == [["next"]])
    def true(self,data):
        self.send((data[0][0], "local"), "true")

SLIDESPEC = notepad+"/slide.%d.png"


def makeBasicSketcher(left=0,top=0,width=1024,height=768):
    #mydisplay = OpenGLDisplay(title="Kamaelia Whiteboard",width=width,height=height,background_colour=(255,255,255))
    ogl_display = OpenGLDisplay(title="Kamaelia Whiteboard",width=1280,height=1024,background_colour=(255,255,255))
    ogl_display.activate()
    OpenGLDisplay.setDisplayService(ogl_display)
    PygameDisplay.setDisplayService(ogl_display)
    return Graphline( CANVAS  = Canvas( position=(left,top+32),width=width,height=(height-(32+15)),notepad=notepad ),
                      PAINTER = Painter(),
                      PALETTE = buildPalette( cols=colours, order=colours_order, topleft=(left+64,top), size=32 ),
                      ERASER  = Eraser(left,top),
                      CLEAR = ClearPage(left+(64*5)+32*len(colours),top),
                      
                      SAVEDECK = SaveDeck(left+(64*9)+32*len(colours),top),
                      LOADDECK = LoadDeck(left+(64*8)+32*len(colours),top),
                      
                      SMARTBOARD = SmartBoard(),
                      
                      WEBCAM = Webcam(),
                      
                      CLOSEDECK = ClearScribbles(left+(64*10)+32*len(colours),top),

                      PAGINGCONTROLS = PagingControls(left+64+32*len(colours),top),
                      LOCALPAGINGCONTROLS = LocalPagingControls(left+(64*6)+32*len(colours),top),
                      LOCALPAGEEVENTS = LocalPageEventsFilter(),

                      HISTORY = CheckpointSequencer(lambda X: [["LOAD", SLIDESPEC % (X,)]],
                                                    lambda X: [["SAVE", SLIDESPEC % (X,)]],
                                                    lambda X: [["CLEAR"]],
                                                    initial = 1,
                                                    highest = num_pages,
                                                    notepad = notepad,
                                ),

                      PAINT_SPLITTER = TwoWaySplitter(),
                      LOCALEVENT_SPLITTER = TwoWaySplitter(),
                      DEBUG   = ConsoleEchoer(),
                      
                      TICKER = Ticker(position=(left,top+height-15),background_colour=(220,220,220),text_colour=(0,0,0),text_height=(17),render_right=(width),render_bottom=(15)),

                      linkages = {
                          ("CANVAS",  "eventsOut") : ("PAINTER", "inbox"),
                          ("PALETTE", "outbox")    : ("PAINTER", "colour"),
                          ("ERASER", "outbox")     : ("PAINTER", "erase"),

                          ("PAINTER", "outbox")    : ("PAINT_SPLITTER", "inbox"),
                          ("CLEAR","outbox")       : ("PAINT_SPLITTER", "inbox"),
                          ("PAINT_SPLITTER", "outbox")  : ("CANVAS", "inbox"),
                          ("PAINT_SPLITTER", "outbox2") : ("", "outbox"), # send to network
                          
                          ("SAVEDECK", "outbox") : ("CANVAS", "inbox"),
                          ("LOADDECK", "outbox") : ("CANVAS", "inbox"),
                          
                          ("CLOSEDECK", "outbox") : ("CANVAS", "inbox"),
                          
                          ("LOCALPAGINGCONTROLS","outbox")  : ("LOCALEVENT_SPLITTER", "inbox"),
                          ("LOCALEVENT_SPLITTER", "outbox2"): ("", "outbox"), # send to network
                          ("LOCALEVENT_SPLITTER", "outbox") : ("LOCALPAGEEVENTS", "inbox"),
                          ("", "inbox")        : ("LOCALPAGEEVENTS", "inbox"),
                          ("LOCALPAGEEVENTS", "false")  : ("CANVAS", "inbox"),
                          ("LOCALPAGEEVENTS", "true")  : ("HISTORY", "inbox"),

                          ("PAGINGCONTROLS","outbox") : ("HISTORY", "inbox"),
                          ("HISTORY","outbox")     : ("CANVAS", "inbox"),

                          ("CANVAS", "outbox")     : ("", "outbox"),
                          ("CANVAS","surfacechanged") : ("HISTORY", "inbox"),
                          
                          ("CANVAS", "toTicker") : ("TICKER", "inbox"),
                          ("CANVAS", "toFirstSlide") : ("HISTORY", "inbox"),
                          
                          ("SMARTBOARD", "colour") : ("PAINTER", "colour"),
                          ("SMARTBOARD", "erase") : ("PAINTER", "erase"),
                          ("SMARTBOARD", "toTicker") : ("TICKER", "inbox"),
                          
                          ("WEBCAM", "outbox") : ("CANVAS", "inbox"),
                          #("WEBCAM", "networkout") : ("", "outbox"), # send to network
                          },
                    )

if __name__=="__main__":
    mainsketcher = \
        Graphline( SKETCHER = makeBasicSketcher(width=1024,height=768),
                   CONSOLE = CommandConsole(),
                   linkages = { ('','inbox'):('SKETCHER','inbox'),
                                ('SKETCHER','outbox'):('','outbox'),
                                ('CONSOLE','outbox'):('SKETCHER','inbox'),
                              }
                     )
    # primary whiteboard
    Pipeline( SubscribeTo("WHITEBOARD"),
              TagAndFilterWrapper(mainsketcher),
              PublishTo("WHITEBOARD")
            ).activate()
            
    # primary sound IO - tagged and filtered, so can't hear self
    Pipeline( SubscribeTo("AUDIO"),
              TagAndFilterWrapperKeepingTag(
                  Pipeline(
                      RawAudioMixer(),
                      SoundOutput(),
                      ######
                      SoundInput(),
                  ),
              ),
              PublishTo("AUDIO"),
            ).activate()

    rhost, rport, serveport = parseOptions()

    # setup a server, if requested
    if serveport:
        LocalEventServer("WHITEBOARD", "AUDIO", port=serveport).activate()


    # connect to remote host & port, if requested
    if rhost and rport:
        EventServerClients(rhost, rport, "WHITEBOARD", "AUDIO").activate()

#    sys.path.append("../Introspection")
#    from Profiling import FormattedProfiler
#    
#    Pipeline(FormattedProfiler( 20.0, 1.0),
#             ConsoleEchoer()
#            ).activate()


    Backplane("WHITEBOARD").activate()
    
    Backplane("AUDIO").run()
    

    