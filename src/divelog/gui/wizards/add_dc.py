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

import time
from PySide import QtCore
from PySide.QtCore import Qt, QAbstractListModel, QAbstractTableModel, \
    QModelIndex, QObject, QThread
from PySide.QtGui import QAbstractItemView, QComboBox, QDialog, QGridLayout, \
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTreeView, \
    QVBoxLayout, QWizard, QWizardPage
from divelog.db import models
from divelog.dc import list_drivers, list_parsers
from divelog.gui.mvf.delegates import NoFocusDelegate

class ListTreeView(QTreeView):
    def __init__(self, parent=None):
        super(ListTreeView, self).__init__(parent)
        
        self.setAlternatingRowColors(True)
        self.setItemDelegate(NoFocusDelegate(self))
        self.setItemsExpandable(False)
        self.setIndentation(0)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setUniformRowHeights(True)
        
    def drawBranches(self, painter, rect, index):
        'Pretend to not be a tree view'
        pass

class DiscoveryWorker(QObject):
    '''
    Device Discovery Worker Object
    
    Uses the Dive Computer Driver discover() method to discover connected dive
    computers.  The foundDevice() signal is emitted for each device found.  The
    parameters passed to foundDevice() are the computer name, computer model,
    and serial number (all as strings).
    '''
    foundDevice = QtCore.Signal(str, str, str)
    finished = QtCore.Signal()
    
    def __init__(self, dcls, dopts, parent=None):
        super(DiscoveryWorker, self).__init__(parent)
        self.drv_class = dcls
        self.drv_opts  = dopts
        
    @QtCore.Slot()
    def start(self):
        'Discover Devices using the passed Driver'
        time.sleep(0.1)
        driver = self.drv_class(*self.drv_opts)
        disc = driver.discover()
        for d in disc:
            drv = self.drv_class(*self.drv_opts)
            drv.connect(d)
            self.foundDevice.emit(d['name'], drv.model, drv.serial)
            drv.disconnect()
        self.finished.emit()
        
class DiscoveredComputersModel(QAbstractTableModel):
    'Discovered Computer List Model'
    def __init__(self):
        super(DiscoveredComputersModel, self).__init__()
        self._computers = []
        
    @QtCore.Slot(str, str, str)
    def addItem(self, name, model, serial):
        dev = {'serial': serial, 'name': name, 'model': model}
        row = len(self._computers)
        self.beginInsertRows(QModelIndex(), row, row)
        self._computers.append(dev)
        self.endInsertRows()
    
    @QtCore.Slot()
    def clear(self):
        self.beginResetModel()
        self._computers = []
        self.endResetModel()
        
    def columnCount(self, parent=QModelIndex()):
        return 3
        
    def rowCount(self, parent=QModelIndex()):
        return len(self._computers)
    
    def hasChildren(self, parent):
        return False
    
    def headerData(self, col, orientation, role):
        if (orientation == Qt.Horizontal and role == Qt.DisplayRole):
            return ['Device Name', 'Device Model', 'Serial Number'][col]
        return None
    
    def data(self, index, role):
        if not index.isValid():
            return None
        c = ['name', 'model', 'serial'][index.column()]
        r = self._computers[index.row()]
        
        if role == Qt.DisplayRole:
            return r[c]
        return None    

class DriverModel(QAbstractListModel):
    'Dive Computer Driver Model'
    def __init__(self):
        super(DriverModel, self).__init__()
        self._drivers = list_drivers()
    
    def rowCount(self, parent=QModelIndex()):
        return len(self._drivers)
    
    def data(self, index, role):
        c = self.rowCount()
        if not index.isValid() or index.row() < 0 or index.row() >= c:
            return None
        
        if role in [Qt.DisplayRole, Qt.EditRole]:
            return self._drivers.keys()[index.row()]
        elif role == Qt.UserRole + 0:
            return self._drivers[self._drivers.keys()[index.row()]]['desc']
        elif role == Qt.UserRole + 1:
            return self._drivers[self._drivers.keys()[index.row()]]['cls']
        return None
    
