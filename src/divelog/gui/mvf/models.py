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
log = logging.getLogger(__name__)

from functools import partial
from PySide.QtCore import Qt, QAbstractListModel, QAbstractTableModel, \
    QModelIndex
from PySide.QtGui import QSortFilterProxyModel
from divelog.db import countries, types

def _defset(o, v, a):
    setattr(o, a, v)
    return True

class ModelColumn(object):
    '''
    '''
    def __init__(self, **kwargs):
        def kw(n, d=None):
            return kwargs[n] if n in kwargs else d

        self._attr = kw('attr')
        self._delegate = kw('delegate')
        self._hidden = kw('hidden', False)
        self._internal = kw('internal', False)
        self._label = kw('label')

        # Appearance
        self._align = kw('alignment')
        self._font = kw('font')
        self._bg = kw('background')
        self._fg = kw('foreground')
        self._checkbox = kw('checkbox', False)

        # Setup Getter/Setter
        self._display = kw('display', lambda o: getattr(o, self._attr))
        self._decoration = kw('decoration', lambda o: None)
        self._get = kw('get', lambda o: getattr(o, self._attr))
        self._set = kw('set', partial(_defset, a=self._attr))
    
    def headerData(self, role):
        'Return the Column Header Data'
        if role == Qt.DisplayRole:
            return self._label
        return None
    
    def setData(self, obj, value, role=Qt.EditRole):
        'Set the Item Data'
        if role == Qt.EditRole:
            return self._set(obj, value)
        return False
        
    def data(self, obj, role=Qt.DisplayRole):
        'Get the Item Data'
        if role == Qt.DisplayRole:
            return self._display(obj)
        elif role == Qt.DecorationRole:
            return self._decoration(obj)
        elif role == Qt.EditRole:
            return self._get(obj)
        elif role == Qt.FontRole:
            return self._font
        elif role == Qt.TextAlignmentRole:
            return self._align
        elif role == Qt.BackgroundRole:
            return self._bg
        elif role == Qt.ForegroundRole:
            return self._fg
        elif role == Qt.CheckStateRole:
            if not self._checkbox:
                return None
            else:
                v = self._display(obj)
                if isinstance(v, bool):
                    return {True: Qt.Checked, False: Qt.Unchecked}[v]
                else:
                    return Qt.PartiallyChecked
        return None
    
    @property
    def delegate(self):
        'Return the Delegate Class'
        return self._delegate
    
    @property
    def hidden(self):
        'Return whether the Column should be Hidden'
        return self._hidden
    
    @property
    def internal(self):
        'Return whether the Column is Internal only'
        return self._internal
    
class SAProxyModel(QSortFilterProxyModel):
    '''
    SQLAlchemy Proxy Model Class
    
    Subclasses Qt's Sort/Filter Proxy Model to provide sorting on native
    Python values.  The PySide implementation of the proxy model in particular
    chokes on Python datetime values and refuses to sort correctly.
    
    Reimplementing this in Python is probably not the fastest solution but it
    seems (subjectively) to be faster than translating every data value to/from
    Qt-native types on every data() call.
    '''
    def lessThan(self, left, right):
        'Compare the two Operands'
        ldata = self.sourceModel().data(left)
        rdata = self.sourceModel().data(right)
        return ldata < rdata

class SATableModel(QAbstractTableModel):
    '''
    SQLAlchemy Table Model Class
    
    The SATableModel class implements a custom PySide table model for use
    with SQLAlchemy tables and queries. 
    '''
    def __init__(self, columns, rows=None, parent=None):
        super(SATableModel, self).__init__()
        
        # Check Column Types
        if not isinstance(columns, (list, tuple)):
            raise TypeError('Columns must be a list of ModelColumn instances')
        for c in columns:
            if not isinstance(c, ModelColumn):
                raise TypeError('Columns must be a list of ModelColumn instances')
        
        # Initialize Column Data and Data Rows
        self._cols = columns
        self._rows = rows
    
    def reset_from_list(self, rows):
        'Reset Model Data from a List'
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
        
    def hasChildren(self, parent):
        'Pretend to be a List'
        return False
    
    def columnCount(self, parent=QModelIndex()):
        '''Return the number of Columns in the model'''
        return len(self._cols)
    
    def rowCount(self, parent=QModelIndex()):
        'Return the number of Rows in the model'
        if self._rows is None:
            return 0
        return len(self._rows)
        
    def headerData(self, col, orientation, role):
        'Return the Column Titles'
        if orientation == Qt.Horizontal:
            return self._cols[col].headerData(role)
        return None
    
    def setData(self, index, value, role=Qt.EditRole):
        'Set the Item Data'
        if not index.isValid():
            return None
        c = self._cols[index.column()]
        r = self._rows[index.row()]
        
        return c.setData(r, value, role)
    
    def data(self, index, role=Qt.DisplayRole):
        'Get the Item Data'
        if not index.isValid():
            return None
        c = self._cols[index.column()]
        r = self._rows[index.row()]
        
        return c.data(r, role)
    
    @property
    def columns(self):
        'Return the list of Columns'
        return self._cols
    
class CountryModel(QAbstractListModel):
    '''
    Country Column Model
    
    Represents a Country value column as a list model, which can be used with
    a combo box for country selection.
    '''
    def __init__(self):
        super(CountryModel, self).__init__()
        self.countries = [types.Country(code) for code, _ in countries.COUNTRIES]
    
    def rowCount(self, parent=QModelIndex):
        'Return the number of Rows in the model'
        return len(self.countries)
    
    def data(self, index, role):
        'Get Item Data'
        if not index.isValid() or index.row() < 0 or index.row() >= len(self.countries):
            return None
        c = self.countries[index.row()]
        
        if role == Qt.DisplayRole:
            return c.name
        elif role == Qt.EditRole:
            return unicode(c)
        elif role == Qt.DecorationRole:
            return c.icon
        
        return None