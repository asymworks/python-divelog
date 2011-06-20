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

import os

from PySide import QtCore
from PySide.QtCore import QSettings
from PySide.QtGui import QAction, QFileDialog, QKeySequence, QMainWindow, \
    QMessageBox
from divelog.db import Logbook

class MainWindow(QMainWindow):
    '''
    MainWindow Class
    
    This is the main window for the pyDiveLog application.  It contains the
    core GUI including the tool bar, menu bar, status bar, navigation tree, and
    individual model views.
    '''
    def __init__(self):
        super(MainWindow, self).__init__()
        
        self._logbook = None
        self._logbookName = 'None'
        self._logbookPath = None
        
        self._createActions()
        self._createMenus()
        self._createLayout()
        self._createStatusBar()
        
        self.setWindowTitle(self.tr('pyDiveLog - %s') % self._logbookName)
        
        self._readSettings()
        
    def _createActions(self):
        'Create main window actions'
        self._actNewLogbook = QAction(self.tr('&New Logbook...'), self)
        self._actNewLogbook.setShortcut(QKeySequence.New)
        self._actNewLogbook.setStatusTip(self.tr('Create a new Logbook file'))
        self._actNewLogbook.triggered.connect(self._actNewLogbookTriggered)
        
        self._actOpenLogbook = QAction(self.tr('&Open Logbook...'), self)
        self._actOpenLogbook.setShortcut(QKeySequence.Open)
        self._actOpenLogbook.setStatusTip(self.tr('Open an existing Logbook file'))
        self._actOpenLogbook.triggered.connect(self._actOpenLogbookTriggered)
        
        self._actCloseLogbook = QAction(self.tr('&Close Logbook'), self)
        self._actCloseLogbook.setStatusTip(self.tr('Close the current Logbook file'))
        self._actCloseLogbook.triggered.connect(self._actCloseLogbookTriggered)
        
        self._actExit = QAction(self.tr('E&xit'), self)
        self._actExit.setShortcut(QKeySequence.Quit)
        self._actExit.setStatusTip(self.tr('Exit the pyDiveLog application'))
        self._actExit.triggered.connect(self.close)
        
    def _createLayout(self):
        'Create main window controls and layout'        
        pass
    
    def _createMenus(self):
        'Create main window menus'
        self._fileMenu = self.menuBar().addMenu(self.tr("&File"))
        self._fileMenu.addAction(self._actNewLogbook)
        self._fileMenu.addAction(self._actOpenLogbook)
        self._fileMenu.addAction(self._actCloseLogbook)
        self._fileMenu.addSeparator()
        self._fileMenu.addAction(self._actExit)
        
    def _createStatusBar(self):
        'Initialize the main window status bar'
        self.statusBar().showMessage('Ready')
        
    def _closeLogbook(self):
        'Close the current Logbook'
        if self._logbook is None:
            return
        
        self._logbook = None
        self._logbookName = 'None'
        self._logbookPath = None
        
        self._writeSettings()
        self.setWindowTitle(self.tr('pyDiveLog - %s') % self._logbookName)
        
    def _openLogbook(self, path):
        'Open an existing Logbook'
        if self._logbook is not None:
            self._closeLogbook()
            
        if not os.path.exists(path):
            QMessageBox.warning(self, self.tr('Missing Logbook File'),
                self.tr('Unable to open Logbook "%s": file not found.') % os.path.basename(path),
                QMessageBox.Ok, QMessageBox.Ok)
            return
        
        #TODO: Handle a Schema Upgrade in a user-friendly manner
        self._logbook = Logbook(path, auto_update=False)
        self._logbookName = os.path.basename(path)
        self._logbookPath = path
        
        self._writeSettings()
        self.setWindowTitle(self.tr('pyDiveLog - %s') % self._logbookName)
        
    def _readSettings(self):
        'Read main window settings from the configuration'
        settings = QSettings()
        settings.beginGroup('MainWindow')
        max = settings.value('max')
        size = settings.value('size')
        pos = settings.value('pos')
        file = settings.value('file')
        settings.endGroup()
        
        # Size and Position the Main Window
        if size is not None:
            self.resize(size)
        if pos is not None:
            self.move(pos)
            
        # HAX because QVariant is not exposed in PySide and the default
        # coercion to string is just stupid
        if max is not None and (max == 'true'):
            self.showMaximized()
        
        # Open the Logbook
        if file is not None:
            self._openLogbook(file)
        
    def _writeSettings(self):
        'Write settings to the configuration'
        settings = QSettings()
        settings.beginGroup('MainWindow')
        settings.setValue('pos', self.pos())
        settings.setValue('size', self.size())
        settings.setValue('max', self.isMaximized())
        settings.setValue('file', self._logbookPath)        
        settings.endGroup()
        
    def closeEvent(self, e):
        'Intercept an OnClose event'
        self._writeSettings()
        e.accept()
        
    #--------------------------------------------------------------------------
    # Slots
    
    @QtCore.Slot()
    def _actCloseLogbookTriggered(self):
        'Close Logbook Action Event Handler'
        self._closeLogbook()
    
    @QtCore.Slot()
    def _actNewLogbookTriggered(self):
        'New Logbook Action Event Handler'
        if self._logbook is not None:
            dir = os.path.dirname(self._logbookPath)
        else:
            dir = os.path.expanduser('~')
            
        fn = QFileDialog.getSaveFileName(self, 
            caption=self.tr('Save new Logbook as...'), dir=dir,
            filter='Logbook Files (*.lbk);;All Files (*.*)')[0]
        if fn == '':
            return
        if os.path.exists(fn):
            if QMessageBox.question(self, self.tr('Create new Logbook?'), 
                    self.tr('Logbook "%s" already exists. Would you like to overwrite it?') % os.path.basename(fn),
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) != QMessageBox.Yes:
                return
            
            # Try and remove the old Logbook file
            try:
                os.remove(fn)
            except:
                QMessageBox.error(self, self.tr('Cannot remove Logbook'),
                    self.tr('Unable to remove Logbook file "%s". Please delete this file manually.') % os.path.basename(fn),
                    QMessageBox.Ok, QMessageBox.Ok)
                return
        
        # Create a new Logbook File
        Logbook.Create(fn)
        self._openLogbook(fn)
    
    @QtCore.Slot()
    def _actOpenLogbookTriggered(self):
        'Open Logbook Action Event Handler'
        if self._logbook is not None:
            dir = os.path.dirname(self._logbookPath)
        else:
            dir = os.path.expanduser('~')
            
        fn = QFileDialog.getOpenFileName(self,
            caption=self.tr('Select a Logbook file'), dir=dir,
            filter='Logbook Files (*.lbk);;All Files(*.*)')[0]
        if fn == '':
            return
        if not os.path.exists(fn):
            if QMessageBox.question(self, self.tr('Create new Logbook?'), 
                    self.tr('Logbook "%s" does not exist. Would you like to create it?') % os.path.basename(fn),
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) != QMessageBox.Yes:
                return
            Logbook.Create(fn)
        self._openLogbook(fn)
        