class ParserModel(QAbstractListModel):
    'Dive Computer Parser Model'
    def __init__(self):
        super(ParserModel, self).__init__()
        self._parsers = list_parsers()
    
    def rowCount(self, parent=QModelIndex()):
        return len(self._parsers)
    
    def data(self, index, role):
        c = self.rowCount()
        if not index.isValid() or index.row() < 0 or index.row() >= c:
            return None
        
        if role in [Qt.DisplayRole, Qt.EditRole]:
            return self._parsers.keys()[index.row()]
        elif role == Qt.UserRole + 0:
            return self._parsers[self._parsers.keys()[index.row()]]['desc']
        elif role == Qt.UserRole + 1:
            return self._parsers[self._parsers.keys()[index.row()]]['cls']
        return None

class Pages:
    Intro   = 0
    Custom  = 1
    Browse  = 2
    Finish  = 3
 
# Pre-defined Computer Types   
ComputerTypes = [
    {
        'name': 'Uwatec Aladin Tec 2G', 
        'driver': 'smart',
        'parser': 'AladinTec2G',
        'driveropt': '',
        'parseropt': '',
    },
]
    
class IntroPage(QWizardPage):
    '''
    Introduction Wizard Page
    
    Contains the introduction text and a combo box to select either a pre-
    defined computer model or a custom computer type.
    '''
    def __init__(self, parent=None):
        super(IntroPage, self).__init__(parent)
        
        self._createLayout()
        
        self.registerField('type', self._cbxType)
        self.setTitle(self.tr('Add a Dive Computer'))
        self.setSubTitle(self.tr('Select the type of Dive Computer to add.  Make sure the computer is connected and ready to download before proceeding.'))

    def nextId(self):
        'Return the next Page Id'
        if self._cbxType.currentIndex() == len(ComputerTypes):
            return Pages.Custom
        else:
            return Pages.Browse
    
    def _createLayout(self):
        'Create the Wizard Page Layout'
        
        self._cbxType = QComboBox()
        self._lblType = QLabel(self.tr('Dive Computer &Type'))
        self._lblType.setBuddy(self._cbxType)
        
        for t in ComputerTypes:
            self._cbxType.addItem(t['name'])
        self._cbxType.addItem('Custom...')
        
        gbox = QGridLayout()
        gbox.addWidget(self._lblType, 0, 0)
        gbox.addWidget(self._cbxType, 0, 1)
        
        vbox = QVBoxLayout()
        vbox.addLayout(gbox)
        vbox.addStretch()
        
        self.setLayout(vbox)
    
class CustomPage(QWizardPage):
    '''
    Custom Computer Wizard Page
    
    Contains inputs for the Driver and Parser that the user can define a 
    custom mix of driver/parser/options.
    '''
    def __init__(self, parent=None):
        super(CustomPage, self).__init__(parent)
        
        self._createLayout()
        
        self.registerField('driver', self._cbxDriver)
        self.registerField('parser', self._cbxParser)
        self.registerField('driveropt', self._txtDOpts)
        self.registerField('parseropt', self._txtPOpts)
    
        self.setTitle(self.tr('Setup Driver Options'))
        self.setSubTitle(self.tr('Select the Driver and Parser to use with your Dive Computer.'))
    
    def nextId(self):
        'Return the next Page Id'
        return Pages.Browse
    
    def _createLayout(self):
        'Create the Wizard Page Layout'
        
        self._cbxDriver = QComboBox()
        self._cbxDriver.setModel(DriverModel())
        self._lblDriver = QLabel(self.tr('&Driver:'))
        self._lblDriver.setBuddy(self._cbxDriver)
        
        self._cbxParser = QComboBox()
        self._cbxParser.setModel(ParserModel())
        self._lblParser = QLabel(self.tr('&Parser:'))
        self._lblParser.setBuddy(self._cbxParser)
        
        self._txtDOpts = QLineEdit()
        self._lblDOpts = QLabel(self.tr('Driver Options:'))
        self._lblDOpts.setBuddy(self._txtDOpts)
        
        self._txtPOpts = QLineEdit()
        self._lblPOpts = QLabel(self.tr('Parser Options:'))
        self._lblPOpts.setBuddy(self._txtPOpts)
        
        gbox = QGridLayout()
        gbox.addWidget(self._lblDriver, 0, 0)
        gbox.addWidget(self._cbxDriver, 0, 1)
        gbox.addWidget(self._lblParser, 1, 0)
        gbox.addWidget(self._cbxParser, 1, 1)
        gbox.addWidget(self._lblDOpts, 2, 0)
        gbox.addWidget(self._txtDOpts, 2, 1)
        gbox.addWidget(self._lblPOpts, 3, 0)
        gbox.addWidget(self._txtPOpts, 3, 1)
        
        vbox = QVBoxLayout()
        vbox.addLayout(gbox)
        vbox.addStretch()
        
        self.setLayout(vbox)
    
