# =============================================================================
# 
# Copyright (C) 2011 Asymworks, LLC.  All Rights Reserved.
# www.pydivelog.com / info@pydivelog.com
# 
# This file is part of the Python divecomputer Package (python-divecomputer)
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# 
# =============================================================================

import base64
from divelog.dc import BaseParser

class ParseError(Exception):
    pass

class NullParser(BaseParser):
    NAME = 'null'
    DESCRIPTION = 'Null parser which simply returns the base64-encoded data'

    def __init__(self, *args):
        pass

    def parse(self, data, *args, **kwargs):
        dive = {'data': base64.encode(data)}
        dive.update(kwargs)
        return dive
    