#!/usr/bin/env python2
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

import sys, os, logging, time
from PySide import QtCore
from PySide.QtCore import Qt, QAbstractListModel, QModelIndex, QObject, \
    QResource, QSettings, QThread
from PySide.QtGui import QApplication, QComboBox, QFileDialog, QGridLayout, \
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPixmap, QProgressBar, \
    QPushButton, QTextEdit, QVBoxLayout, QWidget
from divelog.db import Logbook, models
from divelog.dc import list_drivers, list_parsers
from divelog.gui.wizards import AddDiveComputerWizard

# QSettings Information
__ORG_NAME = 'Asymworks'
__ORG_DOMAIN = 'asymworks.com'
__APP_NAME = 'qdcxfer'
__APP_VERSION = '0.1.0'

# filter to log =< INFO into stdout and rest to stderr
class SingleLevelFilter(logging.Filter):
    def __init__(self, min=None, max=None):
        self.min = min or 0
        self.max = max or 100

    def filter(self, record):
        return self.min <= record.levelno <= self.max

# Initialize Logging
logger = logging.getLogger()
h1 = logging.StreamHandler(sys.stdout)
f1 = SingleLevelFilter(max=logging.INFO)
h1.addFilter(f1)
h2 = logging.StreamHandler(sys.stderr)
f2 = SingleLevelFilter(min=logging.WARN)
h2.addFilter(f2)
logger.addHandler(h1)
logger.addHandler(h2)
logger.setLevel(logging.INFO)

class TransferWorker(QObject):
    '''
    Dive Computer Transfer Worker Object
    
    Given a Dive Computer object, connects and downloads all new dives since
    the last transfer.
    '''
    finished = QtCore.Signal()
    parsedDive = QtCore.Signal(models.Dive)
    progress = QtCore.Signal(int)
    status = QtCore.Signal(str)
    started = QtCore.Signal(int)
    
    class Reporter(object):
        def __init__(self, worker):
            self.worker = worker
        def update(self, value):
            self.worker.progress.emit(value)
    
    def __init__(self, dc):
        super(TransferWorker, self).__init__()
        self._dc = dc
        
    @QtCore.Slot()
    def start(self):
        'Run the Transfer'
        self.status.emit(self.tr('Starting Transfer from %s') % self._dc.name)
        time.sleep(0.1)
        
        # Load the Driver
        try:
            d = list_drivers()[self._dc.driver]
            da = self._dc.driver_args
            dopts = [] if da is None or da == '' else da.split(':')
            driver = d['class'](*dopts)
            self.status.emit(self.tr('Loaded Driver "%s"') % self._dc.driver)
        except:
            self.status.emit(self.tr('Error: Cannot load driver "%s"') % self._dc.driver)
        
        # Load the Parser and Adapter Class
        try:
            p = list_parsers()[self._dc.parser]
            pa = self._dc.parser_args
            popts = [] if pa is None or pa == '' else pa.split(':')
            parser = p['class'](*popts)
            adapter_cls = p['adapter']
            self.status.emit(self.tr('Loaded Parser "%s"') % self._dc.parser)
        except:
            self.status.emit(self.tr('Error: Cannot load parser "%s"') % self._dc.parser)
        
        # Connect and check Serial Number
        self.status.emit('Connecting to %s' % self._dc.name)
        
        #FIXME: driver.discover() blocks main thread
        time.sleep(0.1)
        devs = driver.discover()
        
        drv = None
        for _dev in devs:
            time.sleep(0.1)
            try:
                _drv = d['class'](*dopts)
                _drv.connect(_dev)
                if _drv.serial == self._dc.serial:
                    drv = _drv
                    break
                else:
                    _drv.disconnect()
            except:
                self.status.emit('Error: Could not connect to %s (Driver Error)' % self._dc.name)
                self.finished.emit()
                return
        
        if drv == None:
            self.status.emit('Error: Could not connect to %s (Device Not Found)' % self._dc.name)
            
        time.sleep(0.1)
        
        # Transfer Dives
        drv.set_token(self._dc.token)
        nbytes = drv.get_bytecount()
        self.status.emit('Transferring %d bytes...' % nbytes)
        self.started.emit(nbytes)
        _dives = drv.transfer(TransferWorker.Reporter(self))
        token = drv.issue_token()
        self.status.emit('Transfer Finished (%d new dives)' % len(_dives))
        drv.disconnect()
        
        # Parse Dive Data
        for _dive in _dives:
            dive = models.Dive()
            dive.init_from_adapter(adapter_cls(parser.parse(_dive)))
            dive.computer = self._dc
            self.status.emit(self.tr('Parsed Dive: %s') % dive.dive_datetime.strftime('%x %X'))
            self.parsedDive.emit(dive)
        
        # Update Dive Computer Token
        self._dc.token = token
        
        # Finished Transferring
        self.status.emit(self.tr('Transfer Successful'))
        self.finished.emit()