class BrowsePage(QWizardPage):
    '''
    Browse Computers Wizard Page
    
    Attempts to discover connected computers with the given driver and parser
    and allows the user to select which one to use.  This sets the serial 
    number that is linked to the computer's profile
    '''
    def __init__(self, parent=None):
        super(BrowsePage, self).__init__(parent)
        
        self._model = DiscoveredComputersModel()
        self._createLayout()
        
        self.registerField('serial*', self._txtSerial)
        self.setTitle(self.tr('Select your Dive Computer'))
        self.setSubTitle(self.tr('Select the Dive Computer from the list below.  If your Dive Computer doesn\'t appear, click Refresh List or Help for more options.'))
    
    def nextId(self):
        'Return the next Page Id'
        return Pages.Finish
    
    def initializePage(self):
        'Initialize the Page'
        self._refresh()
        
    @QtCore.Slot(QModelIndex, QModelIndex)
    def _selectionChanged(self, selected, deselected):
        'Selection Changed'
        self.completeChanged.emit()
        if self._lvDevices.selectionModel().hasSelection():
            idx = self._model.index(self._lvDevices.selectedIndexes()[0].row(), 2)
            self._txtSerial.setText(self._model.data(idx, Qt.DisplayRole))
        else:
            self._txtSerial.clear()
        
    @QtCore.Slot()
    def _discoverFinished(self):
        'Discover Thread Finished'
        self._btnRefresh.setEnabled(True)
        self._btnRefresh.setText(self.tr('&Refresh List'))
        
        if self._model.rowCount() == 0:
            QMessageBox.information(self, self.tr('No Devices Found'),
                self.tr('No Dive Computers were found using the specified driver.  Please ensure your device is connected and press Refresh List.'),
                QMessageBox.Ok, QMessageBox.Ok)
    
    @QtCore.Slot()
    def _refresh(self):
        'Refresh the list of Computers'
        self._btnRefresh.setEnabled(False)
        self._btnRefresh.setText('Scanning...')
        self._model.clear()
        
        typ = self.wizard().field('type')
        if typ == len(ComputerTypes):
            # Custom Computer Type
            didx = self.wizard().field('driver')
            drvr = list_drivers().keys()[didx]
            dopt = self.wizard().field('driveropt')
        else:
            # Predefined Computer Type
            drvr = ComputerTypes[typ]['driver']
            dopt = ComputerTypes[typ]['driveropt']
        
        dclass = list_drivers()[drvr]['class']
        doptions = [] if dopt == '' else dopt.split(':')
        
        thread = QThread(self)
        
        #FIXME: ZOMG HAX: Garbage Collector will eat DiscoveryWorker when moveToThread is called
        #NOTE: Qt.QueuedConnection is important...
        self.worker = None
        self.worker = DiscoveryWorker(dclass, doptions)
        self.worker.moveToThread(thread)
        thread.started.connect(self.worker.start, Qt.QueuedConnection)
        self.worker.foundDevice.connect(self._model.addItem, Qt.QueuedConnection)
        self.worker.finished.connect(self._discoverFinished, Qt.QueuedConnection)
        self.worker.finished.connect(self.worker.deleteLater, Qt.QueuedConnection)
        self.worker.finished.connect(thread.deleteLater, Qt.QueuedConnection)

        thread.start()
    
    def _createLayout(self):
        'Create the Wizard Page Layout'
        
        self._lblDevices = QLabel(self.tr('Select a Dive Computer:'))
        self._lvDevices = ListTreeView()
        self._lvDevices.setModel(self._model)
        self._lvDevices.selectionModel().selectionChanged.connect(self._selectionChanged)
        
        self._btnRefresh = QPushButton(self.tr('&Refresh List'))
        self._btnRefresh.clicked.connect(self._refresh)
        
        self._txtSerial = QLineEdit()
        self._txtSerial.setVisible(False)
        
        hbox = QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(self._btnRefresh)
        
        vbox = QVBoxLayout()
        vbox.addWidget(self._lblDevices)
        vbox.addWidget(self._lvDevices, 1)
        vbox.addLayout(hbox)
        
        self.setLayout(vbox)
        
        
