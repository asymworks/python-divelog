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

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, \
    ForeignKey, MetaData, Integer, String, Table, Text
from types import JsonType, CountryType

# Declare global meta-data
meta = MetaData()

# Computer Table
computers = Table('computers', meta,
    Column('id', Integer, primary_key=True),
    Column('driver', String(255), nullable=False),
    Column('serial', String(255), nullable=False),
    Column('name', String(255)),
    Column('token', String(255)),
    Column('parser', String(255)),
    Column('last_transfer', DateTime),
    Column('driver_args', Text),
    Column('parser_args', Text)
)

# Dive Table
dives = Table('dives', meta,
    Column('id', Integer, primary_key=True),
    
    # Basic Information from Computer
    Column('dive_number', Integer),
    Column('dive_datetime', DateTime, nullable=False),
    Column('site_id', Integer, ForeignKey('sites.id')),
    Column('computer_id', Integer, ForeignKey('computers.id')),
    Column('repetition', Integer, nullable=False),
    Column('interval', Integer, nullable=False),
    Column('duration', Integer, nullable=False),
    Column('max_depth', Float, nullable=False),
    Column('avg_depth', Float),
    Column('air_temp', Float),
    Column('max_temp', Float),
    Column('min_temp', Float),
    Column('profile', JsonType),
    Column('vendor', JsonType),
    Column('imported', DateTime),
    
    # Comments and Rating
    Column('comments', Text),
    Column('rating', Float),
    
    # Deco Table Information
    Column('pg_start', String(1)),
    Column('pg_end', String(1)),
    Column('rnt', Integer),
    
    # Deco Algorithm Information
    Column('deco_start', Integer),
    Column('deco_end', Integer),
    Column('nofly_start', Integer),
    Column('nofly_end', Integer),
    Column('algorithm', String(255)),
    
    # Dive Flags
    Column('safety_stop', Boolean),
)

# Dive Site Table
sites = Table('sites', meta,
    Column('id', Integer, primary_key=True),
    Column('site', String(255), nullable=False),
    Column('place', String(255)),
    Column('country', CountryType),
    Column('lat', Float),
    Column('lon', Float),
    Column('platform', String(255)),
    Column('water', String(255)),
    Column('bottom', String(255)),
    Column('salinity', Enum('fresh_water', 'salt_water')),
    Column('altitude', Float),
    Column('bottom_depth', Float),
    Column('comments', Text)
)

# Initialize model tables
def init_tables(engine):
    '''Initialize model tables'''
    meta.create_all(engine)
