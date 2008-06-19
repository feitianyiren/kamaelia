#!/usr/bin/env python
#
# Copyright (C) 2005 British Broadcasting Corporation and Kamaelia Contributors(1)
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

"""\
===========================
Simple Pygame drawing board
===========================

A simple drawing board for the pygame display service.

Use your left mouse button to draw to the board and the
right to erase your artwork.

"""


import pprocess
import pygame
import Axon
import math
from Axon.Ipc import producerFinished
from Kamaelia.UI.PygameDisplay import PygameDisplay
class Paint(Axon.Component.component):
   """\
   MagnaDoodle(...) -> A new MagnaDoodle component.

   A simple drawing board for the pygame display service.

   (this component and its documentation is heaviliy based on Kamaelia.UI.Pygame.Button)

   Keyword arguments:
   
   - position     -- (x,y) position of top left corner in pixels
   - margin       -- pixels margin between caption and button edge (default=8)
   - bgcolour     -- (r,g,b) fill colour (default=(224,224,224))
   - fgcolour     -- (r,g,b) text colour (default=(0,0,0))
   - transparent  -- draw background transparent if True (default=False)
   - size         -- None or (w,h) in pixels (default=None)
   
   """
   
   Inboxes = { "inbox"    : "Receive events from PygameDisplay",
               "control"  : "For shutdown messages",
               "callback" : "Receive callbacks from PygameDisplay",
               "drawn"    : "Information on what was drawn on other Paint canvas"
             }
   Outboxes = { "outbox" : "Used to talk to other Paint canvas",
                "signal" : "For shutdown messages",
                "display_signal" : "Outbox used for communicating to the display surface" }
   
   def __init__(self, caption=None, position=None, margin=8, bgcolour = (124,124,124), fgcolour = (0,0,0), msg=None,
                transparent = False, size=(200,200), selectedColour=(0,0,0)):
      """x.__init__(...) initializes x; see x.__class__.__doc__ for signature"""
      super(Paint,self).__init__()

      self.backgroundColour = bgcolour
      self.foregroundColour = fgcolour
      self.margin = margin
      self.oldpos = None
      self.drawing = False
      self.shape = "line"
      self.size = size
      self.selectedColour = selectedColour
      self.innerRect = pygame.Rect(10, 10, self.size[0]-20, self.size[1]-20)

      if msg is None:
         msg = ("CLICK", self.id)
      self.eventMsg = msg
      if transparent:
         transparency = bgcolour
      else:
         transparency = None
      self.disprequest = { "DISPLAYREQUEST" : True,
                           "callback" : (self,"callback"),
                           "events" : (self, "inbox"),
                           "size": self.size,
                           "transparency" : transparency }

      if not position is None:
        self.disprequest["position"] = position

   def waitBox(self,boxname):
      """Generator. yields 1 until data ready on the named inbox."""
      waiting = True
      while waiting:
        if self.dataReady(boxname): return
        else: yield 1

   def drawBG(self):
      self.display.fill( (255,0,0) )
      self.display.fill( self.backgroundColour, self.innerRect )
      
   def floodFill(self, x, y, newColour, oldColour):
       colour = self.display.get_at((x,y))
       if (self.display.get_at((x,y)) == oldColour and self.display.get_at((x,y)) != newColour):
           self.display.set_at((x,y),newColour)
           self.floodFill(x + 1, y,     newColour, oldColour)
           self.floodFill(x - 1, y,     newColour, oldColour)
           self.floodFill(x,     y + 1, newColour, oldColour)
           self.floodFill(x,     y - 1, newColour, oldColour)
           
   def main(self):
      """Main loop."""
      displayservice = PygameDisplay.getDisplayService()
      self.link((self,"display_signal"), displayservice)

      self.send( self.disprequest,
                  "display_signal")

      for _ in self.waitBox("callback"): yield 1
      self.display = self.recv("callback")
      self.drawBG()
      self.blitToSurface()

      self.send({ "ADDLISTENEVENT" : pygame.MOUSEBUTTONDOWN,
                  "surface" : self.display},
                  "display_signal")

      self.send({ "ADDLISTENEVENT" : pygame.MOUSEBUTTONUP,
                  "surface" : self.display},
                  "display_signal")

      self.send({ "ADDLISTENEVENT" : pygame.MOUSEMOTION,
                  "surface" : self.display},
                  "display_signal")

      self.send({ "ADDLISTENEVENT" : pygame.KEYDOWN,
		  "surface" : self.display},
		  "display_signal")


      done = False
      while not done:
         if not self.anyReady():
             print "in this box"
             self.pause()
         yield 1
         while self.dataReady("control"):
            cmsg = self.recv("control")
            if isinstance(cmsg, producerFinished) or isinstance(cmsg, shutdownMicroprocess):
               self.send(cmsg, "signal")
               done = True
         while self.dataReady("drawn"):
                print "drawn"
                for x in self.recv("drawn"):
                    if x == "c":
                        self.oldpos = None
                        self.drawBG()
                        self.blitToSurface()
         while self.dataReady("inbox"):
            for event in self.recv("inbox"):
                if isinstance(event, tuple):
                    print "here"
                    if event[0] == 'circle':
                        pygame.draw.circle(self.display, (255,0,0), event[1], event[2], 0)
                        self.blitToSurface()
                    if event[0] == 'line':
                        pygame.draw.line(self.display, (0,0,0), event[1], event[2], 3)
                        self.blitToSurface()
                    if event[0] == 'colour':
                        self.selectedColour = event[1]
                    break
                if event == "clear":
                    print "YAY!"
                    self.oldpos = None
                    self.drawBG()
                    self.blitToSurface()
                    break
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.shape == "circle":
                        if event.button == 1:
                            self.oldpos = event.pos
                            self.drawing = True
                    if self.shape == "line":
                        if event.button == 1:
                            self.drawing = True
                    if event.button == 3:
                        self.floodFill(event.pos[0],event.pos[1],(255,0,0,0),self.display.get_at(event.pos))
                      #  self.oldpos = None
                      #  self.drawBG()
                      #  self.blitToSurface()
                      #  self.send(("clear",), "outbox")
                elif event.type == (pygame.KEYDOWN):
                    if event.key == pygame.K_c:
                       self.floodFill(100,100,(240,224,143,0),self.display.get_at((100,100)))
                    elif event.key == pygame.K_l:
                       self.shape = "line"


                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if self.shape == "circle":
                        rad = math.sqrt(((event.pos[0]-self.oldpos[0])**2)+((event.pos[1]-self.oldpos[1])**2))
                        pygame.draw.circle(self.display, self.selectedColour, self.oldpos, rad, 0)
                        circle = ("circle", self.oldpos, rad)
                        self.send((circle,), "outbox")
                        self.blitToSurface()
                    self.drawing = False
                    self.oldpos = None
                elif event.type == pygame.MOUSEMOTION:
                    if self.shape == "line":
                        if self.drawing and self.innerRect.collidepoint(*event.pos):
                              if self.oldpos == None:
                                 self.oldpos = event.pos
                              else:
                                 pygame.draw.line(self.display, self.selectedColour, self.oldpos, event.pos, 3)
                                 line = ("line", self.oldpos, event.pos)
                                 self.send((line,), "outbox")
                                 self.oldpos = event.pos
                              self.blitToSurface()
         self.pause()
         yield 1

   def blitToSurface(self):
       self.send({"REDRAW":True, "surface":self.display}, "display_signal")

__kamaelia_components__  = ( Paint, )

                  
if __name__ == "__main__":
   from Kamaelia.Util.ConsoleEcho import consoleEchoer
   from pygame.locals import *
   from XYPad import XYPad
   from Kamaelia.Util.Clock import CheapAndCheerfulClock as Clock
   
   import sys; sys.path.append("../../../MPS/pprocess/");
   from MultiPipeline import ProcessGraphline







  # clock2.link((clock2, "outbox"), (xyPad2, "newframe"))
   ProcessGraphline(
        COLOURS = XYPad(size=(255, 255), bouncingPuck = False, position = (70, 0),
                   bgcolour=(0, 0, 0), fgcolour=(255, 255, 255),
                   positionMsg="p2"),
        WINDOW1 = Paint(bgcolour=(100,100,172),position=(0,0) ),
        WINDOW2 = Paint(bgcolour=(172,100,100),position=(0,0) ),
        linkages = {
            ("WINDOW1", "outbox") : ("WINDOW2", "inbox"),
            ("COLOURS", "outbox") : ("WINDOW1", "inbox"),
        },
        __debug = True,
   ).run()
# Licensed to the BBC under a Contributor Agreement: THF/DK