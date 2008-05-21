#!/usr/bin/env python
#
# Copyright (C) 2006 British Broadcasting Corporation and Kamaelia Contributors(1)
#	 All Rights Reserved.
#
# You may only modify and redistribute this under the terms of any of the
# following licenses(2): Mozilla Public License, V1.1, GNU General
# Public License, V2.0, GNU Lesser General Public License, V2.1
#
# (1) Kamaelia Contributors are listed in the AUTHORS file and at
#	 http://kamaelia.sourceforge.net/AUTHORS - please extend this file,
#	 not this notice.
# (2) Reproduced in the COPYING file, and at:
#	 http://kamaelia.sourceforge.net/COPYING
# Under section 3.5 of the MPL, we are using this text since we deem the MPL
# notice inappropriate for this file. As per MPL/GPL/LGPL removal of this
# notice is prohibited.
#
# Please contact us via: kamaelia-list-owner@lists.sourceforge.net
# to discuss alternative licensing.
# -------------------------------------------------------------------------
#
"""\
=================
UnseenOnly component
=================

This component forwards on any messages it receives that it has not
seen before.

Example Usage
-------------

Lines entered into this setup will only be duplicated on screen the
first time they are entered.

pipeline(
    ConsoleReader()
    UnseenOnly()
    ConsoleEchoer()
).run()

"""
from PureTransformer import PureTransformer
    
class UnseenOnly(PureTransformer):
    def __init__(self):
        super(UnseenOnly, self).__init__()
        self.seen = {}
        
    def processMessage(self, msg):
        if not self.seen.get(msg, False):
            self.seen[msg] = True
            return msg