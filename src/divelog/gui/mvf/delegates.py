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

from PySide.QtCore import Qt, QSize, QDate, QDateTime, QTime
from PySide.QtGui import QApplication, QComboBox, QDateTimeEdit, QImage
from PySide.QtGui import QStyle, QStyleOptionViewItem, QStyleOptionViewItemV4, \
    QStyledItemDelegate
from divelog.gui.controls import RatingEditor
from divelog.gui.settings import read_setting, quantities, abbr, conversion

class CustomDelegate(QStyledItemDelegate):
    '''
    Custom Delegate Base Class
    
    Provides helper methods for drawing styled items since QStyledItemDelegate 
    inexplicably does not implement the protected QItemDelegate draw*() 
    methods.  Also implements setEditorData() and setModelData() for combo
    boxes, which do not work properly with QDataWidgetMapper.
    
    CustomDelegate also provides a hook function to allow subclasses to perform
    filtering on the display parameters (contained in a QStyleOptionViewItemV4
    instance) before the widget is drawn.  See the filter() method documentation
    for more information.
    ''' 
    def drawBackground(self, painter, option, index):
        '''Draw the background only of a styled item'''
        opt = QStyleOptionViewItemV4(option)
        self.initStyleOption(opt, index)
        
        if opt.widget is None:
            style = QApplication.style()
        else:
            style = opt.widget.style()
        
        style.drawPrimitive(QStyle.PE_PanelItemViewItem, opt, painter, opt.widget)
        
    def filter(self, option, index):
        '''
        Inline Option Filter
        
        This method can be used to tweak the QStyleOptionViewItemV4 after it
        has been initialized with the view data, directly before it is drawn
        using style.drawWidget().  This method must return an instance of
        QStyleOptionViewItemV4.
        
        The current model index is also provided so that the filter function
        can use context to alter filter behavior.  The default behavior 
        provides no filtering.
        
        The primary advantage to this approach is that it moves the content
        display filtering out of the model (QAbstractItemModel::data()) into
        the presentation layer so that the same model data can be displayed in
        various ways by different views.
        '''
        return option
        
    def paint(self, painter, option, index):
        '''Re-implementation from QStyledItemDelegate, calls filter()'''
        opt = QStyleOptionViewItemV4(option)
        self.initStyleOption(opt, index)
        
        # Filter the Style Option View Item
        opt_ = self.filter(opt, index)
        if opt_ and isinstance(opt_, QStyleOptionViewItem):
            opt = opt_
        
        # Draw the item view
        if opt.widget is None:
            style = QApplication.style()
        else:
            style = opt.widget.style()
    
        style.drawControl(QStyle.CE_ItemViewItem, opt, painter, opt.widget)
    
    def setEditorData(self, editor, index):
        # http://bugreports.qt.nokia.com/browse/QTBUG-428 - combo boxes don't play nice with qdatawidget mapper
        if isinstance(editor, QComboBox):
            text = index.data(Qt.EditRole)
            if text == None:
                text = ''
            if editor.isEditable():
                editor.setCurrentText(text)
            else:
                editor.setCurrentIndex(editor.findData(text, Qt.EditRole))
        elif isinstance(editor, QDateTimeEdit):
            v = index.data(Qt.EditRole)
            d = QDate(v.year, v.month, v.day)
            t = QTime(v.hour, v.minute, v.second)
            dt = QDateTime(d, t)
            editor.setDateTime(dt)
        elif isinstance(editor, RatingEditor):
            r = index.data(Qt.EditRole)
            editor.setRating(r)
        else:
            super(CustomDelegate, self).setEditorData(editor, index)
            
    def setModelData(self, editor, model, index):
        # http://bugreports.qt.nokia.com/browse/QTBUG-428 - combo boxes don't play nice with qdatawidget mapper
        if isinstance(editor, QComboBox):
            model.setData(index, editor.itemData(editor.currentIndex(), Qt.EditRole))
        elif isinstance(editor, QDateTimeEdit):
            model.setData(index, editor.dateTime().toPython(), Qt.EditRole)
        elif isinstance(editor, RatingEditor):
            model.setData(index, editor.rating(), Qt.EditRole)
        else:
            super(CustomDelegate, self).setModelData(editor, model, index)

