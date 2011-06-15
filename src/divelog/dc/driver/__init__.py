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

import datetime
import pickle

from divelog.dc import BaseDriver

class FileDriver(BaseDriver):
    '''
    File device driver.  Reads data from a pickled file.
    '''
    
    NAME = 'file'
    DESCRIPTION = 'File Driver'
    
    def __init__(self, filename=None, **kwargs):
        self._filename = filename
        self._file = None
        
    def discover(self):
        if not self._filename:
            return []
        return [{'addr' : self._filename, 'name' : '<File: %s>' % self._filename}]
    
    def connect(self, device):
        self._file = open(device['addr'], 'rb')
        
    def disconnect(self):
        self._file.close()
        
    def get_bytecount(self):
        return 0
    
    def issue_token(self):
        return ''
    
    def set_token(self, token):
        pass
    
    def transfer(self, progressObj = None):
        return pickle.load(self._file)
        
    @property
    def model(self):
        return 'File'
    
    @property
    def parser(self):
        '''
        Get the suggested parser class name
        '''
        return None
    
    @property
    def serial(self):
        return '0'
    
    @property
    def curtime(self):
        return datetime.datetime.now()