class DiveComputersModel(QAbstractListModel):
    '''
    Dive Computers Model
    
    Models the list of Dive Computers in a Logbook
    '''
    def __init__(self, logbook):
        super(DiveComputersModel, self).__init__()
        self._logbook = logbook
        self._computers = []
        self.reload()
        
    def reload(self):
        self.beginResetModel()
        self._computers = self._logbook.all_computers
        self.endResetModel()
        
    def rowCount(self, parent=QModelIndex()):
        return len(self._computers)
    
    def data(self, index, role):
        c = self.rowCount()
        if not index.isValid() or index.row() < 0 or index.row() >= c:
            return None
        
        if role in [Qt.DisplayRole, Qt.EditRole]:
            return self._computers[index.row()].name
        elif role == Qt.UserRole + 0:
            return self._computers[index.row()]
        return None

class TransferPanel(QWidget):
    '''
    Transfer Panel
    
    This Panel is the main dialog box for the Dive Computer Transfer GUI
    '''
    def __init__(self, parent=None):
        super(TransferPanel, self).__init__(parent)
        
        self._logbook = None
        self._logbookName = 'None'
        self._logbookPath = None
        
        self._createLayout()
        
        self._readSettings()
        self.setWindowTitle(self.tr('DC Transfer - %s') % self._logbookName)
        
    def _createLayout(self):
        'Create the Widget Layout'
        
        self._txtLogbook = QLineEdit()
        self._txtLogbook.setReadOnly(True)
        self._lblLogbook = QLabel(self.tr('&Logbook File:'))
        self._lblLogbook.setBuddy(self._txtLogbook)
        self._btnBrowse = QPushButton('...')
        self._btnBrowse.clicked.connect(self._btnBrowseClicked)
        self._btnBrowse.setStyleSheet('QPushButton { min-width: 24px; max-width: 24px; }')
        self._btnBrowse.setToolTip(self.tr('Browse for a Logbook'))
        
        self._cbxComputer = QComboBox()
        self._lblComputer = QLabel(self.tr('Dive &Computer:'))
        self._lblComputer.setBuddy(self._cbxComputer)
        self._btnAddComputer = QPushButton(QPixmap(':/icons/list-add.png'), self.tr(''))
        self._btnAddComputer.setStyleSheet('QPushButton { min-width: 24px; min-height: 24; max-width: 24px; max-height: 24; }')
        self._btnAddComputer.clicked.connect(self._btnAddComputerClicked)
        self._btnRemoveComputer = QPushButton(QPixmap(':/icons/list-remove.png'), self.tr(''))
        self._btnRemoveComputer.setStyleSheet('QPushButton { min-width: 24px; min-height: 24; max-width: 24px; max-height: 24; }')
        self._btnRemoveComputer.clicked.connect(self._btnRemoveComputerClicked)
        
        hbox = QHBoxLayout()
        hbox.addWidget(self._btnAddComputer)
        hbox.addWidget(self._btnRemoveComputer)
        
        gbox = QGridLayout()
        gbox.addWidget(self._lblLogbook, 0, 0)
        gbox.addWidget(self._txtLogbook, 0, 1)
        gbox.addWidget(self._btnBrowse, 0, 2)
        gbox.addWidget(self._lblComputer, 1, 0)
        gbox.addWidget(self._cbxComputer, 1, 1)
        gbox.addLayout(hbox, 1, 2)
        gbox.setColumnStretch(1, 1)
        
        self._pbTransfer = QProgressBar()
        self._pbTransfer.reset()
        self._txtStatus = QTextEdit()
        self._txtStatus.setReadOnly(True)
        
        self._btnTransfer = QPushButton(self.tr('&Transfer Dives'))
        self._btnTransfer.clicked.connect(self._btnTransferClicked)
        
        self._btnExit = QPushButton(self.tr('E&xit'))
        self._btnExit.clicked.connect(self.close)
        
        hbox = QHBoxLayout()
        hbox.addWidget(self._btnTransfer)
        hbox.addStretch()
        hbox.addWidget(self._btnExit)
        
        vbox = QVBoxLayout()
        vbox.addLayout(gbox)
        vbox.addWidget(self._pbTransfer)
        vbox.addWidget(self._txtStatus)
        vbox.addLayout(hbox)
        
        self.setLayout(vbox)
        
    def _closeLogbook(self):
        'Close the current Logbook'
        if self._logbook is None:
            return
        
        self._logbook = None
        self._logbookName = 'None'
        self._logbookPath = None
        
        self._txtLogbook.clear()
        self._cbxComputer.setModel(None)
        
        self._writeSettings()
        self.setWindowTitle(self.tr('DC Transfer - %s') % self._logbookName)
        
    def _openLogbook(self, path):
        'Open an existing Logbook'
        if self._logbook is not None:
            self._closeLogbook()
            
        if not os.path.exists(path):
            QMessageBox.critical(self, self.tr('Missing Logbook'), 
                self.tr('Logbook File "%s" does not exist.') % path)
            return
        
        #TODO: Handle a Schema Upgrade in a user-friendly manner
        self._logbook = Logbook(path, auto_update=False)
        self._logbookName = os.path.basename(path)
        self._logbookPath = path
        
        self._txtLogbook.setText(self._logbookPath)
        self._cbxComputer.setModel(DiveComputersModel(self._logbook))
        
        self._writeSettings()
        self.setWindowTitle(self.tr('DC Transfer - %s') % self._logbookName)
        
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
    def _btnAddComputerClicked(self):
        'Add a Dive Computer'
        dc = AddDiveComputerWizard.RunWizard(self)
        
        if dc is not None:
            self._logbook.session.add(dc)
            self._logbook.session.commit()
            self._cbxComputer.model().reload()
            self._cbxComputer.setCurrentIndex(self._cbxComputer.findText(dc.name))
    
    @QtCore.Slot()
    def _btnRemoveComputerClicked(self):
        'Remove a Dive Computer'
        idx = self._cbxComputer.currentIndex()
        dc = self._cbxComputer.itemData(idx, Qt.UserRole+0)
        if QMessageBox.question(self, self.tr('Delete Dive Computer?'), 
                    self.tr('Are you sure you want to delete "%s"?') % dc.name,
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) == QMessageBox.Yes:
            self._logbook.session.delete(dc)
            self._logbook.session.commit()
            self._cbxComputer.model().reload()
    
    @QtCore.Slot()
    def _btnBrowseClicked(self):
        'Browse for a Logbook File'
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
        
    @QtCore.Slot()
    def _btnTransferClicked(self):
        'Transfer Dives'
        idx = self._cbxComputer.currentIndex()
        dc = self._cbxComputer.itemData(idx, Qt.UserRole+0)
        
        if self._logbook.session.dirty:
            print "Flushing dirty session"
            self._logbook.rollback()
        
        self._txtLogbook.setEnabled(False)
        self._btnBrowse.setEnabled(False)
        self._cbxComputer.setEnabled(False)
        self._btnAddComputer.setEnabled(False)
        self._btnRemoveComputer.setEnabled(False)
        self._btnTransfer.setEnabled(False)
        self._btnExit.setEnabled(False)
        
        self._txtStatus.clear()
        
        thread = QThread(self)
        
        #FIXME: ZOMG HAX: Garbage Collector will eat TransferWorker when moveToThread is called
        #NOTE: Qt.QueuedConnection is important...
        self.worker = None
        self.worker = TransferWorker(dc)
        thread.started.connect(self.worker.start, Qt.QueuedConnection)
        self.worker.moveToThread(thread)
        self.worker.finished.connect(self._transferFinished, Qt.QueuedConnection)
        self.worker.finished.connect(self.worker.deleteLater, Qt.QueuedConnection)
        self.worker.finished.connect(thread.deleteLater, Qt.QueuedConnection)
        self.worker.progress.connect(self._transferProgress, Qt.QueuedConnection)
        self.worker.started.connect(self._transferStart, Qt.QueuedConnection)
        self.worker.status.connect(self._transferStatus, Qt.QueuedConnection)
        
        thread.start()
        
    @QtCore.Slot(str)
    def _transferStatus(self, msg):
        'Transfer Status Message'
        self._txtStatus.append(msg)
        
    @QtCore.Slot(int)
    def _transferStart(self, nBytes):
        'Transfer Thread Stated'
        if nBytes > 0:
            self._pbTransfer.setMaximum(nBytes)
        else:
            self._pbTransfer.setMaximum(100)
        self._pbTransfer.reset()
        
    @QtCore.Slot(int)
    def _transferProgress(self, nTransferred):
        'Transfer Thread Progress Event'
        self._pbTransfer.setValue(nTransferred)
        
    @QtCore.Slot(models.Dive)
    def _transferParsed(self, dive):
        'Transfer Thread Parsed Dive'
        self._logbook.session.add(dive)
        
    @QtCore.Slot()
    def _transferFinished(self):
        'Transfer Thread Finished'
        self._logbook.session.commit()
        
        self._txtLogbook.setEnabled(True)
        self._btnBrowse.setEnabled(True)
        self._cbxComputer.setEnabled(True)
        self._btnAddComputer.setEnabled(True)
        self._btnRemoveComputer.setEnabled(True)
        self._btnTransfer.setEnabled(True)
        self._btnExit.setEnabled(True)
        
def main():
    'Main Program Entry Point'
    QResource.registerResource('res/icons.rcc')
    
    app = QApplication(sys.argv)
    app.setOrganizationName(__ORG_NAME)
    app.setOrganizationDomain(__ORG_DOMAIN)
    app.setApplicationName(__APP_NAME)
    app.setApplicationVersion(__APP_VERSION)
    
    w = TransferPanel()
    w.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()