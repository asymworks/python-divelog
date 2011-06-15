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
Uwatec Smart parser library

Implements parsers for the Uwatec Smart line of dive computers, including the
Smart Pro, Galileo Sol, Aladin Tec, Aladin Tec 2G, Smart Com, Smart Tec, and
Smart Z.  Each device uses a slightly different header and profile format, so
the client should choose the proper device based on the dive computer model.
'''

import base64
import datetime
import logging
import struct

log = logging.getLogger(__name__)

from divelog.dc import BaseParser, BaseAdapter
from divelog.dc.parser import ParseError

class SmartAdapter(BaseAdapter):
    def __init__(self, data):
        super(SmartAdapter, self).__init__(data)
        self._profile = None
    
    def dive_datetime(self):
        return self._data['date'] + datetime.timedelta(seconds = 60*15*(self._data['utc_offset'] or 0))
    
    def repetition(self):
        return self._data['rep_no']
    
    def interval(self):
        return self._data['interval']
    
    def duration(self):
        return self._data['duration']

    def max_depth(self):
        return float(self._data['max_depth'])/100
    
    def avg_depth(self):
        return float(self._data['avg_depth'])/100
    
    def air_temp(self):
        return float(self._data['air_temp'])/10
    
    def max_temp(self):
        return float(self._data['max_temp'])/10
    
    def min_temp(self):
        return float(self._data['min_temp'])/10
        
    def mixes(self):
        return {
            'gas_1': {
                'n2':   100-self._data['ppO2_1'],
                'o2':       self._data['ppO2_1'],
                'he':   0,
                'h2':   0,
                'ar':   0
            },
            
            'gas_2': {
                'n2':   100-self._data['ppO2_2'],
                'o2':       self._data['ppO2_2'],
                'he':   0,
                'h2':   0,
                'ar':   0
            },
            
            'gas_d': {
                'n2':   100-self._data['ppO2_3'],
                'o2':       self._data['ppO2_3'],
                'he':   0,
                'h2':   0,
                'ar':   0
            },
        }
        
    def profile(self):
        if not self._profile:
            self._profile = []
            for wp in self._data['profile']:
                if 'alarms' in wp:
                    alarms = ','.join(wp['alarms'])
                else:
                    alarms = ''
                                
                self._profile.append({
                    'time':     wp['time'],
                    'depth':    float(wp['depth'])/100,
                    'temp':     float(wp['temp'])/10,
                    'alarms':   alarms,
                })
                
        return self._profile
    
    def vendor(self):
        return {
            'mode':                 self._data['mode'],
            'battery':              self._data['batt'],
            'alarms':               self._data['alarms'],
            'microbubble_level':    self._data['mbLevel'],
        }
    
    def computer(self):
        return {
            'vendor':               'Uwatec',
            'model':                self._data['model'],
            'driver':               self._data['driver'],
            'serial':               self._data['serial'],
        }

class BaseSmartParser(BaseParser):
    '''
    Abstract Base Class for Uwatec Smart device parsers
    
    Implements common unpacking methods to retrieve signed and unsigned numbers
    and to convert timestamps into date/time values
    '''    
    def smart_ticks_to_datetime(self, ticks, utc_offset=None):
        '''Convert a Smart tick count to a UTC date/time'''
        td = datetime.timedelta(seconds = ticks / 2)
        if utc_offset:
            td += datetime.timedelta(seconds = utc_offset * 15 * 60)
        return datetime.datetime(year = 2000, month = 1, day = 1) + td
    
    def read_datetime(self, data, offset):
        '''Read a date/time value from the data'''
        return self.smart_ticks_to_datetime(struct.unpack_from('<L', data, offset)[0])
    
    def read_ulong(self, data, offset):
        '''Read an unsigned long value from the data'''
        return struct.unpack_from('<L', data, offset)[0]
    
    def read_uint(self, data, offset):
        '''Read an unsigned integer value from the data'''
        return struct.unpack_from('<H', data, offset)[0]
    
    def read_sshort(self, data, offset):
        '''Read a signed byte value from the data'''
        return struct.unpack_from('<b', data, offset)[0]
    
    def read_ushort(self, data, offset):
        '''Read an unsigned byte value from the data'''
        return struct.unpack_from('<B', data, offset)[0]
    
    def smart_dti_identify(self, data, offset):
        '''Return the number of '1' bits in the DTI'''
        nbits = 0
        for i in range(16):       # Assume 16 bytes max in a DTI
            byte = self.read_ushort(data, offset + i)
            for j in range(8):
                mask = 1 << (7 - j)
                if byte & mask == 0:
                    return nbits
                nbits += 1
                
        return -1
    
    def smart_fix_signbit(self, value, nbits):
        if nbits == 0 or nbits > 32:
            return 0
        
        sgnbit = (1 << (nbits - 1))
        mask = (0xFFFFFFFF << nbits) & 0xFFFFFFFF
        
        if (value & sgnbit) == sgnbit:
            return value | mask
        return value & ~mask
    
    def process_dti(self, data, cur_pos, dti):
        # Advance past initial DTI bytes if necessary
        cur_pos += dti['bits'] / 8
        nbits = 0
        value = 0
        n = dti['bits'] % 8
        if n > 0:
            nbits = 8 - n
            value = (0xFF >> n) & self.read_ushort(data, cur_pos)
            
            if dti['ignore_type_bits']:
                nbits = 0
                value = 0
            
            cur_pos += 1
        
        # Ensure that we have enough bytes remaining
        if cur_pos + dti['extra'] > len(data):
            raise ParseError('Unexpected end of data')
        
        # Process data bytes
        for _ in range(dti['extra']):
            nbits += 8
            value = value << 8
            value += self.read_ushort(data, cur_pos)
            cur_pos += 1
    
        # Fix the Sign Bit
        svalue = self.smart_fix_signbit(value, nbits)
        svalue = struct.unpack('<l', struct.pack('<L', int(svalue)))[0]
        
        # Return the Data
        return (cur_pos, value, svalue)
    
    def init_parser(self):
        '''Initialize profile state'''
        class State(object):
            pass
        
        self._state = State()
        
        self._state.time = 0
        self._state.complete = 0
        
        self._state.alarms = []
        self._state.cal = 0
        self._state.depth = 0
        self._state.temp = 0
        
        self._state.has_alarms = False
        self._state.has_depth = False
        self._state.has_temp = False
        
    def alarm_name(self, idx, mask, alarm_table=[]):
        name = 'alarm%d_%d' % (idx, mask)
        for a in alarm_table:
            if a['idx'] == idx and a['mask'] == mask:
                return a['name']
        return name
    
    def update_alarms(self, idx, value, alarm_table=[]):
        # Clear existing alarms
        _a = self._state.alarms
        for a in _a:
            if a['idx'] == idx and (value & a['mask'] == 0):
                self._state.alarms.remove(a)
                
        # Set new alarms
        m = 1
        while m <= value:
            if value & m == m:
                name = self.alarm_name(idx, m, alarm_table)
                self._state.alarms.append({'idx': idx, 'mask': m, 'name': name})
                
            m = m << 1
    
    def parse_dti(self, dti, value, svalue, profile, alarm_table=[]):
        #log.debug('Processing DTI %s_%s' % ('abs' if dti['abs'] else 'delta', dti['name']))
        
        # Parse Temperature
        if dti['name'] == 'temp':
            if dti['abs']:
                self._state.temp = value * 4
                self._state.has_temp = True
            else:
                self._state.temp += svalue * 4
        
        # Parse Depth
        elif dti['name'] == 'depth':
            if dti['abs']:
                self._state.depth = value * 2
                if self._state.cal == 0:
                    self._state.cal = self._state.depth
                self._state.has_depth = True
            else:
                self._state.depth += svalue * 2
            self._state.complete = 1
        
        # Parse Alarms
        elif dti['name'] == 'alarms':
            self.update_alarms(dti['idx'], value, alarm_table)
        
        # Parse Time
        elif dti['name'] == 'time':
            self._state.complete = value
            
        # Unknown DTI
        else:
            log.warning('Unrecognized DTI: %s' % (dti['name']))
        
        # Setup a Profile Entry
        while self._state.complete > 0:
            entry = {'time': self._state.time}
            
            if self._state.has_temp:
                entry['temp'] = self._state.temp
            
            if self._state.has_depth:
                entry['depth'] = self._state.depth - self._state.cal
            
            if len(self._state.alarms) > 0:    
                entry['alarms'] = [a['name'] for a in self._state.alarms]
            
            profile.append(entry)
            self._state.time += 4
            self._state.complete -= 1
            
    def parse_profile(self, data):
        _pos = 0
        _profile = []
        
        while _pos < len(data):
            # Identify the DTI
            idx = self.smart_dti_identify(data, _pos)
            if idx > len(self.DTI_TABLE):
                raise ParseError('Invalid DTI index (%d)' % idx)
            
            # Process the DTI 
            (_pos, value, svalue) = self.process_dti(data, _pos, self.DTI_TABLE[idx])
            
            # Parse the DTI Value into the Profile
            self.parse_dti(self.DTI_TABLE[idx], value, svalue, _profile, self.ALARM_TABLE)
            
        return _profile
        
class AladinTec2G(BaseSmartParser):
    # Magic Attributes for the register_parser method
    NAME = 'AladinTec2G'
    DESCRIPTION = 'Uwatec Aladin Tec 2G parser'
    ADAPTER = SmartAdapter
    
    # Data Type Identifier Table
    DTI_TABLE = [
        { 'name': 'depth',   'abs': False, 'idx': 0, 'bits': 1, 'ignore_type_bits': False, 'extra': 0 },    # 0ddd dddd
        { 'name': 'temp',    'abs': False, 'idx': 0, 'bits': 2, 'ignore_type_bits': False, 'extra': 0 },    # 10dd dddd
        { 'name': 'time',    'abs': True,  'idx': 0, 'bits': 3, 'ignore_type_bits': False, 'extra': 0 },    # 110d dddd
        { 'name': 'alarms',  'abs': True,  'idx': 0, 'bits': 4, 'ignore_type_bits': False, 'extra': 0 },    # 1110 dddd
        { 'name': 'depth',   'abs': False, 'idx': 0, 'bits': 5, 'ignore_type_bits': False, 'extra': 1 },    # 1111 0ddd dddd dddd
        { 'name': 'temp',    'abs': False, 'idx': 0, 'bits': 6, 'ignore_type_bits': False, 'extra': 1 },    # 1111 10dd dddd dddd
        { 'name': 'depth',   'abs': True,  'idx': 0, 'bits': 7, 'ignore_type_bits': True,  'extra': 2 },    # 1111 110d dddd dddd dddd dddd
        { 'name': 'temp',    'abs': True,  'idx': 0, 'bits': 8, 'ignore_type_bits': False, 'extra': 2 },    # 1111 1110 dddd dddd dddd dddd
        { 'name': 'alarms',  'abs': True,  'idx': 1, 'bits': 9, 'ignore_type_bits': False, 'extra': 0 },    # 1111 1111 0ddd dddd
    ]
    
    # Alarm Identifier Table
    ALARM_TABLE = [
        { 'idx': 0, 'mask': 2,  'name': 'ascent' },
        { 'idx': 0, 'mask': 4,  'name': 'bookmark' },
    ]
        
    def parse(self, data, *args, **kwargs):
        self.init_parser()
        
        if len(data) < 116:
            raise ParseError("Dive data must be at least 116 bytes")
        
        _len = struct.unpack_from('<L', data, 4)[0]
        
        if _len != len(data):
            raise ParseError("Data length mismatch")
    
        dive = {'cmp' : [0, 0, 0, 0, 0, 0, 0, 0]}
        dive.update(kwargs)
        
        dive['date']            = self.read_datetime(data, 8)            # offset 0x08 - 0x0b
    #   dive['_unk1']           = self.read_ulong(data, 12)              # offset 0x0c - 0x0f
        dive['utc_offset']      = self.read_sshort(data, 16)             # offset 0x10
        dive['rep_no']          = self.read_ushort(data, 17)             # offset 0x11
        dive['mbLevel']         = self.read_ushort(data, 18)             # offset 0x12
    #   dive['_unk2']           = self.read_ushort(data, 19)             # offset 0x13
        dive['alarms']          = self.read_uint(data, 20)               # offset 0x14 - 0x15
        dive['max_depth']       = self.read_uint(data, 22)               # offset 0x16 - 0x17
        dive['avg_depth']       = self.read_uint(data, 24)               # offset 0x18 - 0x19
        dive['duration']        = self.read_uint(data, 26)               # offset 0x1a - 0x1b
        dive['max_temp']        = self.read_uint(data, 28)               # offset 0x1c - 0x1d
        dive['min_temp']        = self.read_uint(data, 30)               # offset 0x1e - 0x1f
        dive['air_temp']        = self.read_uint(data, 32)               # offset 0x20 - 0x21
        dive['ppO2_1']          = self.read_ushort(data, 34)             # offset 0x22
        dive['ppO2_2']          = self.read_ushort(data, 35)             # offset 0x23
        dive['ppO2_3']          = self.read_ushort(data, 36)             # offset 0x24
        dive['batt']            = self.read_ushort(data, 37)             # offset 0x25
    #   dive['_unk5']           = self.read_uint(data, 38)               # offset 0x26 - 0x27
        dive['interval']        = self.read_uint(data, 40)               # offset 0x28 - 0x29
        dive['cnsO2']           = self.read_uint(data, 42)               # offset 0x2a - 0x2b
    #   dive['_unk6']           = self.read_uint(data, 44)               # offset 0x2c - 0x2d
        dive['ppO2_max1']       = self.read_uint(data, 46)               # offset 0x2e - 0x2f
        dive['ppO2_max2']       = self.read_uint(data, 48)               # offset 0x30 - 0x31
        dive['ppO2_max3']       = self.read_uint(data, 50)               # offset 0x32 - 0x33
    #   dive['_unk7']           = self.read_ulong(data, 52)              # offset 0x34 - 0x37
        dive['desat_before']    = self.read_uint(data, 56)               # offset 0x38 - 0x39
        dive['nofly_before']    = self.read_uint(data, 58)               # offset 0x3a - 0x3b
        dive['mode']            = self.read_ulong(data, 60)              # offset 0x3c - 0x3f
    #   dive['_unk9']           = self.read_uint(data, 64)               # offset 0x40 - 0x41
    #   dive['_unk10']          = self.read_uint(data, 66)               # offset 0x42 - 0x43
    #   dive['_unk11']          = self.read_ulong(data, 68)              # offset 0x44 - 0x47
    #   dive['_unk12']          = self.read_ulong(data, 72)              # offset 0x48 - 0x4b
    #   dive['_unk13']          = self.read_ulong(data, 76)              # offset 0x4c - 0x4f
    #   dive['_unk14']          = self.read_uint(data, 80)               # offset 0x50 - 0x51
    #   dive['_unk15']          = self.read_uint(data, 82)               # offset 0x52 - 0x53
        dive['cmp'][0]          = self.read_ulong(data, 84)              # offset 0x54 - 0x57
        dive['cmp'][1]          = self.read_ulong(data, 88)              # offset 0x58 - 0x5b
        dive['cmp'][2]          = self.read_ulong(data, 92)              # offset 0x5c - 0x5f
        dive['cmp'][3]          = self.read_ulong(data, 96)              # offset 0x60 - 0x63
        dive['cmp'][4]          = self.read_ulong(data, 100)             # offset 0x64 - 0x67
        dive['cmp'][5]          = self.read_ulong(data, 104)             # offset 0x68 - 0x6b
        dive['cmp'][6]          = self.read_ulong(data, 108)             # offset 0x6c - 0x6f
        dive['cmp'][7]          = self.read_ulong(data, 112)             # offset 0x70 - 0x73 
        
        dive['profile']         = self.parse_profile(data[116:])
        
        dive['_bin_header']     = base64.encodestring(data[0:116]).strip()
        dive['_bin_profile']    = base64.encodestring(data[116:]).strip()
        
        return dive
