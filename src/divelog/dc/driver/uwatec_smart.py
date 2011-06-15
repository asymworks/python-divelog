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

'''
Uwatec Smart protocol driver

Implements a driver for the Uwatec Smart line of dive computers, including the
Smart Pro, Galileo Sol, Aladin Tec, Aladin Tec 2G, Smart Com, Smart Tec, and
Smart Z.  This driver may be used with any computer which implements the smart 
protocol may be used; however, automatic model identification may not succeed.
'''

import datetime
import struct

from divelog.dc import BaseDriver

try:
    import irsocket
except ImportError:
    irsocket = None

class SmartDriver(BaseDriver):
    # Magic Attributes for the register_driver method
    NAME = 'smart'
    DESCRIPTION = 'Uwatec Smart protocol driver'
    
    @classmethod
    def on_register(cls):
        if irsocket is None:
            return False
        return True
    
    # Transfer Chunk Size
    CHUNK_SIZE = 16
    
    # List of Uwatec Smart Models and suggested parsers
    MODELS = [
        { 'name': 'Smart Pro',      'id': 0x10, 'parser': None },
        { 'name': 'Galileo Sol',    'id': 0x11, 'parser': None },
        { 'name': 'Aladin Tec',     'id': 0x12, 'parser': None },
        { 'name': 'Aladin Tec 2G',  'id': 0x13, 'parser': 'AladinTec2G' },
        { 'name': 'Smart Com',      'id': 0x14, 'parser': None },
        { 'name': 'Smart Tec',      'id': 0x18, 'parser': None },
        { 'name': 'Smart Z',        'id': 0x1c, 'parser': None },
    ]
    
    # Class Constructor
    def __init__(self, **kwargs):
        '''
        Class Constructor
        
        Create a new instance of the Smart Driver.  Creates a new IrDA socket
        and initializes class members to None.  Note that if irsocket is not
        installed, the constructor will throw an exception.
        '''
        super(SmartDriver, self).__init__(**kwargs)
        
        # Create the IrDA Socket
        if irsocket is None:
            raise RuntimeError('Cannot initialize %s: irsocket is not installed', self.__class__.name)
        self._socket = irsocket.irsocket()
        
        self._addr = None
        self._model = None
        self._parser = None
        self._serial = None
        self._ticks = None
        self._token = None
        
    def _sendcmd(self, command, recvlen):
        self._socket.sendall(command)
        return self._socket.recv(recvlen)
        
    # Connect to a Device
    def connect(self, device):
        '''
        Connect to a Smart Device
        
        Connects to the device given in the 'device' argument.  The device
        should be one returned previously by the discover() call.  This call
        performs all handshaking and reads basic device information including
        the computer model, serial number, and current timestamp.
        '''
        if not 'addr' in device:
            raise KeyError('Missing \'addr\' key in device passed to %s.connect()' % self.__class__.name)
        
        self._addr = device['addr']
        self._socket.connect(self._addr)
        self._socket.settimeout(2000)
        
        # Handshake with the Smart device
        r1 = self._sendcmd('\x1b', 1)
        r2 = self._sendcmd('\x1c\x10\x27\x00\x00', 1)
        if (r1 != '\x01') or (r2 != '\x01'):
            raise IOError("Failed to handshake with Uwatec Smart device")
        
        # Get Device Information
        model_id = struct.unpack('<B', self._sendcmd('\x10', 1))[0]
        self._serial = struct.unpack('<L', self._sendcmd('\x14', 4))[0]
        self._ticks = struct.unpack('<L', self._sendcmd('\x1a', 4))[0]
        
        # Find Model Name
        self._model = "Uwatec Smart Device (id:%d)" % model_id
        self._parser = None
        for mdl in self.MODELS:
            if model_id == mdl['id']:
                self._model = mdl['name']
                self._parser = mdl['parser']
                break
        
    # Disconnect from the Device
    def disconnect(self):
        '''
        Disconnect a connected device
        '''
        if self._socket:
            self._socket.close()
            self._socket = None
            self._addr = None
        
    # Discover Devices on the IrDA bus
    def discover(self):
        '''
        Device Discovery Method
        
        Searches for devices on the IrDA bus which implement the Uwatec Smart
        protocol.  This returns a list of device entries, each of which have
        a 'addr' and 'name' key.  The dictionary should be passed to connect()
        to connect to the desired dive computer.
        '''
        irdevs = self._socket.enum_devices()
        
        if not irdevs:
            return []
        
        dcdevs = []
        for dev in irdevs:
            if  'UWATEC'  in dev['name'].upper() or \
                'ALADIN'  in dev['name'].upper() or \
                'GALILEO' in dev['name'].upper() or \
                'SMART'   in dev['name'].upper():
                
                dcdevs.append(dev)
        return dcdevs
    
    # Return the number of bytes in the current transfer
    def get_bytecount(self):
        '''
        Return the number of bytes to transfer
        
        Returns the number of bytes that will be transferred to download all
        dives logged past the currently-set token.  This method does not set
        a new token, and can be called without side-effects.
        '''
        cmd = '\xc6%s\x10\x27\x00\x00' % struct.pack('<L', self._token or 0)
        return struct.unpack('<L', self._sendcmd(cmd, 4))[0]
    
    # Return current Token
    def issue_token(self):
        '''
        Issue a new Token
        
        Generates and returns a new token for this dive computer.  A Token is
        used to mark the last dive downloaded, so that subsequent downloads
        only download new dives.
        
        The token returned from this function should be saved, and then passed
        to set_token() prior to downloading new dives.
        '''
        return "%d" % self._ticks
    
    # Set the Token
    def set_token(self, token):
        '''
        Set the current Token
        
        Sets the token for this dive computer transaction.  Only dives after
        the given token will be downloaded.  A Token is used to mark the last 
        dive downloaded, so that subsequent downloads only download new dives.
        '''
        self._token = long(token or 0)
        
    # Transfer Dive Data
    def transfer(self, progressObj = None):
        '''
        Transfer Dive Data
        
        Transfers dive data from the dive computer.  This method will download
        all dives logged past the currently-set token and return a list of
        binary dive data.  Each entry in the list represents a single dive as
        logged by the computer, and can be decoded using the appropriate parser
        object.
        '''
        num = self.get_bytecount()
        
        if num == 0:
            return []
        
        cmd = '\xc4%s\x10\x27\x00\x00' % struct.pack('<L', self._token or 0)
        nb = struct.unpack('<L', self._sendcmd(cmd, 4))[0]
        
        if nb != num + 4:
            raise RuntimeError('Mismatch in returned byte counts in %s.transfer()' % self.__class__.name)
        
        if hasattr(progressObj, 'start') and callable(progressObj.start):
            progressObj.start(num)
        
        data = ''
        while num > 0:
            if num > self.CHUNK_SIZE:
                s = self._socket.recv(self.CHUNK_SIZE)
            else:
                s = self._socket.recv(num)
            
            num -= len(s)
            data += s
            
            if hasattr(progressObj, 'update') and callable(progressObj.update):
                progressObj.update(len(data))
            
        if hasattr(progressObj, 'finish') and callable(progressObj.finish):
            progressObj.finish()
        
        # Split data into dives.  This implementation intentionally does not
        # use the str.split() method in case there is a A5A5 5A5A DWORD buried
        # in the profile or in other legitimate data (e.g. a timestamp).  This
        # could occur sometime in 2024.  We are future-proof!
        _hdr = '\xa5\xa5\x5a\x5a'
        _pos = 0
        _len = 0
        dives = []
        
        while _pos < len(data) - 4:
            if data[_pos:_pos+4] != _hdr:
                raise RuntimeError('Invalid or corrupt dive data in %s.transfer()' % self.__class__.name)
            _len = struct.unpack_from('<L', data, _pos+4)[0]
            
            if _len <= 0:
                raise RuntimeError('Length of dive %d is zero or negative in %s.transfer()' % (len(dives)+1, self.__class__.name))
            if _pos + _len > len(data):
                raise RuntimeError('Length of dive %d extends past received data in %s.transfer()' % (len(dives)+1, self.__class__.name))
            dives.append(data[_pos:_pos+_len])
            _pos += _len
        
        # Return list of dive data
        return dives
    
    #-------------------------------------------------------------------------
    # Properties
    
    @property
    def curtime(self):
        '''
        Get the dive computer's current time of day
        '''
        td = datetime.timedelta(seconds = self._ticks / 2)
        return datetime.datetime(2000, 1, 1) + td
    
    @property
    def model(self):
        '''
        Get the dive computer's model name
        '''
        return self._model
    
    @property
    def parser(self):
        '''
        Get the suggested parser class name
        '''
        return self._parser
    
    @property
    def serial(self):
        '''
        Get the dive computer's serial number
        '''
        return "%d" % self._serial