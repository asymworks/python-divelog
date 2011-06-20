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

from PySide import QtCore
from PySide.QtCore import Qt, QSize
from PySide.QtGui import QDoubleValidator, QImage, QLineEdit, QPainter, \
    QPixmap, QStyle, QStyleOptionFrameV3, QToolButton, QWidget
from divelog.gui.settings import read_setting, abbr, conversion, quantities

class SearchEdit(QLineEdit):
    '''
    SearchEdit
    
    Styled search edit box which includes a search icon, clear button, and
    pre-defined preview text.
    '''
    def __init__(self, parent=None):
        super(SearchEdit, self).__init__(parent)
        
        clr_pixmap = QPixmap(':/icons/clear.png')
        self._btn_clear = QToolButton(self)
        self._btn_clear.setIcon(clr_pixmap)
        self._btn_clear.setIconSize(clr_pixmap.size())
        self._btn_clear.setCursor(Qt.ArrowCursor)
        self._btn_clear.setStyleSheet('QToolButton { border: none; padding: 0px; }');
        self._btn_clear.clicked.connect(self.clear)
        fw = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
        
        #TODO: Make a Search glyph show up properly
        self.setStyleSheet('QLineEdit { padding-right: %dpx; }' % (self._btn_clear.sizeHint().width() + fw + 1))
        msz = self.minimumSizeHint()
        self.setMinimumSize(max([msz.width(), self._btn_clear.sizeHint().height() + fw * 2 + 2]), 
                            max([msz.height(), self._btn_clear.sizeHint().height() + fw * 2 + 2]))
        self.setPlaceholderText('Search')
    
    def resizeEvent(self, e):
        sz = self._btn_clear.sizeHint()
        fw = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
        self._btn_clear.move(self.rect().right() - fw - sz.width(),
            (self.rect().bottom() + 1 - sz.height()) / 2 + 1)
        
    def sizeHint(self):
        s = super(SearchEdit, self).sizeHint()
        s.setWidth(250)
        return s
    
class QuantityEdit(QLineEdit):
    '''
    QuantityEdit
    
    Unit-Aware quantity editor class.  Contains a field which holds the
    quantity being edited.  Unit conversion is handled by the delegate class.
    The constructor takes the quantity ('depth', 'temperature', etc) as well
    as the default units ('feet', 'meters', etc).  If the default is None the
    stored default units will be used.
    '''
    def __init__(self, quantity, units=None, parent=None):
        super(QuantityEdit, self).__init__(parent)
        
        self._quantity = quantity
        self._units = units
        
        if not quantity in quantities():
            raise KeyError('Unknown Unit Quantity %s' % quantity)
        
        if self._units is None:
            self._units = read_setting('%s_units' % self._quantity)
        
        self.setValidator(QDoubleValidator(parent))
        
    def quantity(self):
        'Return the Quantity'
        return self._quantity
    
    def setQuantity(self, value):
        'Set the Quantity'
        if not value in quantities():
            raise KeyError('Unknown Unit Quantity %s' % value)
        
        self._quantity = value
        self._units = read_setting('%s_units' % self._quantity)
    
    def units(self):
        'Return the Units'
        return self._unit
    
    def setUnits(self, value):
        'Set the Units'
        self._units = value
        
    def toNative(self):
        'Return the Native Units'
        try:
            val = float(self.text())
        except ValueError:
            val = 0
        conv = conversion(self._quantity, self._units)
        
        return conv[0](val)
    
    def fromNative(self, val):
        'Set the value from the Native Units'
        conv = conversion(self._quantity, self._units)
        self.setText('%g' % conv[1](val))
        
class RatingEditor(QWidget):
    '''
    Star Rating Editor
    
    Editor class to edit a 5-star rating.  Clicking the control enables dragging
    the mouse to select the rating.  This control is compatible with Qt MVF.
    '''
    editingFinished = QtCore.Signal()
    
    def __init__(self, parent=None):
        super(RatingEditor, self).__init__(parent)
        
        self.setAutoFillBackground(True)
        self.setFocusPolicy(Qt.ClickFocus)
        self._sopt = QStyleOptionFrameV3()
        
        self._star = QImage(':/icons/star.png')
        self._blue = QImage(':/icons/star-blue.png')
        self._dot = QImage(':/icons/star-dot.png')
        
        self._rating = 0
        self._active = False
    
    def _updateRating(self, e):
        'Update the Rating based on the Mouse Event'
        r = int(round(float(e.x()) / self._star.width()))
        self.setRating(r)
        
    def mousePressEvent(self, e):
        'Mouse Press Event'
        if e.buttons() == Qt.LeftButton:
            self._active = True
            self._updateRating(e)
        
    def mouseMoveEvent(self, e):
        'Mouse Move Event'
        if self._active:
            self._updateRating(e)
            
    def mouseReleaseEvent(self, e):
        'Mouse Release Event'
        if self._active:
            self._active = False
            self.update()
            self.editingFinished.emit()
    
    def paintEvent(self, e):
        'Custom Paint Event'
        p = QPainter(self)
        
        opt = QStyleOptionFrameV3()
        opt.initFrom(self)
        opt.rect = self.contentsRect()
        opt.lineWidth = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth, opt, self)
        opt.midLineWidth = 0
        opt.state = opt.state | QStyle.State_Sunken
        
        if self._active:
            opt.state = opt.state | QStyle.State_HasFocus
        else:
            opt.state = opt.state & ~QStyle.State_HasFocus;
        
        self.style().drawPrimitive(QStyle.PE_PanelLineEdit, opt, p)

        y = (opt.rect.height() - self._star.height()) / 2 
        width = self._star.width()
        
        for i in range(0, 5):
            x = i*(width + 1) + opt.lineWidth
            
            if self._rating >= i+0.5:
                p.drawImage(x, y, self._star if not self._active else self._blue)
            else:
                p.drawImage(x, y, self._dot)
    
    def rating(self):
        'Return the Rating'
        return self._rating
        
    def sizeHint(self):
        'Return the Size Hint'
        return QSize((self._star.width()+2) * 5, self._star.height()+2)
    
    @QtCore.Slot(int)
    def setRating(self, r):
        'Set the new Rating'
        if r < 0:
            r = 0
        elif r > 5:
            r = 5
        
        self._rating = r
        self.update()
    
    
    