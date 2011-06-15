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

from PySide.QtCore import Qt
from PySide.QtGui import QApplication, QComboBox
from PySide.QtGui import QStyle, QStyleOptionViewItem, QStyleOptionViewItemV4, \
    QStyledItemDelegate

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
        else:
            super(CustomDelegate, self).setEditorData(editor, index)
            
    def setModelData(self, editor, model, index):
        # http://bugreports.qt.nokia.com/browse/QTBUG-428 - combo boxes don't play nice with qdatawidget mapper
        if isinstance(editor, QComboBox):
            model.setData(index, editor.itemData(editor.currentIndex(), Qt.EditRole))
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