class FinishPage(QWizardPage):
    '''
    Finish Wizard Page
    
    Contains a summary of the computer and a space for the user to enter a 
    name for the Computer.
    '''
    def __init__(self, parent=None):
        super(FinishPage, self).__init__(parent)
        
        self._createLayout()
        
        self.registerField('name*', self._txtName)
        self.setTitle(self.tr('Name your Dive Computer'))
        self.setSubTitle(self.tr('Enter a name for the Dive Computer to finish adding the Dive Computer to the Logbook.'))
    
    def nextId(self):
        'Return the next Page Id'
        return -1
    
    def _createLayout(self):
        'Create the Wizard Page Layout'
        
        self._txtName = QLineEdit()
        self._lblName = QLabel(self.tr('Computer &Name:'))
        self._lblName.setBuddy(self._txtName)
        
        gbox = QGridLayout()
        gbox.addWidget(self._lblName, 0, 0)
        gbox.addWidget(self._txtName, 0, 1)
        
        vbox = QVBoxLayout()
        vbox.addLayout(gbox)
        vbox.addStretch()
        
        self.setLayout(vbox)
    
    
class AddDiveComputerWizard(QWizard):
    '''
    Qt Wizard to add a new Dive Computer to the Logbook
    
    Contains four pages: intro/select computer type, custom computer setup,
    and browse computers.  The wizard will configure a new DiveComputer
    instance which can then be added to the Logbook.
    '''
    def __init__(self, parent=None):
        super(AddDiveComputerWizard, self).__init__(parent)
        
        self.setPage(Pages.Intro, IntroPage(self))
        self.setPage(Pages.Custom, CustomPage(self))
        self.setPage(Pages.Browse, BrowsePage(self))
        self.setPage(Pages.Finish, FinishPage(self))
        
        self.setWindowTitle(self.tr('Add a Dive Computer'))

    @classmethod
    def RunWizard(cls, parent=None):
        'Run the Add Dive Computer Wizard and return a DiveComputer object'
        wiz = cls(parent)
        if wiz.exec_() == QDialog.Rejected:
            return None

        # Handle Wizard Fields
        typ = wiz.field('type')
        if typ == len(ComputerTypes):
            # Custom Computer Type
            didx = wiz.field('driver')
            pidx = wiz.field('parser')
            drvr = list_drivers().keys()[didx]
            prsr = list_parsers().keys()[pidx]
            dopt = wiz.field('driveropt')
            popt = wiz.field('parseropt')
        else:
            # Predefined Computer Type
            drvr = ComputerTypes[typ]['driver']
            prsr = ComputerTypes[typ]['parser']
            dopt = ComputerTypes[typ]['driveropt']
            popt = ComputerTypes[typ]['parseropt']
        
        serno = wiz.field('serial')
        name = wiz.field('name')
        
        # Create the DiveComputer model
        dc = models.DiveComputer()
        dc.driver = drvr
        dc.serial = serno
        dc.name = name
        dc.parser = prsr
        dc.driver_args = dopt
        dc.parser_args = popt
        
        return dc
    