class NoFocusDelegate(CustomDelegate):
    '''
    No-Focus Item Delegate
    
    Model View Delegate which suppresses painting of the focus rectangle.  
    Useful for read-only views which should only support row selects.
    '''
    def paint(self, painter, option, index):
        option.state &= ~(QStyle.State_HasFocus)
        super(NoFocusDelegate, self).paint(painter, option, index)
        
class DateTimeDelegate(NoFocusDelegate):
    '''
    Date/Time Delegate
    
    Delegate which formats a datetime value according to the desired date/time
    format stored in settings.  Note that this formats Python datetime, _not_
    Qt DateTime since the overhead of constructing QDateTime and converting is
    quite high.
    '''
    def displayText(self, value, locale):
        fmt = read_setting('dtformat', '%x %I:%M %p')
        return value.strftime(fmt)
    
class MinutesDelegate(NoFocusDelegate):
    '''
    Minutes Delegate
    
    Delegate which formats a number of minutes as hh:mm.
    '''
    def displayText(self, value, locale):
        return "%d:%02d" % divmod(value, 60)
    
class RatingDelegate(NoFocusDelegate):
    '''
    Star Rating Item Delegate
    
    Model View Delegate which draws a rating score between zero and five as a
    line of zero to five star glyphs.  A custom star glyph can be passed to the
    constructor, otherwise a resource named '/icons/star.png' is used.
    
    See also RatingEditor.
    '''
    #TODO: Create RatingEditor and link here
    def __init__(self, parent=None, star=None):
        super(RatingDelegate, self).__init__(parent)
        
        if star is None:
            self._star = QImage(':/icons/star.png')
        elif not isinstance(star, QImage):
            raise TypeError('Star Image must be a descendant of QImage')
        else:
            self._star = star
            
    def paint(self, p, option, index):
        p.save()
        
        self.drawBackground(p, option, index)
        rating = index.data()
        width = self._star.width()
        
        y = (option.rect.height() - self._star.height()) / 2 
        p.translate(option.rect.left(), option.rect.top())
        
        for i in range(0, 5):
            if rating >= (i+1):
                p.drawImage(i*(width + 1), y, self._star)
        
        p.restore()
    
    def sizeHint(self, option, index):
        return QSize((self._star.width()+2) * 5, self._star.height()+2)
        
    def setStarImage(self, star):
        'Set the Star Image'
        if not isinstance(star, QImage):
            raise TypeError('Star Image must be a descendant of QImage')
        self._star = star
        
    def starImage(self):
        return self._star
    
class UnitsDelegate(NoFocusDelegate):
    '''
    Units Delegate
    
    Delegate base class for formatting units.  The constructor expects the 
    quantity (e.g. 'depth' or 'temperature') and the default unit.
    '''
    def __init__(self, quantity, default=None, showAbbr=True, parent=None):
        super(UnitsDelegate, self).__init__(parent)
        
        self._quantity = quantity
        self._default = default
        self._showAbbr = showAbbr
        
        if not quantity in quantities():
            raise KeyError('Unknown Unit Quantity %s' % quantity)
            
    def displayText(self, value, locale):
        _units = read_setting('%s_units' % self._quantity)
        
        if _units is None:
            _units = self._default
        
        _abbr = abbr(self._quantity, _units)
        _conv = conversion(self._quantity, _units)
        
        if _units is None or _abbr is None or _conv[1] is None:
            return '%.1f' % value
        elif self._showAbbr:
            return '%.1f %s' % (_conv[1](value), _abbr)
        else:
            return '%.1f' % _conv[1](value)
        
class DepthDelegate(UnitsDelegate):
    '''
    Depth Delegate
    
    Delegate which formats a depth value according to the desired depth units
    stored in settings.
    '''
    def __init__(self, parent=None):
        super(DepthDelegate, self).__init__('depth', 'meters', False, parent)

class TemperatureDelegate(UnitsDelegate):
    '''
    Temperature Delegate
    
    Delegate which formats a temperature value according to the desired depth units
    stored in settings.
    '''
    def __init__(self, parent=None):
        super(TemperatureDelegate, self).__init__('temperature', 'celsius', False, parent)