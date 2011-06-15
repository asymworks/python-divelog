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

import json
import sqlalchemy.types as satypes
from sqlalchemy.ext.mutable import MutableComposite

class JsonType(satypes.MutableType, satypes.TypeDecorator):
    '''
    JsonType
    
    Stores Python objects in the database using a JSON representation.  Ideal
    to store dictionaries and lists/arrays in a platform-independent format.
    Adapted from the SQLalchemy PickleType class.
    '''
    impl = satypes.Unicode
    
    def __init__(self, mutable=True, comparator=None):
        self.mutable = mutable
        self.comparator = comparator
        super(JsonType, self).__init__()
    
    def bind_processor(self, dialect):
        impl_processor = self.impl.bind_processor(dialect)
        dumps = json.dumps
        
        if impl_processor:
            def process(value):
                if value is not None:
                    value = unicode(dumps(value, ensure_ascii=False))
                return impl_processor(value)
        else:
            def process(value):
                if value is not None:
                    value = unicode(dumps(value, ensure_ascii=False))
                return value
        
        return process
    
    def result_processor(self, dialect, coltype):
        impl_processor = self.impl.result_processor(dialect, coltype)
        loads = json.loads
        
        if impl_processor:
            def process(value):
                value = impl_processor(value)
                if value is None:
                    return None
                return loads(value)
        else:
            def process(value):
                if value is None:
                    return None
                return loads(value)
        
        return process
    
    def copy_value(self, value):
        if self.mutable:
            return json.loads(json.dumps(value))
        else:
            return value

    def compare_values(self, x, y):
        if self.comparator:
            return self.comparator(x, y)
        else:
            return x == y

    def is_mutable(self):
        return self.mutable

class Country(object):
    '''
    ISO 3166 Country Class
    
    Holds information about a Country including its name, ISO 3166 code, and 
    a Qt Image of the country flag, if the resource is available.  The flag
    image should reside in the resource /flags/xx.png, where xx is the two-
    character lower-case country code.
    '''
    def __init__(self, code):
        self.code = code.upper()
        self._flag = None
        self._icon = None
    
    def __unicode__(self):
        return unicode(self.code or u'')

    def __eq__(self, other):
        return unicode(self) == unicode(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __cmp__(self, other):
        return cmp(unicode(self), unicode(other))

    def __hash__(self):
        return hash(unicode(self))

    def __repr__(self):
        return "%s(code=%r)" % (self.__class__.__name__, unicode(self))

    def __nonzero__(self):
        return bool(self.code)

    def __len__(self):
        return len(unicode(self))
    
    @property
    def name(self):
        # Local import so the countries aren't loaded unless they are needed. 
        from countries import COUNTRIES
        for code, name in COUNTRIES:
            if self.code.upper() == code.upper():
                return name
        return ''
    
    @property
    def flag(self):
        # Load flag image from resource
        if not self._flag:
            from PySide.QtGui import QImage 
            self._flag = QImage(':/flags/%s.png' % self.code.lower())
        return self._flag if not self._flag.isNull() else None
    
    @property
    def icon(self):
        # Load flag icon from resource
        from PySide.QtGui import QIcon
        return QIcon(':/flags/%s.png' % self.code.lower())

class CountryType(satypes.MutableType, satypes.TypeDecorator):
    '''
    CountryType
    
    Stores an ISO 3166 Country Code in two-letter format.  Presents the data
    to Python as a Country object, which includes getters for the Country Name
    '''
    impl = satypes.Unicode
    
    def __init__(self, mutable=True, comparator=None):
        self.mutable = mutable
        self.comparator = comparator
        super(CountryType, self).__init__()
    
    def bind_processor(self, dialect):
        impl_processor = self.impl.bind_processor(dialect)
        
        if impl_processor:
            def process(value):
                if value is not None:
                    value = unicode(value.code.upper())
                return impl_processor(value)
        else:
            def process(value):
                if value is not None:
                    value = unicode(value.code.upper())
                return value
        
        return process
    
    def result_processor(self, dialect, coltype):
        impl_processor = self.impl.result_processor(dialect, coltype)
        
        if impl_processor:
            def process(value):
                value = impl_processor(value)
                if value is None:
                    return None
                return Country(value)
        else:
            def process(value):
                if value is None:
                    return None
                return Country(value)
        
        return process
    
    def copy_value(self, value):
        return value

    def compare_values(self, x, y):
        if self.comparator:
            return self.comparator(x, y)
        else:
            return x == y

    def is_mutable(self):
        return self.mutable
    
class LatLng(MutableComposite):
    '''
    LatLng - Latitude/Longitude Composite Value
    
    Represents a latitude/longitude pair as a composite value, using separate
    columns in the underlying table.
    '''
    def __init__(self, lat, lon):
        self._lat = lat
        self._lon = lon
    def __composite_values__(self):
        return self._lat, self._lon
    def __eq__(self, other):
        return other is not None and \
            self._lat == other._lat and \
            self._lon == other._lon
    def __ne__(self, other):
        return not self.__eq__(other)
    def __repr__(self):
        if self.lat is None or self.lon is None:
            return ''
        return '%.6f, %.6f' % (self.lat, self.lon)
    @property
    def lat(self):
        return self._lat
    @lat.setter
    def setLat(self, v):
        if v < -90.0 or v > 90.0:
            raise ValueError('Latitude must be between -90 and +90 degrees')
        self._lat = v
        self.changed()
    @property
    def lon(self):
        return self._lon
    @lon.setter
    def setLon(self, v):
        if v < -180.0 or v > 180.0:
            raise ValueError('Longitude must be between -180 and +180 degrees')
        self._lon = v
        self.changed()
