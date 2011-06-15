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

from datetime import datetime
from sqlalchemy.orm import backref, deferred, mapper, \
    composite, relationship
import tables
from types import LatLng

# Dive Model
class Dive(object):
    '''
    Dive Model
    
    Contains information about a single dive.
    
    BackRefs:
    - dive_site : <DiveSite> (via site_id)
    - computer : <DiveComputer> (via computer_id)
    '''
    
    #TODO: Link to Mixes
    
    def init_from_adapter(self, adapter):
        '''Load the Dive object from an adapter'''
        self.dive_number = None
        self.dive_datetime = adapter.dive_datetime()
        self.site_id = None
        self.repetition = adapter.repetition()
        self.interval = adapter.interval()
        self.duration = adapter.duration()
        self.max_depth = adapter.max_depth()
        self.avg_depth = adapter.avg_depth()
        self.air_temp = adapter.air_temp()
        self.max_temp = adapter.max_temp()
        self.min_temp = adapter.min_temp()
        
        self.profile = adapter.profile()
        self.vendor = adapter.vendor()
        
        self.inserted = datetime.now()
        self.comments = None
        self.rating = None
        
    def __repr__(self):
        return '<Dive %d (%s)>' % (self.id, self.dive_datetime.date().strftime('%x'))

# Dive Mapper
mapper(Dive, tables.dives, properties={
    'profile': deferred(tables.dives.c.profile),
    'vendor': deferred(tables.dives.c.vendor)
})

# Dive Computer Model
class DiveComputer(object):
    '''
    DiveComputer Model
    
    Contains information about a dive computer, including the driver and serial
    number used to access the dive computer, a name for the dive computer and
    parser information to parse returned data.
    
    Also stored is a token used to record the last dive transferred from the 
    dive computer, so that on subsequent transfers, only new dives are returned
    rather than all dives.
    
    Relationships:
    - dives : <Dive>*
    '''
    
    def __repr__(self):
        return '<Dive Computer: %s>' % (self.name or self.driver.title())

# Dive Computer Mapper
mapper(DiveComputer, tables.computers, properties={
    'dives': relationship(Dive, backref=backref('computer', lazy='join'))
})

# Dive Site Model
class DiveSite(object):
    '''
    DiveSite Model
    
    Contains information about a particular dive site, including location,
    entry type, water type, altitude, bottom depth, etc.
    
    site: Name of the dive site
    place: Place name where the site is located (e.g. City, State, Island)
    country: Country in which the site is located
    
    lat: Latitude of the dive site (in decimal degrees N)
    lon: Longitude of the dive site (in decimal degrees E)
    
    platform: Type of platform used to enter the site (e.g. Beach, Boat, ...)
    water: Type of the body of water (e.g. Ocean, Lake, Quarry, ...)
    bottom: Composition of the bottom (e.g. Sand, Rock, ...)
    salinity: Water Salinity (Fresh, Salt, or Brackish)
    altitude: Altitude of the site [m MSL]
    bottom_depth: Maximum Bottom Depth of the site [m]
    
    comments: Comments about the dive site
    
    The max_depth and avg_depth properties calculate the maximum depth and
    average maximum depth over all dives made at this dive site, which may
    be different from the bottom_depth property.
    
    Relationships:
    - dives: <Dive>*
    '''

    @property
    def num_dives(self):
        '''
        Return the number of dives made at this site
        '''
        return len(self.dives)
    
    @property
    def avg_depth(self):
        '''
        Return the average maximum depth attained over all dives at this site.
        This is not a time-average depth as in the Dive object, but rather a
        dive-averaged depth.
        '''
        if self.num_dives == 0:
            return 0
        
        ad = 0
        for dive in self.dives:
            ad += dive.max_depth
        return float(ad) / self.num_dives
    
    @property
    def avg_temp(self):
        '''
        Return the average temperature recorded over all dives at this site.
        '''
        if self.num_dives == 0:
            return 0
        
        at = 0
        for dive in self.dives:
            at += dive.min_temp
        return float(at) / self.num_dives
    
    @property
    def max_depth(self):
        '''
        Return the maximum depth recorded over all dives at this site
        '''
        md = 0
        for dive in self.dives:
            if dive.max_depth > md:
                md = dive.max_depth
        return md
    
    @property
    def rating(self):
        '''
        Return the average rating for dives at this site.  Only considers dives
        which have a non-zero rating.
        '''
        r = 0
        n = 0
        for dive in self.dives:
            if dive.rating:
                r += dive.rating
                n += 1
        return r / n if n > 0 else 0
    
    def __repr__(self):
        return '<DiveSite: %s>' % self.site
    
# Dive Site Mapper
mapper(DiveSite, tables.sites, properties={
    'dives': relationship(Dive, backref=backref('dive_site', lazy='join')),
    'latlng': composite(LatLng, tables.sites.c.lat, tables.sites.c.lon)
})
