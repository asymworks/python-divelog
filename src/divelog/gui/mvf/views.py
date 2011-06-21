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

from PySide import QtCore
from PySide.QtCore import Qt
from PySide.QtGui import QAbstractItemView, QAbstractProxyModel, QAction, \
    QHeaderView, QMenu, QTreeView

from divelog.gui.mvf.delegates import NoFocusDelegate

class MultiColumnListView(QTreeView):
    headerChanged = QtCore.Signal()
    
    '''
    Multi-Column List View
    
    Since Qt does not ship with a useful, multi-column list-view, this class
    forces a Tree View to fulfill the same purpose.  This class should in 
    general be used for read-only list views (use QTableView for editable 
    views).
    
    This class also supports showing/hiding columns by right-clicking on the
    header area.  For proper operation, only use this class with models which
    descend from SATableModel and use ModelColumn column objects.
    '''
    #FIXME: Having to query the underlying model for columns is kind of janky
    def __init__(self, parent=None):
        super(MultiColumnListView, self).__init__(parent)
        
        self.setAlternatingRowColors(True)
        self.setItemDelegate(NoFocusDelegate(self))
        self.setItemsExpandable(False)
        self.setIndentation(0)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setUniformRowHeights(True)
    
        hdr = self.header()
    
        hdr.setContextMenuPolicy(Qt.CustomContextMenu)
        hdr.customContextMenuRequested.connect(self.showContextMenu)
        hdr.sectionResized.connect(self._saveSections1)
        hdr.sectionAutoResize.connect(self._saveSections2)
        hdr.sectionMoved.connect(self._saveSections3)
        
    @QtCore.Slot(int, int, int)
    def _saveSections1(self, logicalIndex, oldSize, newSize):
        'Section Resized'
        self.headerChanged.emit()
    
    @QtCore.Slot(int, QHeaderView.ResizeMode)
    def _saveSections2(self, logicalIndex, mode):
        'Section Auto-Resized'
        self.headerChanged.emit()
    
    @QtCore.Slot(int, int, int)
    def _saveSections3(self, logicalIndex, oldVisualIndex, newVisualIndex):
        'Section Moved'
        self.headerChanged.emit()
        
    def loadHeaderGeometry(self, state):
        'Load geometry from the state argument'
        return True
        
    def saveHeaderGeometry(self):
        'Save and return geometry state as an object'
        return {}
        
    def drawBranches(self, painter, rect, index):
        'Pretend to not be a tree view'
        pass
    
    def resetColumns(self):
        'Reset column visibilities to defaults'
        if self.model() is None:
            return
        
        # If we are viewing a proxy model, skip to the source model
        mdl = self.model()
        while isinstance(mdl, QAbstractProxyModel):
            mdl = mdl.sourceModel()
        
        if mdl is None or not hasattr(mdl, 'columns'):
            return
        
        for i in range(len(mdl.columns)):
            c = mdl.columns[i]
            
            if c.delegate is not None:
                self.setItemDelegateForColumn(i, c.delegate(self))

            self.setColumnHidden(i, c.hidden or c.internal)
    
    def setModel(self, model):
        'Set the model and update columns'
        super(MultiColumnListView, self).setModel(model)
        self.resetColumns()
    
    def showHideColumn(self, s, c):
        'Show or Hide a Column'
        self.setColumnHidden(c, not s)
        self.headerChanged.emit()
    
    def showContextMenu(self, point):
        'Show the Columns context menu'
        if self.model() is None:
            return
        
        # If we are viewing a proxy model, skip to the source model
        mdl = self.model()
        while isinstance(mdl, QAbstractProxyModel):
            mdl = mdl.sourceModel()
        
        if mdl is None or not hasattr(mdl, 'columns'):
            return
        
        # Generate and show the Menu
        m = QMenu()
        for i in range(len(mdl.columns)):
            c = mdl.columns[i]
            if c.internal:
                continue
            
            a = QAction(mdl.headerData(i, Qt.Horizontal, Qt.DisplayRole), m)
            a.setCheckable(True)
            a.setChecked(not self.isColumnHidden(i))
            a.triggered.connect(partial(self.showHideColumn, c=i, s=self.isColumnHidden(i)))
            m.addAction(a)
            
        m.exec_(self.header().mapToGlobal(point))
        
    def saveState(self, s):
        'Write State to the Settings Object'
        col_width = []
        col_vidx = []
        h = self.header()
        for i in range(h.count()):
            col_width.append(h.sectionSize(i))
            col_vidx.append(h.visualIndex(i))
        s.setValue('col_width', ','.join([str(i) for i in col_width]))
        s.setValue('col_vidx', ','.join([str(i) for i in col_vidx]))
        
    def loadState(self, s):
        'Load State from the Settings Object'
        cw = s.value('col_width')
        cv = s.value('col_vidx')
        
        h = self.header()
        if cv is not None:
            col_vidx = [int(s) for s in cv.split(',')]
            for i in range(len(col_vidx)):
                if col_vidx[i] != i:
                    h.moveSection(h.visualIndex(i), col_vidx[i])
        
        if cw is not None:
            col_width = [int(s) for s in cw.split(',')]
            for i in range(len(col_width)):
                if col_width[i] == 0:
                    h.hideSection(i)
                else:
                    h.resizeSection(i, col_width[i])