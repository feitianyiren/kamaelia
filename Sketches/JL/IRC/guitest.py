#! /usr/bin/env python
from Kamaelia.Internet.TCPClient import TCPClient
from Kamaelia.Chassis.Graphline import Graphline
from Kamaelia.Util.Fanout import Fanout
from Kamaelia.Util.PureTransformer import PureTransformer
import sys ; sys.path.append("../../JL/IRC/")
from IRCClient import *
import string

def formatter(text):
    return text.split()

def ComplexIRCClientPrefab(host="127.0.0.1",
                          port=6667,
                          nick="kamaeliabot",
                          nickinfo="Kamaelia",
                          defaultChannel="#kamaeliatest",
                          IRC_Handler=IRC_Client):
    return Graphline(
        CLIENT = TCPClient(host, port),
        PROTO = IRC_Handler(nick, nickinfo, defaultChannel),
        FORMAT = PureTransformer(formatter),
        SPLIT = Fanout(["toGraphline", "toTCP"]),
        linkages = {
              ("CLIENT" , "outbox") : ("PROTO" , "inbox"),
              ("PROTO"  , "outbox") : ("SPLIT", "inbox"),
              ("PROTO"  , "heard")  : ("SELF", "outbox"), #passthrough
              ("SELF"  , "inbox") : ("FORMAT", "inbox" ), #passthrough
              ("FORMAT", "outbox") : ("PROTO" , "talk"), 
              ("SELF"  , "control") : ("PROTO" , "control"), #passthrough
              ("PROTO"  , "signal") : ("CLIENT", "control"),
              ("CLIENT" , "signal") : ("SELF" , "signal"), #passthrough
              ("SPLIT", "toGraphline") : ("SELF", "sendCopy"), #passthrough
              ("SPLIT", "toTCP") : ("CLIENT", "inbox"),
              }
        )

if __name__ == '__main__':
    from Kamaelia.Util.Console import ConsoleReader
    from TextDisplayer import TextDisplayer
    from Textbox import Textbox
    from Kamaelia.Chassis.Graphline import Graphline
    Graphline(
        irc = ComplexIRCClientPrefab(host="irc.freenode.net", nick="kamaeliabot", defaultChannel="#kamtest"),
        display1 = TextDisplayer(screen_width = 800,screen_height = 300, position=(0,0)),
        reader = Textbox(screen_width = 800,screen_height = 300, position = (0, 340)),
        linkages = {
            ("reader", "outbox") : ("irc", "inbox"),
            ("irc", "outbox") : ("display1", "inbox"),
            ("irc", "sendCopy") : ("display1", "inbox")
            }
            
    ).run()