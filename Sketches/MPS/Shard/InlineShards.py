import inspect
import re
#
# This is where we will put shards that come from *inside* the main method.
#
def MOUSEBUTTONDOWN_handler(self):
    if  event.button == 1:
        self.drawing = True
    elif event.button == 3:
        self.oldpos = None
        self.drawBG()
        self.blitToSurface()

def MOUSEBUTTONUP_handler(self):
    if event.button == 1:
        self.drawing = False
        self.oldpos = None

def MOUSEMOTION_handler(self):
    if self.drawing and self.innerRect.collidepoint(*event.pos):
        if self.oldpos == None:
            self.oldpos = event.pos
        else:
            pygame.draw.line(self.display, (0,0,0), self.oldpos, event.pos, 3)
            self.oldpos = event.pos
        self.blitToSurface()

def SetEventOptions(self):
    self.addListenEvent("MOUSEBUTTONDOWN")
    self.addListenEvent("MOUSEBUTTONUP")
    self.addListenEvent("MOUSEMOTION")

def __INIT__(self):
    self.backgroundColour = argd.get("bgcolour", (124,124,124))
    self.foregroundColour = argd.get("fgcolour", (0,0,0))
    self.margin = argd.get("margin", 8)
    self.oldpos = None
    self.drawing = False

    self.size = argd.get("size", (200,200))
    self.innerRect = pygame.Rect(10, 10, self.size[0]-20, self.size[1]-20)

    if argd.get("msg", None) is None:
        argd["msg"] = ("CLICK", self.id)
    self.eventMsg = argd.get("msg", None)
    if argd.get("transparent",False):
        transparency = argd.get("bgcolour", (124,124,124))
    else:
        transparency = None
    self.disprequest = { "DISPLAYREQUEST" : True,
                         "callback" : (self,"callback"),
                         "events" : (self, "inbox"),
                         "size": self.size,
                         "transparency" : transparency }

    if not argd.get("position", None) is None:
        self.disprequest["position"] = argd.get("position",None)

#
# Reuseable IShards
#

def ShutdownHandler(self):
    while self.dataReady("control"):
        cmsg = self.recv("control")
        if isinstance(cmsg, producerFinished) or isinstance(cmsg, shutdownMicroprocess):
            self.send(cmsg, "signal")
            done = True

def LoopOverPygameEvents(self):
    while self.dataReady("inbox"):
        for event in self.recv("inbox"):
            if event.type == pygame.MOUSEBUTTONDOWN:
                exec self.getIShard("MOUSEBUTTONDOWN")
            elif event.type == pygame.MOUSEBUTTONUP:
                exec self.getIShard("MOUSEBUTTONUP")
            elif event.type == pygame.MOUSEMOTION:
                exec self.getIShard("MOUSEMOTION")

def RequestDisplay(self):
    displayservice = PygameDisplay.getDisplayService()
    self.link((self,"display_signal"), displayservice)
    self.send( self.disprequest, "display_signal")

def GrabDisplay(self):
    self.display = self.recv("callback")
