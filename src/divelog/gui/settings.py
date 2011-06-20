# =============================================================================
# 
# Copyright (C) 2011 Asymworks, LLC.  All Rights Reserved.
# www.pydivelog.com / info@pydivelog.com
# 
# This file is part of the Python Dive Logbook (pyDiveLog)
# 
# This file may be used under the terms of the GNU General Public
# License version 2.0 as published by the Free Software Foundation
# and appearing in the file license.txt included in the packaging of
# this file.  Please review this information to ensure GNU
# General Public Licensing requirements will be met.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
# 
# =============================================================================

from PySide.QtCore import QSettings

def read_setting(name, default=None):
    '''
    Read a Name/Value Setting
    
    Reads a name/value setting from the Qt settings store.  If the value does
    not exist, the default parameter is returned.  Note that QSettings stores
    all settings as strings, so the caller is responsible for casting the 
    returned value into the proper Python type.
    '''
    s = QSettings()
    s.beginGroup('Settings')
    v = s.value(name)
    s.endGroup()
    
    if v is None:
        return default
    return v

def write_setting(name, value):
    '''
    Write a Name/Value Setting
    
    Writes a name/value setting to the Qt settings store.  Note that QSettings
    stores all settings as strings, so the passed value will be converted to a
    string using the python str() function prior to being stored.
    '''
    s = QSettings()
    s.beginGroup('Settings')
    s.setValue(name, value)
    s.endGroup()
    
# Unit Conversion Table
_units = {
    'depth': {
        # NB: Depth is given in msw/fsw (pressure), _not_ meters/feet (length)
        'meters': {
            'to_native':    lambda x: x,
            'from_native':  lambda x: x,
            'abbr':         u'msw'
        },
        'feet': {
            'to_native':    lambda x: x*0.30705,
            'from_native':  lambda x: x/0.30705,
            'abbr':         u'fsw'
        },
    },
    'temperature': {
        'celsius': {
            'to_native':    lambda x: x,
            'from_native':  lambda x: x,
            'abbr':         u'\u00b0C'
        },
        'farenheit': {
            'to_native':    lambda x: 5.0/9.0*(x-32),
            'from_native':  lambda x: x*9.0/5.0+32,
            'abbr':         u'\u00b0F'
        },
    },
}

def quantities():
    'Return all Unit Quantities'
    return _units.keys()

def units(qty):
    'Return all Units for a Quantity'
    if not qty in _units:
        return []
    return _units[qty].keys()

def abbr(qty, name):
    'Return the abbreviation for the given Unit'
    if not qty in _units or not name in _units[qty]:
        return None
    return _units[qty][name]['abbr']

def conversion(qty, name):
    'Return a tuple with the to_native and from_native conversion functions'
    if not qty in _units or not name in _units[qty]:
        return (None, None)
    q = _units[qty][name]
    return (q['to_native'], q['from_native'])