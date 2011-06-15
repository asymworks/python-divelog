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
Python Dive Computer package

Implements a set of driver and parser objects to download data from commonly-
available SCUBA and free-diving computers.  Protocols and data formats are
adapted from `libdivecomputer <http://divesoftware.org/libdc>` and `JDiveLog
<http://www.jdivelog.org>`_.  All implementations are pure Python for easy
incoporation into third-party dive logging and transferring software.

This package uses the `irsocket <http://github.com/asymworks/python-irda>`
and `pySerial <http://pyserial.sourceforge.net>` to implement IrDA and RS-232
communication protocols.  
'''

import logging

__version__ = '0.1.3'
__all__ = [ 'BaseDriver', 'register_driver', 'list_drivers', 
            'BaseParser', 'register_parser', 'list_parsers',
            'BaseAdapter',
]

log = logging.getLogger(__name__)

# Driver and Parser Registries
_driver_registry = {}
_parser_registry = {}

# Check for a valid identifier
def isidentifier(str):
    import re, tokenize
    return re.match(tokenize.Name, str, re.I)

# Base class for Dive Computer Drivers
class BaseDriver(object):
    def __init__(self, event_sink=None):
        self._event_sink = event_sink
        
# Base class for Dive Computer Parsers
class BaseParser(object):
    pass

# Base class for Dive Computer Adapters
class BaseAdapter(object):
    '''
    Base class for Dive Computer Adapters
    
    This class is used as the base class for adapter objects which translate
    from a computer-specific parse result to a standard interface that can be
    used by a higher-level dive logging application.  This class provides 
    default methods that should be overridden by child classes which retrieve
    the data from the parser result.
    
    The adapter class defines a common subset of data that every dive computer
    should implement, namely dive date/time, repetitive dive number, surface
    interval, dive duration, max/avg depth, and air/min/max temperature, gas
    mix information, and depth/temperature profile.  All other information 
    logged by the dive computer should be added either to the profile, as a 
    user-defined extra profile, or to the vendor property, which contains user-
    defined key/value pairs. 
    '''
    def __init__(self, data):
        self._data = data
        
    def dive_datetime(self):
        '''Dive Date/Time'''
    
    def repetition(self):
        '''Repetitive Dive Number'''
    
    def interval(self):
        '''Surface Interval [min]'''
    
    def duration(self):
        '''Dive Duration [min]'''

    def max_depth(self):
        '''Maximum Depth [m]'''
    
    def avg_depth(self):
        '''Average Depth [m]'''
    
    def air_temp(self):
        '''Air Temperature [deg C]'''
    
    def max_temp(self):
        '''Maximum Temperature [deg C]'''
    
    def min_temp(self):
        '''Minimum Temperature [deg C]'''
        
    def mixes(self):
        '''
        Gas Mix Data
        
        The return value should be a dictionary of gas definitions used by the
        computer during the dive.  Each gas definition is itself a dictionary
        with the keys 'n2', 'o2', 'he', 'h2', and 'ar', each specifying the 
        fraction of the specified compound (molecular nitrogen, molecular 
        oxygen, helium, molecular hydrogen, and argon) present in the gas mix.
        
        All five gasses should be specified for each breathing mix, and the sum
        of all five fractions should be 1.
        '''
    
    def profile(self):
        '''
        Dive Profile Data
        
        The return value should be a list of dictionaries with at least two 
        keys: 'time' and 'depth'.  Several standard measurands are supported as
        listed below; in addition, user-defined keys are supported, and will be
        displayed by translating underscores to spaces and title-casing the 
        result.  Data should be stored using the following default units:
        
        Profile Key | Default Units
        ----------------------------
        alarm       | -N/A-
        battery     | percent
        cnsO2       | percent
        depth       | meters
        heading     | degrees
        mix         | -N/A-
        otu         | OTU
        pressure    | bar
        rbt         | minutes
        sac         | bar/min/atm
        temp        | deg. Celsius
        time        | seconds
        
        The 'alarms' value should be a comma-separated list of alarm flags.  
        Standard alarm flags are 'ascent', 'descent', 'rbt', 'deco', 'bookmark'
        and 'battery'.  User-defined alarms are permitted and will be displayed 
        by translating underscores to spaces and title-casing the result.
        
        If multiple breathing mixes are used, the 'mix' key should be included
        and the value set to the key name of the mix as returned by the mixes() 
        method.  If the key is not present, the breathing gas is assumed to be
        air (20.9% oxygen, 79.1% nitrogen).
        
        Note that to correspond with UDDF guidelines (and to make the job of the
        GUI easier), all defined profiles must appear in each waypoint, even if
        the value does not change from one sample to the next.
        '''
    
    def vendor(self):
        '''
        Vendor-Specific Data
        
        The return value should be a dictionary of user-defined keys.  The data
        will be displayed as a name-value list, with the names derived from the
        keys by translating underscores to spaces and title-casing the result.
        '''
    
    def computer(self):
        '''
        Dive Computer Data
        
        The return value should be a dictionary with the following keys: 
        'vendor', 'model', 'driver', and 'serial'.  The 'vendor' value should
        specify the computer vendor/manufacturer.  The 'model' value should be
        the computer model name or number.  The 'driver' value should be set
        to the name of the python-divecomputer driver used to download data
        from the device.  The 'serial' value should be set to the dive computer
        serial number, as returned by the driver.
        '''

# Register a new Driver class
def register_driver(cls, name=None, desc=None):
    '''
    Register a new driver class
    
    This function registers a driver class with the DiveComputer package so
    that it can be discovered at runtime using the list_drivers() function. 
    Driver registration is not required if the client knows a priori which
    driver class to load.  Driver classes must extend or have as their 
    metaclass the BaseDriver class.  Driver classes may include a class method
    on_register(cls) which is called by this function when the class is
    registered.  If the function exists, and returns false, the class will
    not be registered and the registration function will exit normally.
    
    All drivers provided by pyDiveComputer are automatically registered by
    the master package and do not need to be re-registered by the client.
    
    To register a new dive computer driver class the function can be called
    manually or used as a class decorator.  The 'name' parameter is a short
    identifier for the class and must be unique.  It must obey usual Python
    identifier rules (starts with character or '_', only letters and numbers,
    no whitespace, etc).  If the identifier is invalid, the function will
    raise a KeyError.
    '''
    
    if not cls:
        raise ValueError("Invalid driver class (None)")
    if not issubclass(cls, BaseDriver):
        raise ValueError("Invalid driver class '%s'" % cls.__name__)
    
    if not name:
        if  hasattr(cls, 'NAME'):
            name = cls.NAME
        else:
            name = cls.__name__
            
    if not desc and hasattr(cls, 'DESCRIPTION'):
        desc = cls.DESCRIPTION
    
    if not isidentifier(name):
        raise KeyError("'%s' is not a valid identifier" % name)
    if name in _driver_registry:
        raise KeyError("Driver '%s' is already registered" % name)
    
    if hasattr(cls, 'on_register') and callable(cls.on_register):
        if not cls.on_register():
            return cls
    
    _driver_registry[name] = { 'desc': desc, 'class': cls }
    
    log.debug('Registered driver class "%s" (%s)', name, desc)
    
    # In case we are called as a decorator
    return cls

# Register a new Parser class
def register_parser(cls, name=None, desc=None, adapter=None):
    '''
    Register a new parser class
    
    This function registers a parser class with the DiveComputer package so
    that it can be discovered at runtime using the list_parsers() function. 
    Parser registration is not required if the client knows a priori which
    parser class to load.  Parser classes must extend or have as their 
    metaclass the BaseParser class.  Parser classes may include a class method
    on_register(cls) which is called by this function when the class is
    registered.  If the function exists, and returns false, the class will
    not be registered and the registration function will exit normally.
    
    All parsers provided by pyDiveComputer are automatically registered by
    the master package and do not need to be re-registered by the client.
    
    To register a new dive computer parser class the function can be called
    manually or used as a class decorator.  The 'name' parameter is a short
    identifier for the class and must be unique.  It must obey usual Python
    identifier rules (starts with character or '_', only letters and numbers,
    no whitespace, etc).  If the identifier is invalid, the function will
    raise a KeyError.
    
    Parsers can optionally specify an adapter class which can be used to
    adapt the object returned by the parse() method into a standard interface.
    See the documentation of the BaseAdapter class above for the interface
    definition that the adapter should implement.
    '''
    
    if not cls:
        raise ValueError("Invalid parser class (None)")
    if not issubclass(cls, BaseParser):
        raise ValueError("Invalid parser class '%s'", cls.__name__)
    
    if not name:
        if  hasattr(cls, 'NAME'):
            name = cls.NAME
        else:
            name = cls.__name__
            
    if not desc and hasattr(cls, 'DESCRIPTION'):
        desc = cls.DESCRIPTION
        
    if not adapter and hasattr(cls, 'ADAPTER'):
        adapter = cls.ADAPTER
    if adapter and not issubclass(adapter, BaseAdapter):
        raise ValueError("Adapter '%s' does not descend from BaseAdapter" % adapter.__class__.__name__)
    
    if not isidentifier(name):
        raise KeyError("'%s' is not a valid identifier" % name)
    if name in _parser_registry:
        raise KeyError("Parser '%s' is already registered" % name)
    
    if hasattr(cls, 'on_register') and callable(cls.on_register):
        if not cls.on_register():
            return cls
    
    _parser_registry[name] = { 'desc': desc, 'class': cls, 'adapter': adapter }
    
    log.debug('Registered parser class "%s" (%s)', name, desc)
    
    # In case we are called as a decorator
    return cls

# Return the Driver registry dict
def list_drivers():
    '''Return the Driver registry'''
    return _driver_registry

# Return the Parser registry dict
def list_parsers():
    '''Return the Parser registry'''
    return _parser_registry

# Import and Register built-in drivers and parsers
from divelog.dc.driver import *
from divelog.dc.driver.uwatec_smart import *

from divelog.dc.parser import *
from divelog.dc.parser.uwatec_smart import *

register_driver(FileDriver)
register_driver(SmartDriver)

register_parser(NullParser)
register_parser(AladinTec2G)