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

import logging
import datetime
import sqlalchemy
import models, tables, types
from sqlalchemy.orm import defer, sessionmaker, Query
from migrate.versioning import api
from migrate.exceptions import DatabaseNotControlledError

_log = logging.getLogger(__name__)
_repo = 'divelog/db/migrations'

class DatabaseError(Exception):
    'Database Error Class'
    
class DBNeedsUpgrade(DatabaseError):
    'Database Needs Upgrade Error Class'

class DBNeedsDowngrade(DatabaseError):
    'Database Needs Downgrade Error Class'

class Logbook(object):
    '''
    Logbook Class
    
    The Logbook class contains all information related to a single logbook
    database file.  Each Logbook instance is linked to a single file on the
    filesystem, passed to the constructor.  This file is then opened as an
    SQLalchemy database and initialized.
    
    PyDiveLog uses sqlalchemy-migrate to maintain a consistent database schema
    as new features are added.  Any changes to database schema should be put
    into a new migration script, which will be picked up the next time the 
    Logbook is opened.  Schema upgrades are performed automatically by the 
    constructor.  To prevent this behavior, pass auto_update=False to the 
    constructor.  If the auto_update parameter is false, and the database file
    is not the current version, a DatabaseError exception will be raised.
    
    The class methods Logbook.Version() and Logbook.CurrentVersion() can be 
    used to query a file's version and the most current schema version, 
    respectively.  To manually update a Logbook to a new version, or to 
    downgrade a Logbook to a previous version, use the Logbook.Upgrade() and
    Logbook.Downgrade() class methods.
    
    NOTE: CALLING Logbook.Downgrade() MAY RESULT IN DATA LOSS FROM DROPPED 
    COLUMNS AND TABLES.
    
    To create a new logbook, use the Logbook.Create() class method rather than
    passing a non-existing file name to __init__().  This will ensure that the
    schema versioning gets set up properly in the new database and that tables
    will be consistent with the internal schema.
    '''
    def __init__(self, filename, **kwargs):
        self._echo = 'echo' in kwargs and kwargs['echo']
        self._filename = filename
        self._url = 'sqlite:///%s' % filename
        self._engine = sqlalchemy.create_engine(self._url, echo=self._echo)
        
        self._session_factory = sessionmaker()
        self._session_factory.configure(bind=self._engine)
        self._session = None   # We will lazy-create session
         
        self._check_schema(not 'auto_update' in kwargs or kwargs['auto_update'])
    
    def _check_schema(self, auto_update=True):
        'Check the database version, upgrading schema if necessary'
        
        # Check the DB Version
        try:
            cur = Logbook.CurrentVersion()
            ver = self.db_version
            
            if ver < cur:
                if auto_update:
                    _log.info('Upgrading Logbook to version %d', cur)
                    api.upgrade(self._url, _repo)
                else:
                    raise DBNeedsUpgrade("Logbook %s was created with a previous version of pyDiveLog" % self._filename)
            elif ver > cur:
                raise DBNeedsDowngrade("Logbook %s was created with a newer version of pyDiveLog" % self._filename)
            else:
                _log.info('Opened \'%s\' with version %d', self._filename, ver)
        except DatabaseNotControlledError:
            raise DatabaseError("%s is not a valid Logbook" % self._filename)
        
    #-------------------------------------------------------------------------
    # Basic Queries
    
    @classmethod
    def q_dives(cls):
        '''Return a query for all Dives'''
        return Query(models.Dive)
    
    @classmethod
    def q_sites(cls):
        '''Return a query for all Dive Sites'''
        return Query(models.DiveSite)
    
    @classmethod
    def q_computers(cls):
        '''Return a query for all Dive Computers'''
        return Query(models.DiveComputer)
        
    #-------------------------------------------------------------------------
    # Properties
    
    @property
    def all_dives(self):
        '''Shortcut for q_dives.all()'''
        q = Logbook.q_dives()
        q.session = self.session
        return q.all()
    
    @property
    def all_sites(self):
        '''Shortcut for q_sites.all()'''
        q = Logbook.q_sites()
        q.session = self.session
        return q.all()
    
    @property
    def all_countries(self):
        '''Return a list of distinct Countries'''
        return [i[0] for i in self.session.query(models.DiveSite.country).distinct().all()]
    
    @property
    def all_computers(self):
        '''Shortcut for q_computers.all()'''
        q = Logbook.q_computers()
        q.session = self.session
        return q.all()
    
    @property
    def db_version(self):
        '''Return the File Version of this Logbook'''
        return api.db_version(self._url, _repo)
    
    @property
    def filename(self):
        return self._filename
    
    @property
    def session(self):
        '''Return the current SQLalchemy Session'''
        if self._session == None:
            self._session = self._session_factory()
        return self._session
        
    #-------------------------------------------------------------------------
    # Class Methods
    
    @classmethod
    def Create(cls, filename, **kwargs):
        'Create a new Logbook database'
        url = 'sqlite:///%s' % filename
        engine = sqlalchemy.create_engine(url)
        
        # Initialize the Model Tables and setup Versioning
        tables.init_tables(engine)
        api.version_control(url, _repo, cls.CurrentVersion())
        
        # Return a new Logbook instance
        return cls(filename, **kwargs)
    
    @classmethod
    def Downgrade(cls, filename, version, **kwargs):
        '''Downgrade a Logbook's database schema'''
        api.downgrade('sqlite:///%s' % filename, _repo, version, **kwargs)
    
    @classmethod
    def Upgrade(cls, filename, version=None, **kwargs):
        '''Upgrade a Logbook's database schema'''
        api.upgrade('sqlite:///%s' % filename, _repo, version, **kwargs)
    
    @classmethod
    def CurrentVersion(cls):
        'Return the current Logbook schema version'
        return api.version(_repo)
    
    @classmethod
    def Version(cls, filename):
        'Check the Schema Version of a Logbook'
        return api.db_version('sqlite:///%s' % filename, _repo)
