#!/usr/bin/env python
#
# (C) 2004 British Broadcasting Corporation and Kamaelia Contributors(1)
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

from distutils.core import setup

setup(name = "Kamaelia",
      version = "0.4.0",
      description = "Kamaelia - Multimedia & Server Development Kit",
      author = "Michael & Kamaelia Contributors",
      author_email = "ms_@users.sourceforge.net",
      url = "http://kamaelia.sourceforge.net/",
      packages = ["Kamaelia",
                  "Kamaelia.Util",
                  "Kamaelia.Protocol",
                  "Kamaelia.Internet",
                  "Kamaelia.Internet.Simulate",
                  "Kamaelia.Codec",
                  "Kamaelia.Chassis",
                  "Kamaelia.File",
                  "Kamaelia.UI",
                  "Kamaelia.UI.Tk",
                  "Kamaelia.UI.MH",
                  "Kamaelia.UI.Pygame",  
                  "Kamaelia.Automata",
                  "Kamaelia.Visualisation",
                  "Kamaelia.Visualisation.Axon",
                  "Kamaelia.Visualisation.PhysicsGraph",
                  "Kamaelia.Codec",
                  "Kamaelia.Support",
                  "Kamaelia.Support.Data",
                  "Kamaelia.Support.Particles",
                  "Kamaelia.Support.Tk",
                  "Kamaelia.Device",
                  "Kamaelia.Device.DVB",
                  ""],
#      scripts = ['Tools/KamaeliaPresent.py'],
      long_description = """
"""
      )