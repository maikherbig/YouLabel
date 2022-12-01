# -*- coding: utf-8 -*-
"""
Created on Wed Sep 15 08:39:57 2021

@author: MaikH
"""

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets, QtGui

import os, sys
import numpy as np
rand_state = np.random.RandomState(13) #to get the same random number on diff. PCs 
import traceback
import cv2
import h5py,shutil,time

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtWidgets.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig)


if sys.platform=="darwin":
    icon_suff = ".icns"
else:
    icon_suff = ".ico"

dir_root = os.path.dirname(__file__)


def myexcepthook(etype, value, trace):
    error = traceback.format_exception(etype, value, trace)
    error = "".join(error)
    message(error,msg_type="Error")
    return

def message(msg_text,msg_type="Error"):
    #There was an error!
    msg = QtWidgets.QMessageBox()
    if msg_type=="Error":
        msg.setIcon(QtWidgets.QMessageBox.Critical)       
    elif msg_type=="Information":
        msg.setIcon(QtWidgets.QMessageBox.Information)       
    elif msg_type=="Question":
        msg.setIcon(QtWidgets.QMessageBox.Question)       
    elif msg_type=="Warning":
        msg.setIcon(QtWidgets.QMessageBox.Warning)       
    msg.setText(str(msg_text))
    msg.setWindowTitle(msg_type)
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg.exec_()


#Special signal for combobox: when clicked basically (when dropped down)
class QComboBox2(QtWidgets.QComboBox):
    onDropdown = QtCore.pyqtSignal()

    def showPopup(self):
        self.onDropdown.emit()
        super(QComboBox2, self).showPopup()


class MyTable(QtWidgets.QTableWidget):
    dropped = QtCore.pyqtSignal(list)
#    clicked = QtCore.pyqtSignal()
#    dclicked = QtCore.pyqtSignal()

    def __init__(self,  rows, columns, parent):
        super(MyTable, self).__init__(rows, columns, parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        #self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.drag_item = None
        self.drag_row = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        #super(MyTable, self).dropEvent(event)
        #print(self.drag_row, self.row(self.drag_item),self.drag_item)
        self.drag_item = None
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                links.append(str(url.toLocalFile()))
            self.dropped.emit(links)

        else:
            event.ignore()       
        
    def startDrag(self, supportedActions):
        super(MyTable, self).startDrag(supportedActions)
        self.drag_item = self.currentItem()
        self.drag_row = self.row(self.drag_item)


DEFAULT_CSS = """
QRangeSlider * {
    border: 0px;
    padding: 0px;
}
QRangeSlider #Head {
    background: #222;
}
QRangeSlider #Span {
    background: #393;
}
QRangeSlider #Span:active {
    background: #282;
}
QRangeSlider #Tail {
    background: #222;
}
QRangeSlider > QSplitter::handle {
    background: #393;
}
QRangeSlider > QSplitter::handle:vertical {
    height: 4px;
}
QRangeSlider > QSplitter::handle:pressed {
    background: #ca5;
}
"""

def scale(val, src, dst):
    return int(((val - src[0]) / float(src[1]-src[0])) * (dst[1]-dst[0]) + dst[0])


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("QRangeSlider")
        Form.resize(300, 30)
        Form.setStyleSheet(DEFAULT_CSS)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName("gridLayout")
        self._splitter = QtWidgets.QSplitter(Form)
        self._splitter.setMinimumSize(QtCore.QSize(0, 0))
        self._splitter.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self._splitter.setOrientation(QtCore.Qt.Horizontal)
        self._splitter.setObjectName("splitter")
        self._head = QtWidgets.QGroupBox(self._splitter)
        self._head.setTitle("")
        self._head.setObjectName("Head")
        self._handle = QtWidgets.QGroupBox(self._splitter)
        self._handle.setTitle("")
        self._handle.setObjectName("Span")
        self._tail = QtWidgets.QGroupBox(self._splitter)
        self._tail.setTitle("")
        self._tail.setObjectName("Tail")
        self.gridLayout.addWidget(self._splitter, 0, 0, 1, 1)
        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("QRangeSlider", "QRangeSlider"))


class Element(QtWidgets.QGroupBox):
    def __init__(self, parent, main):
        super(Element, self).__init__(parent)
        self.main = main

    def setStyleSheet(self, style):
        self.parent().setStyleSheet(style)

    def textColor(self):
        return getattr(self, '__textColor', QtGui.QColor(125, 125, 125))

    def setTextColor(self, color):
        if type(color) == tuple and len(color) == 3:
            color = QtGui.QColor(color[0], color[1], color[2])
        elif type(color) == int:
            color = QtGui.QColor(color, color, color)
        setattr(self, '__textColor', color)

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        if self.main.drawValues():
            self.drawText(event, qp)
        qp.end()


class Head(Element):
    def __init__(self, parent, main):
        super(Head, self).__init__(parent, main)

    def drawText(self, event, qp):
        qp.setPen(self.textColor())
        qp.setFont(QtGui.QFont('Arial', 10))
        qp.drawText(event.rect(), QtCore.Qt.AlignLeft, str(self.main.min()))


class Tail(Element):
    def __init__(self, parent, main):
        super(Tail, self).__init__(parent, main)

    def drawText(self, event, qp):
        qp.setPen(self.textColor())
        qp.setFont(QtGui.QFont('Arial', 10))
        qp.drawText(event.rect(), QtCore.Qt.AlignRight, str(self.main.max()))


class Handle(Element):
    def __init__(self, parent, main):
        super(Handle, self).__init__(parent, main)

    def drawText(self, event, qp):
        qp.setPen(self.textColor())
        qp.setFont(QtGui.QFont('Arial', 10))
        qp.drawText(event.rect(), QtCore.Qt.AlignLeft, str(self.main.start()))
        qp.drawText(event.rect(), QtCore.Qt.AlignRight, str(self.main.end()))

    def mouseMoveEvent(self, event):
        event.accept()
        mx = event.globalX()
        _mx = getattr(self, '__mx', None)
        if not _mx:
            setattr(self, '__mx', mx)
            dx = 0
        else:
            dx = mx - _mx
        setattr(self, '__mx', mx)
        if dx == 0:
            event.ignore()
            return
        elif dx > 0:
            dx = 1
        elif dx < 0:
            dx = -1
        s = self.main.start() + dx
        e = self.main.end() + dx
        if s >= self.main.min() and e <= self.main.max():
            self.main.setRange(s, e)


class QRangeSlider(QtWidgets.QWidget, Ui_Form):
    endValueChanged = QtCore.pyqtSignal(int)
    maxValueChanged = QtCore.pyqtSignal(int)
    minValueChanged = QtCore.pyqtSignal(int)
    startValueChanged = QtCore.pyqtSignal(int)
    minValueChanged = QtCore.pyqtSignal(int)
    maxValueChanged = QtCore.pyqtSignal(int)
    startValueChanged = QtCore.pyqtSignal(int)
    endValueChanged = QtCore.pyqtSignal(int)

    _SPLIT_START = 1
    _SPLIT_END = 2

    def __init__(self, parent=None):
        super(QRangeSlider, self).__init__(parent)
        self.setupUi(self)
        self.setMouseTracking(False)
        self._splitter.splitterMoved.connect(self._handleMoveSplitter)
        self._head_layout = QtWidgets.QHBoxLayout()
        self._head_layout.setSpacing(0)
        self._head_layout.setContentsMargins(0, 0, 0, 0)
        self._head.setLayout(self._head_layout)
        self.head = Head(self._head, main=self)
        self._head_layout.addWidget(self.head)
        self._handle_layout = QtWidgets.QHBoxLayout()
        self._handle_layout.setSpacing(0)
        self._handle_layout.setContentsMargins(0, 0, 0, 0)
        self._handle.setLayout(self._handle_layout)
        self.handle = Handle(self._handle, main=self)
        self.handle.setTextColor((150, 255, 150))
        self._handle_layout.addWidget(self.handle)
        self._tail_layout = QtWidgets.QHBoxLayout()
        self._tail_layout.setSpacing(0)
        self._tail_layout.setContentsMargins(0, 0, 0, 0)
        self._tail.setLayout(self._tail_layout)
        self.tail = Tail(self._tail, main=self)
        self._tail_layout.addWidget(self.tail)
        self.setMin(0)
        self.setMax(99)
        self.setStart(0)
        self.setEnd(99)
        self.setDrawValues(True)

    def min(self):
        return getattr(self, '__min', None)

    def max(self):
        return getattr(self, '__max', None)

    def setMin(self, value):
        setattr(self, '__min', value)
        self.minValueChanged.emit(value)

    def setMax(self, value):
        setattr(self, '__max', value)
        self.maxValueChanged.emit(value)

    def start(self):
        return getattr(self, '__start', None)

    def end(self):
        return getattr(self, '__end', None)

    def _setStart(self, value):
        setattr(self, '__start', value)
        self.startValueChanged.emit(value)

    def setStart(self, value):
        v = self._valueToPos(value)
        self._splitter.splitterMoved.disconnect()
        self._splitter.moveSplitter(v, self._SPLIT_START)
        self._splitter.splitterMoved.connect(self._handleMoveSplitter)
        self._setStart(value)

    def _setEnd(self, value):
        setattr(self, '__end', value)
        self.endValueChanged.emit(value)

    def setEnd(self, value):
        v = self._valueToPos(value)
        self._splitter.splitterMoved.disconnect()
        self._splitter.moveSplitter(v, self._SPLIT_END)
        self._splitter.splitterMoved.connect(self._handleMoveSplitter)
        self._setEnd(value)

    def drawValues(self):
        return getattr(self, '__drawValues', None)

    def setDrawValues(self, draw):
        setattr(self, '__drawValues', draw)

    def getRange(self):
        return (self.start(), self.end())

    def setRange(self, start, end):
        self.setStart(start)
        self.setEnd(end)

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Left:
            s = self.start()-1
            e = self.end()-1
        elif key == QtCore.Qt.Key_Right:
            s = self.start()+1
            e = self.end()+1
        else:
            event.ignore()
            return
        event.accept()
        if s >= self.min() and e <= self.max():
            self.setRange(s, e)

    def setBackgroundStyle(self, style):
        self._tail.setStyleSheet(style)
        self._head.setStyleSheet(style)

    def setSpanStyle(self, style):
        self._handle.setStyleSheet(style)

    def _valueToPos(self, value):
        return scale(value, (self.min(), self.max()), (0, self.width()))

    def _posToValue(self, xpos):
        return scale(xpos, (0, self.width()), (self.min(), self.max()))

    def _handleMoveSplitter(self, xpos, index):
        hw = self._splitter.handleWidth()
        def _lockWidth(widget):
            width = widget.size().width()
            widget.setMinimumWidth(width)
            widget.setMaximumWidth(width)
        def _unlockWidth(widget):
            widget.setMinimumWidth(0)
            widget.setMaximumWidth(16777215)

        if index == 1:
            v = self._posToValue(xpos)
        elif index == 2:
            v = self._posToValue(xpos+hw)

        if index == self._SPLIT_START:
            _lockWidth(self._tail)
            if v >= self.end():
                return
            offset = -20
            w = xpos + offset
            self._setStart(v)
        elif index == self._SPLIT_END:
            _lockWidth(self._head)
            if v <= self.start():
                return
            offset = -40
            w = self.width() - xpos + offset
            self._setEnd(v)
        _unlockWidth(self._tail)
        _unlockWidth(self._head)
        _unlockWidth(self._handle)



# class RangeSlider3(QtWidgets.QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)

#         self.first_position = 1
#         self.second_position = 8

#         self.opt = QtWidgets.QStyleOptionSlider()
#         self.opt.minimum = 0
#         self.opt.maximum = 255

#         self.setTickPosition(QtWidgets.QSlider.TicksAbove)
#         self.setTickInterval(1)

#         self.setSizePolicy(
#             QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Slider)
#         )

#     def setRangeLimit(self, minimum: int, maximum: int):
#         self.opt.minimum = minimum
#         self.opt.maximum = maximum

#     def setRange(self, start: int, end: int):
#         self.first_position = start
#         self.second_position = end

#     def getRange(self):
#         return (self.first_position, self.second_position)

#     def setTickPosition(self, position: QtWidgets.QSlider.TickPosition):
#         self.opt.tickPosition = position

#     def setTickInterval(self, ti: int):
#         self.opt.tickInterval = ti

#     def paintEvent(self, event: QtGui.QPaintEvent):

#         painter = QtGui.QPainter(self)

#         # Draw rule
#         self.opt.initFrom(self)
#         self.opt.rect = self.rect()
#         self.opt.sliderPosition = 0
#         self.opt.subControls = QtWidgets.QStyle.SC_SliderGroove | QtWidgets.QStyle.SC_SliderTickmarks

#         #   Draw GROOVE
#         self.style().drawComplexControl(QtWidgets.QStyle.CC_Slider, self.opt, painter)

#         #  Draw INTERVAL

#         color = self.palette().color(QtGui.QPalette.Highlight)
#         color.setAlpha(160)
#         painter.setBrush(QtGui.QBrush(color))
#         painter.setPen(QtCore.Qt.NoPen)

#         self.opt.sliderPosition = self.first_position
#         x_left_handle = (
#             self.style()
#             .subControlRect(QtWidgets.QStyle.CC_Slider, self.opt, QtWidgets.QStyle.SC_SliderHandle)
#             .right()
#         )

#         self.opt.sliderPosition = self.second_position
#         x_right_handle = (
#             self.style()
#             .subControlRect(QtWidgets.QStyle.CC_Slider, self.opt, QtWidgets.QStyle.SC_SliderHandle)
#             .left()
#         )

#         groove_rect = self.style().subControlRect(
#             QtWidgets.QStyle.CC_Slider, self.opt, QtWidgets.QStyle.SC_SliderGroove
#         )

#         selection = QtCore.QRect(
#             x_left_handle,
#             groove_rect.y(),
#             x_right_handle - x_left_handle,
#             groove_rect.height(),
#         ).adjusted(-1, 1, 1, -1)

#         painter.drawRect(selection)

#         # Draw first handle

#         self.opt.subControls = QtWidgets.QStyle.SC_SliderHandle
#         self.opt.sliderPosition = self.first_position
#         self.style().drawComplexControl(QtWidgets.QStyle.CC_Slider, self.opt, painter)

#         # Draw second handle
#         self.opt.sliderPosition = self.second_position
#         self.style().drawComplexControl(QtWidgets.QStyle.CC_Slider, self.opt, painter)

#     def mousePressEvent(self, event: QtGui.QMouseEvent):

#         self.opt.sliderPosition = self.first_position
#         self._first_sc = self.style().hitTestComplexControl(
#             QtWidgets.QStyle.CC_Slider, self.opt, event.pos(), self
#         )

#         self.opt.sliderPosition = self.second_position
#         self._second_sc = self.style().hitTestComplexControl(
#             QtWidgets.QStyle.CC_Slider, self.opt, event.pos(), self
#         )

#     def mouseMoveEvent(self, event: QtGui.QMouseEvent):

#         distance = self.opt.maximum - self.opt.minimum

#         pos = self.style().sliderValueFromPosition(
#             0, distance, event.pos().x(), self.rect().width()
#         )

#         if self._first_sc == QtWidgets.QStyle.SC_SliderHandle:
#             if pos <= self.second_position:
#                 self.first_position = pos
#                 self.update()
#                 return

#         if self._second_sc == QtWidgets.QStyle.SC_SliderHandle:
#             if pos >= self.first_position:
#                 self.second_position = pos
#                 self.update()

#     def sizeHint(self):
#         """ override """
#         SliderLength = 84
#         TickSpace = 5

#         w = SliderLength
#         h = self.style().pixelMetric(QtWidgets.QStyle.PM_SliderThickness, self.opt, self)

#         if (
#             self.opt.tickPosition & QtWidgets.QSlider.TicksAbove
#             or self.opt.tickPosition & QtWidgets.QSlider.TicksBelow
#         ):
#             h += TickSpace

#         return (
#             self.style()
#             .sizeFromContents(QtWidgets.QStyle.CT_Slider, self.opt, QtCore.QSize(w, h), self)
#             .expandedTo(QtWidgets.QApplication.globalStrut())
#         )







def setup_main_ui(self):
    self.setObjectName("MainWindow")
    self.resize(696, 615)
    sys.excepthook = myexcepthook

    self.centralwidget = QtWidgets.QWidget(self)
    self.centralwidget.setObjectName("centralwidget")
    self.gridLayout_5 = QtWidgets.QGridLayout(self.centralwidget)
    self.gridLayout_5.setObjectName("gridLayout_5")
    self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
    self.tabWidget.setObjectName("tabWidget")
    self.LoadFiles = QtWidgets.QWidget()
    self.LoadFiles.setObjectName("LoadFiles")
    self.gridLayout_2 = QtWidgets.QGridLayout(self.LoadFiles)
    self.gridLayout_2.setObjectName("gridLayout_2")
    
    self.tableWidget_loadFiles = MyTable(0,9,self.LoadFiles)
    
    self.tableWidget_loadFiles.setObjectName("tableWidget_loadFiles")
    # self.tableWidget_loadFiles.setColumnCount(0)
    # self.tableWidget_loadFiles.setRowCount(0)
    self.gridLayout_2.addWidget(self.tableWidget_loadFiles, 0, 0, 1, 1)
    self.tabWidget.addTab(self.LoadFiles, "")
    self.tab_work = QtWidgets.QWidget()
    self.tab_work.setObjectName("tab_work")
    self.gridLayout = QtWidgets.QGridLayout(self.tab_work)
    self.gridLayout.setObjectName("gridLayout")
    self.splitter_4 = QtWidgets.QSplitter(self.tab_work)
    self.splitter_4.setOrientation(QtCore.Qt.Vertical)
    self.splitter_4.setObjectName("splitter_4")
    self.widget = QtWidgets.QWidget(self.splitter_4)
    self.widget.setObjectName("widget")
    self.horizontalLayout_top = QtWidgets.QHBoxLayout(self.widget)
    self.horizontalLayout_top.setContentsMargins(0, 0, 0, 0)
    self.horizontalLayout_top.setObjectName("horizontalLayout_top")
    self.comboBox_selectFile = QtWidgets.QComboBox(self.widget)
    self.comboBox_selectFile.setObjectName("comboBox_selectFile")
    self.horizontalLayout_top.addWidget(self.comboBox_selectFile)
    self.pushButton_start = QtWidgets.QPushButton(self.widget)
    self.pushButton_start.setMinimumSize(QtCore.QSize(75, 28))
    self.pushButton_start.setMaximumSize(QtCore.QSize(75, 28))
    self.pushButton_start.setObjectName("pushButton_start")
    self.horizontalLayout_top.addWidget(self.pushButton_start)
    self.groupBox_view = QtWidgets.QGroupBox(self.splitter_4)
    self.groupBox_view.setObjectName("groupBox_view")
    self.gridLayout_6 = QtWidgets.QGridLayout(self.groupBox_view)
    self.gridLayout_6.setObjectName("gridLayout_6")
    self.splitter_view = QtWidgets.QSplitter(self.groupBox_view)
    self.splitter_view.setOrientation(QtCore.Qt.Horizontal)
    self.splitter_view.setObjectName("splitter_view")
    
    self.label_showFullImage = pg.ImageView(self.splitter_view)
    # self.label_showFullImage.setMinimumSize(QtCore.QSize(0, 200))
    # self.label_showFullImage.setMaximumSize(QtCore.QSize(9999999, 200))
    self.label_showFullImage.ui.histogram.hide()
    self.label_showFullImage.ui.roiBtn.hide()
    self.label_showFullImage.ui.menuBtn.hide()

    self.label_showFullImage.setObjectName("label_showFullImage")
    self.label_showCroppedImage = pg.ImageView(self.splitter_view)
    # self.label_showCroppedImage.setMinimumSize(QtCore.QSize(0, 200))
    # self.label_showCroppedImage.setMaximumSize(QtCore.QSize(9999999, 200))
    self.label_showCroppedImage.ui.histogram.hide()
    self.label_showCroppedImage.ui.roiBtn.hide()
    self.label_showCroppedImage.ui.menuBtn.hide()
    
    self.gridLayout_6.addWidget(self.splitter_view, 0, 0, 1, 1)
    self.groupBox_belowView = QtWidgets.QGroupBox(self.splitter_4)
    self.groupBox_belowView.setTitle("")
    self.groupBox_belowView.setObjectName("groupBox_belowView")
    self.gridLayout_7 = QtWidgets.QGridLayout(self.groupBox_belowView)
    self.gridLayout_7.setObjectName("gridLayout_7")
    self.pushButton_layerOptions = QtWidgets.QPushButton(self.groupBox_belowView)
    self.pushButton_layerOptions.setObjectName("pushButton_layerOptions")
    self.gridLayout_7.addWidget(self.pushButton_layerOptions, 0, 0, 1, 1)
    self.horizontalSlider_index = QtWidgets.QSlider(self.groupBox_belowView)
    self.horizontalSlider_index.setOrientation(QtCore.Qt.Horizontal)
    self.horizontalSlider_index.setObjectName("horizontalSlider_index")
    self.gridLayout_7.addWidget(self.horizontalSlider_index, 0, 1, 1, 1)
    self.spinBox_index = QtWidgets.QSpinBox(self.groupBox_belowView)
    self.spinBox_index.setMinimumSize(QtCore.QSize(91, 22))
    self.spinBox_index.setMaximumSize(QtCore.QSize(91, 22))
    self.spinBox_index.setObjectName("spinBox_index")
    self.gridLayout_7.addWidget(self.spinBox_index, 0, 2, 1, 1)
    self.label_Class2 = QtWidgets.QLabel(self.groupBox_belowView)
    self.label_Class2.setObjectName("label_Class2")
    self.gridLayout_7.addWidget(self.label_Class2, 0, 3, 1, 1)
    self.spinBox_Class2 = QtWidgets.QSpinBox(self.groupBox_belowView)
    self.spinBox_Class2.setObjectName("spinBox_Class2")
    self.spinBox_Class2.setEnabled(False)

    self.gridLayout_7.addWidget(self.spinBox_Class2, 0, 4, 1, 1)
    self.splitter_bottom = QtWidgets.QSplitter(self.splitter_4)
    self.splitter_bottom.setOrientation(QtCore.Qt.Horizontal)
    self.splitter_bottom.setObjectName("splitter_bottom")
    self.groupBox_decisions = QtWidgets.QGroupBox(self.splitter_bottom)
    self.groupBox_decisions.setObjectName("groupBox_decisions")
    self.gridLayout_4 = QtWidgets.QGridLayout(self.groupBox_decisions)
    self.gridLayout_4.setObjectName("gridLayout_4")
    self.tableWidget_decisions = QtWidgets.QTableWidget(self.groupBox_decisions)
    self.tableWidget_decisions.setObjectName("tableWidget_decisions")
    self.tableWidget_decisions.setColumnCount(0)
    self.tableWidget_decisions.setRowCount(0)
    self.gridLayout_4.addWidget(self.tableWidget_decisions, 0, 0, 1, 1)
    self.splitter_imgProc = QtWidgets.QSplitter(self.splitter_bottom)
    self.splitter_imgProc.setOrientation(QtCore.Qt.Vertical)
    self.splitter_imgProc.setObjectName("splitter_imgProc")
    self.groupBox_imgProc = QtWidgets.QGroupBox(self.splitter_imgProc)
    self.groupBox_imgProc.setObjectName("groupBox_imgProc")
    self.gridLayout_49 = QtWidgets.QGridLayout(self.groupBox_imgProc)
    self.gridLayout_49.setObjectName("gridLayout_49")
    self.comboBox_GrayOrRGB = QtWidgets.QComboBox(self.groupBox_imgProc)
    self.comboBox_GrayOrRGB.setObjectName("comboBox_GrayOrRGB")
    self.comboBox_GrayOrRGB.addItem("")
    self.comboBox_GrayOrRGB.addItem("")

    self.gridLayout_49.addWidget(self.comboBox_GrayOrRGB, 1, 4, 1, 1)
    self.horizontalLayout_crop = QtWidgets.QHBoxLayout()
    self.horizontalLayout_crop.setObjectName("horizontalLayout_crop")
    self.label_CropIcon_2 = QtWidgets.QLabel(self.groupBox_imgProc)
    self.label_CropIcon_2.setText("")
    self.label_CropIcon_2.setPixmap(QtGui.QPixmap("C:/BIOTEC-WORK/Own ideas/56 AIDeveloper/013_AIDeveloper_0.0.8_dev1/art/Icon theme 1/cropping.png"))
    self.label_CropIcon_2.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
    self.label_CropIcon_2.setObjectName("label_CropIcon_2")
    self.horizontalLayout_crop.addWidget(self.label_CropIcon_2)
    self.label_Crop = QtWidgets.QLabel(self.groupBox_imgProc)
    self.label_Crop.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
    self.label_Crop.setObjectName("label_Crop")
    self.horizontalLayout_crop.addWidget(self.label_Crop)
    self.gridLayout_49.addLayout(self.horizontalLayout_crop, 0, 0, 1, 1)
    self.horizontalLayout_colorMode = QtWidgets.QHBoxLayout()
    self.horizontalLayout_colorMode.setObjectName("horizontalLayout_colorMode")
    self.label_colorModeIcon = QtWidgets.QLabel(self.groupBox_imgProc)
    self.label_colorModeIcon.setText("")
    self.label_colorModeIcon.setPixmap(QtGui.QPixmap("C:/BIOTEC-WORK/Own ideas/56 AIDeveloper/013_AIDeveloper_0.0.8_dev1/art/Icon theme 1/color_mode.png"))
    self.label_colorModeIcon.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
    self.label_colorModeIcon.setObjectName("label_colorModeIcon")
    self.horizontalLayout_colorMode.addWidget(self.label_colorModeIcon)
    self.label_colorMode = QtWidgets.QLabel(self.groupBox_imgProc)
    self.label_colorMode.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
    self.label_colorMode.setObjectName("label_colorMode")
    self.horizontalLayout_colorMode.addWidget(self.label_colorMode)
    self.gridLayout_49.addLayout(self.horizontalLayout_colorMode, 1, 3, 1, 1)
    self.horizontalLayout_nrEpochs = QtWidgets.QHBoxLayout()
    self.horizontalLayout_nrEpochs.setObjectName("horizontalLayout_nrEpochs")
    self.label_padIcon = QtWidgets.QLabel(self.groupBox_imgProc)
    self.label_padIcon.setText("")
    self.label_padIcon.setPixmap(QtGui.QPixmap("C:/BIOTEC-WORK/Own ideas/56 AIDeveloper/013_AIDeveloper_0.0.8_dev1/art/Icon theme 1/padding.png"))
    self.label_padIcon.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
    self.label_padIcon.setObjectName("label_padIcon")
    self.horizontalLayout_nrEpochs.addWidget(self.label_padIcon)
    self.label_paddingMode = QtWidgets.QLabel(self.groupBox_imgProc)
    self.label_paddingMode.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
    self.label_paddingMode.setObjectName("label_paddingMode")
    self.horizontalLayout_nrEpochs.addWidget(self.label_paddingMode)
    self.gridLayout_49.addLayout(self.horizontalLayout_nrEpochs, 1, 0, 1, 1)
    self.doubleSpinBox_brightness = QtWidgets.QDoubleSpinBox(self.groupBox_imgProc)
    self.doubleSpinBox_brightness.setMaximum(999.0)
    self.doubleSpinBox_brightness.setProperty("value", 1.0)
    self.doubleSpinBox_brightness.setSingleStep(0.1)
    self.doubleSpinBox_brightness.setObjectName("doubleSpinBox_brightness")
    self.gridLayout_49.addWidget(self.doubleSpinBox_brightness, 2, 4, 1, 1)

    self.comboBox_BgRemove = QtWidgets.QComboBox(self.groupBox_imgProc)
    self.comboBox_BgRemove.setMinimumSize(QtCore.QSize(200, 0))
    self.comboBox_BgRemove.addItem("")
    self.comboBox_BgRemove.addItem("")

    self.comboBox_BgRemove.setObjectName("comboBox_BgRemove")
    self.gridLayout_49.addWidget(self.comboBox_BgRemove, 0, 4, 1, 1)
    self.spinBox_cropsize = QtWidgets.QSpinBox(self.groupBox_imgProc)
    self.spinBox_cropsize.setMinimum(1)
    self.spinBox_cropsize.setMaximum(999999)
    self.spinBox_cropsize.setProperty("value", 64)
    self.spinBox_cropsize.setObjectName("spinBox_cropsize")
    self.gridLayout_49.addWidget(self.spinBox_cropsize, 0, 1, 1, 1)
    self.comboBox_paddingMode = QtWidgets.QComboBox(self.groupBox_imgProc)
    self.comboBox_paddingMode.setEnabled(True)
    self.comboBox_paddingMode.setObjectName("comboBox_paddingMode")
    self.comboBox_paddingMode.addItem("")
    self.comboBox_paddingMode.addItem("")
    self.comboBox_paddingMode.addItem("")
    self.comboBox_paddingMode.addItem("")
    self.comboBox_paddingMode.addItem("")
    self.comboBox_paddingMode.addItem("")
    self.comboBox_paddingMode.addItem("")
    self.comboBox_paddingMode.addItem("")
    self.comboBox_paddingMode.addItem("")
    self.comboBox_paddingMode.addItem("")
    self.gridLayout_49.addWidget(self.comboBox_paddingMode, 1, 1, 1, 1)
    
    

    self.horizontalLayout_brightness = QtWidgets.QHBoxLayout()
    self.horizontalLayout_brightness.setObjectName("horizontalLayout_brightness")
    self.label_brightnessIcon = QtWidgets.QLabel(self.groupBox_imgProc)
    self.label_brightnessIcon.setText("")
    self.label_brightnessIcon.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
    self.label_brightnessIcon.setObjectName("label_brightnessIcon")
    self.horizontalLayout_brightness.addWidget(self.label_brightnessIcon)
    self.label_brightness = QtWidgets.QLabel(self.groupBox_imgProc)
    self.label_brightness.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
    self.label_brightness.setObjectName("label_brightness")
    self.horizontalLayout_brightness.addWidget(self.label_brightness)
    self.gridLayout_49.addLayout(self.horizontalLayout_brightness, 2, 3, 1, 1)

    self.horizontalLayout_normalization = QtWidgets.QHBoxLayout()
    self.horizontalLayout_normalization.setObjectName("horizontalLayout_normalization")
    self.label_NormalizationIcon = QtWidgets.QLabel(self.groupBox_imgProc)
    self.label_NormalizationIcon.setText("")
    self.label_NormalizationIcon.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
    self.label_NormalizationIcon.setObjectName("label_NormalizationIcon")
    self.horizontalLayout_normalization.addWidget(self.label_NormalizationIcon)
    self.label_Normalization = QtWidgets.QLabel(self.groupBox_imgProc)
    self.label_Normalization.setLayoutDirection(QtCore.Qt.LeftToRight)
    self.label_Normalization.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
    self.label_Normalization.setObjectName("label_Normalization")
    self.horizontalLayout_normalization.addWidget(self.label_Normalization)
    self.gridLayout_49.addLayout(self.horizontalLayout_normalization, 0, 3, 1, 1)
    self.groupBox_saving = QtWidgets.QGroupBox(self.splitter_imgProc)
    self.groupBox_saving.setObjectName("groupBox_saving")
    self.gridLayout_3 = QtWidgets.QGridLayout(self.groupBox_saving)
    self.gridLayout_3.setObjectName("gridLayout_3")
    self.label_Class = QtWidgets.QLabel(self.groupBox_saving)
    self.label_Class.setObjectName("label_Class")
    self.gridLayout_3.addWidget(self.label_Class, 0, 0, 1, 1)
    self.label_SaveName = QtWidgets.QLabel(self.groupBox_saving)
    self.label_SaveName.setObjectName("label_SaveName")
    self.gridLayout_3.addWidget(self.label_SaveName, 0, 1, 1, 1)
    self.comboBox_Class = QComboBox2(self.groupBox_saving)
    self.comboBox_Class.setObjectName("comboBox_Class")
    self.gridLayout_3.addWidget(self.comboBox_Class, 1, 0, 1, 1)
    self.lineEdit_Savename = QtWidgets.QLineEdit(self.groupBox_saving)
    self.lineEdit_Savename.setObjectName("lineEdit_Savename")
    self.lineEdit_Savename.setEnabled(False)
    self.gridLayout_3.addWidget(self.lineEdit_Savename, 1, 1, 1, 1)
    self.pushButton_Save = QtWidgets.QPushButton(self.groupBox_saving)
    self.pushButton_Save.setObjectName("pushButton_Save")
    self.pushButton_Save.setEnabled(False)
    self.gridLayout_3.addWidget(self.pushButton_Save, 1, 2, 1, 1)
    self.gridLayout.addWidget(self.splitter_4, 0, 0, 1, 1)
    self.tabWidget.addTab(self.tab_work, "")
    self.gridLayout_5.addWidget(self.tabWidget, 0, 0, 1, 1)
    self.setCentralWidget(self.centralwidget)
    self.menubar = QtWidgets.QMenuBar(self)
    self.menubar.setGeometry(QtCore.QRect(0, 0, 696, 25))
    self.menubar.setObjectName("menubar")
    self.setMenuBar(self.menubar)
    self.statusbar = QtWidgets.QStatusBar(self)
    self.statusbar.setObjectName("statusbar")
    self.setStatusBar(self.statusbar)

    self.retranslateUi()
    self.tabWidget.setCurrentIndex(0)
    QtCore.QMetaObject.connectSlotsByName(self)



    ##########################Manual changes###############################
    #######################################################################
    self.tableWidget_loadFiles.setObjectName(_fromUtf8("tableWidget_loadFiles"))
    header_labels = ["File", "Index" ,"T", "V", "Show","Features","Cells total","Cells/Epoch","PIX"]
    self.tableWidget_loadFiles.setHorizontalHeaderLabels(header_labels) 
    header = self.tableWidget_loadFiles.horizontalHeader()
    for i in [1,2,3,4,5,6,7,8]:#range(len(header_labels)):
        header.setResizeMode(i, QtWidgets.QHeaderView.ResizeToContents)        
    self.tableWidget_loadFiles.setAcceptDrops(True)
    self.tableWidget_loadFiles.setDragEnabled(True)
    self.tableWidget_loadFiles.dropped.connect(self.dataDropped)
    self.tableWidget_loadFiles.resizeRowsToContents()

    self.pushButton_start.clicked.connect(self.start_analysis)
    self.shortcut_true = QtGui.QShortcut(QtGui.QKeySequence("T"), self.tabWidget)
    self.shortcut_true.activated.connect(self.true_cell)
    self.shortcut_false = QtGui.QShortcut(QtGui.QKeySequence("F"), self.tabWidget)
    self.shortcut_false.activated.connect(self.false_cell)
    self.pushButton_layerOptions.clicked.connect(self.show_layercontrols)
    #self.shortcut_number = QtGui.QShortcut(QtGui.QKeySequence("1"), self.tabWidget)
    # self.shortcut_number.activated.connect(self.number_pressed)
    
    # self.shortcut_channel = QtGui.QShortcut(QtGui.QKeySequence("C"), self.tabWidget)

    self.comboBox_Class.onDropdown.connect(self.fill_class_combobox)
    
    self.shortcut_next = QtGui.QShortcut(QtGui.QKeySequence("Right"), self.tabWidget)
    self.shortcut_next.activated.connect(self.next_cell)
    self.shortcut_next = QtGui.QShortcut(QtGui.QKeySequence("Left"), self.tabWidget)
    self.shortcut_next.activated.connect(self.previous_cell)

    self.horizontalSlider_index.valueChanged.connect(self.onIndexChange)
    self.spinBox_index.valueChanged.connect(self.onIndexChange)
    self.spinBox_cropsize.valueChanged.connect(lambda ind: self.put_image(self.spinBox_index.value()))
    self.doubleSpinBox_brightness.valueChanged.connect(lambda ind: self.put_image(self.spinBox_index.value()))
    self.comboBox_paddingMode.currentIndexChanged.connect(lambda ind: self.put_image(self.spinBox_index.value()))

    self.comboBox_BgRemove.currentIndexChanged.connect(lambda ind: self.put_image(self.spinBox_index.value()))
    self.comboBox_GrayOrRGB.currentIndexChanged.connect(lambda ind: self.put_image(self.spinBox_index.value()))
    
    self.lineEdit_Savename.setText("_addon.rtdc")
    self.pushButton_Save.clicked.connect(self.save_events)

    self.comboBox_selectFile.currentIndexChanged.connect(self.start_analysis)
    ############################Variables##################################
    #######################################################################
    #Initilaize some variables which are lateron filled in the program
    self.colors = 10*["g","m","b","c"]
    #self.colors = QtGui.QColor.colorNames() #returns a list of all available colors
    self.colors2 = 10*['blue','red','magenta','cyan','green','black','grey','orange','yellow','cornflowerblue','chocolate','lime','tomato','gold','purple']    #Some colors which are later used for different subpopulations
    self.ram = dict() #Variable to store data if Option "Data to RAM is enabled"
    #######################################################################
    #######################################################################


    #######################################################################
    ###############################Icons###################################
    #######################################################################
    self.label_CropIcon_2.setPixmap(QtGui.QPixmap(os.path.join(dir_root,"art","cropping.png")))
    self.label_CropIcon_2.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)

    self.label_colorModeIcon.setPixmap(QtGui.QPixmap(os.path.join(dir_root,"art","color_mode.png")))
    self.label_colorModeIcon.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)

    self.label_colorMode.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)

    self.label_padIcon.setPixmap(QtGui.QPixmap(os.path.join(dir_root,"art","padding.png")))
    self.label_padIcon.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
    
    self.label_paddingMode.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)

    self.label_brightnessIcon.setPixmap(QtGui.QPixmap(os.path.join(dir_root,"art","brightness_mult.png")))

    self.pushButton_Save.setIcon(QtGui.QIcon(os.path.join(dir_root,"art","save.png")))


def retranslate_main_ui(self,VERSION):
    _translate = QtCore.QCoreApplication.translate
    self.setWindowTitle(_translate("MainWindow", "YouLabel_v"+VERSION))
    self.tabWidget.setTabText(self.tabWidget.indexOf(self.LoadFiles), _translate("MainWindow", "Load Files"))
    self.pushButton_start.setText(_translate("MainWindow", "Start"))
    self.label_Class2.setText(_translate("MainWindow", "Class"))
    self.horizontalSlider_index.setToolTip(_translate("MainWindow", "Shortcut: Left/Right arrow"))
    self.groupBox_view.setTitle(_translate("MainWindow", "View"))
    self.pushButton_layerOptions.setText(_translate("MainWindow", "LayerOptions"))
    self.label_Class2.setText(_translate("MainWindow", "Class"))

    self.groupBox_decisions.setTitle(_translate("MainWindow", "Decisions"))
    self.groupBox_imgProc.setTitle(_translate("MainWindow", "Image processing"))
    self.label_Crop.setToolTip(_translate("MainWindow", "Define size of the cropped image (right)."))
    self.label_Crop.setText(_translate("MainWindow", "Cropping size"))
    self.label_colorMode.setText(_translate("MainWindow", "Color Mode"))
    self.label_paddingMode.setText(_translate("MainWindow", "Padding mode"))
    self.comboBox_paddingMode.setToolTip(_translate("MainWindow", "By default, the padding mode is \"constant\", which means that zeros are padded.\n"
"\"edge\": Pads with the edge values of array.\n"
"\"linear_ramp\": Pads with the linear ramp between end_value and the array edge value.\n"
"\"maximum\": Pads with the maximum value of all or part of the vector along each axis.\n"
"\"mean\": Pads with the mean value of all or part of the vector along each axis.\n"
"\"median\": Pads with the median value of all or part of the vector along each axis.\n"
"\"minimum\": Pads with the minimum value of all or part of the vector along each axis.\n"
"\"reflect\": Pads with the reflection of the vector mirrored on the first and last values of the vector along each axis.\n"
"\"symmetric\": Pads with the reflection of the vector mirrored along the edge of the array.\n"
"\"wrap\": Pads with the wrap of the vector along the axis. The first values are used to pad the end and the end values are used to pad the beginning.\n"
"Text copied from https://docs.scipy.org/doc/numpy/reference/generated/numpy.pad.html"))
    self.comboBox_paddingMode.setItemText(0, _translate("MainWindow", "constant"))
    self.comboBox_paddingMode.setItemText(1, _translate("MainWindow", "edge"))
    self.comboBox_paddingMode.setItemText(2, _translate("MainWindow", "reflect"))
    self.comboBox_paddingMode.setItemText(3, _translate("MainWindow", "symmetric"))
    self.comboBox_paddingMode.setItemText(4, _translate("MainWindow", "wrap"))
    self.comboBox_paddingMode.setItemText(5, _translate("MainWindow", "alternate"))
    self.label_brightness.setText(_translate("MainWindow", "Brightness"))
    
    self.comboBox_GrayOrRGB.setItemText(0, _translate("MainWindow", "Grayscale"))
    self.comboBox_GrayOrRGB.setItemText(1, _translate("MainWindow", "RGB"))

    self.comboBox_BgRemove.setItemText(0, _translate("MainWindow", "None"))
    self.comboBox_BgRemove.setItemText(1, _translate("MainWindow", "vstripes_removal"))
   
    self.label_Normalization.setToolTip(_translate("MainWindow", "Define, if a particular backgound removal algorithm should be applied (chnages only the appearance of the displayed image. Has no effect during saving (original images are saved)"))
    self.label_Normalization.setText(_translate("MainWindow", "Background removal"))
    self.groupBox_saving.setTitle(_translate("MainWindow", "Saving"))
    self.pushButton_Save.setText(_translate("MainWindow", "Save"))
    self.pushButton_Save.setToolTip(_translate("MainWindow", "File is saved into same directory as original file."))
    self.label_Class.setText(_translate("MainWindow", "Class"))
    self.label_SaveName.setText(_translate("MainWindow", "Savename"))

    self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_work), _translate("MainWindow", "Label Images"))



class Ui_LayerControl(object):
    def setupUi(self, Form,keys_image):
        Form.setObjectName("Form")
        Form.resize(481, 208)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.scrollArea_layerControls = QtWidgets.QScrollArea(Form)
        self.scrollArea_layerControls.setWidgetResizable(True)
        self.scrollArea_layerControls.setObjectName("scrollArea_layerControls")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 459, 186))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.groupBox_layerControl = QtWidgets.QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_layerControl.setObjectName("groupBox_layerControl")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox_layerControl)
        self.gridLayout_2.setObjectName("gridLayout_2")

        self.label_chName = QtWidgets.QLabel(self.groupBox_layerControl)
        self.label_chName.setAlignment(QtCore.Qt.AlignCenter)
        self.label_chName.setObjectName("label_chName")
        self.gridLayout_2.addWidget(self.label_chName, 0, 0, 1, 1)
        self.label_auto = QtWidgets.QLabel(self.groupBox_layerControl)
        self.label_auto.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.label_auto.setAlignment(QtCore.Qt.AlignCenter)
        self.label_auto.setObjectName("label_auto")
        self.gridLayout_2.addWidget(self.label_auto, 0, 5, 1, 1)
        self.label_show = QtWidgets.QLabel(self.groupBox_layerControl)
        self.label_show.setAlignment(QtCore.Qt.AlignCenter)
        self.label_show.setObjectName("label_show")
        self.gridLayout_2.addWidget(self.label_show, 0, 1, 1, 1)
        self.label_range = QtWidgets.QLabel(self.groupBox_layerControl)
        self.label_range.setAlignment(QtCore.Qt.AlignCenter)
        self.label_range.setObjectName("label_range")
        self.gridLayout_2.addWidget(self.label_range, 0, 3, 1, 1)
        self.label_min = QtWidgets.QLabel(self.groupBox_layerControl)
        self.label_min.setAlignment(QtCore.Qt.AlignCenter)
        self.label_min.setObjectName("label_min")
        self.gridLayout_2.addWidget(self.label_min, 0, 2, 1, 1)
        self.label_max = QtWidgets.QLabel(self.groupBox_layerControl)
        self.label_max.setAlignment(QtCore.Qt.AlignCenter)
        self.label_max.setObjectName("label_max")
        self.gridLayout_2.addWidget(self.label_max, 0, 4, 1, 1)
        self.label_cmap = QtWidgets.QLabel(self.groupBox_layerControl)
        self.label_cmap.setAlignment(QtCore.Qt.AlignCenter)
        self.label_cmap.setObjectName("label_cmap_ch0")
        self.gridLayout_2.addWidget(self.label_cmap, 0, 6, 1, 1)

        self.label_layername_chX = []
        self.checkBox_show_chX = []
        self.horizontalSlider_chX = []
        self.checkBox_auto_chX = []
        self.comboBox_cmap_chX = []
        self.spinBox_minChX = []
        self.spinBox_maxChX = []


        for ith in range(len(keys_image)):
            key_image = keys_image[ith]

            self.label_layername_chX.append( QtWidgets.QLabel(self.groupBox_layerControl) )
            self.label_layername_chX[ith].setText(key_image)
            self.label_layername_chX[ith].setObjectName("label_layername_ch"+str(ith))
            self.gridLayout_2.addWidget(self.label_layername_chX[ith], ith+1, 0, 1, 1)
    
            self.checkBox_show_chX.append( QtWidgets.QCheckBox(self.groupBox_layerControl) )
            self.checkBox_show_chX[ith].setLayoutDirection(QtCore.Qt.RightToLeft)
            self.checkBox_show_chX[ith].setText("")
            if ith==0:
                self.checkBox_show_chX[ith].setChecked(True)
            self.checkBox_show_chX[ith].setObjectName("checkBox_show_ch"+str(ith))
            self.gridLayout_2.addWidget(self.checkBox_show_chX[ith], ith+1, 1, 1, 1)
    
            self.horizontalSlider_chX.append( QRangeSlider(self.groupBox_layerControl) )
            self.horizontalSlider_chX[ith].setMin(0)
            self.horizontalSlider_chX[ith].setMax(255)
            self.horizontalSlider_chX[ith].setRange(0, 255)
            # self.horizontalSlider_chX[ith].setRangeLimit(0, 255)
            self.horizontalSlider_chX[ith].setObjectName("horizontalSlider_ch"+str(ith))
            self.gridLayout_2.addWidget(self.horizontalSlider_chX[ith], ith+1, 3, 1, 1)
            
            self.checkBox_auto_chX.append( QtWidgets.QCheckBox(self.groupBox_layerControl) )
            self.checkBox_auto_chX[ith].setLayoutDirection(QtCore.Qt.LeftToRight)
            self.checkBox_auto_chX[ith].setText("")
            self.checkBox_auto_chX[ith].setEnabled(False)
            self.checkBox_auto_chX[ith].setObjectName("checkBox_auto_ch"+str(ith))
            self.gridLayout_2.addWidget(self.checkBox_auto_chX[ith], ith+1, 5, 1, 1)
    
            self.comboBox_cmap_chX.append( QtWidgets.QComboBox(self.groupBox_layerControl) )
            self.comboBox_cmap_chX[ith].setObjectName("comboBox_cmap_ch"+str(ith))
            self.comboBox_cmap_chX[ith].addItems(["Red","Green","Blue"])
            self.comboBox_cmap_chX[ith].setCurrentIndex(ith)
            self.gridLayout_2.addWidget(self.comboBox_cmap_chX[ith], ith+1, 6, 1, 1)
                    
            self.spinBox_minChX.append( QtWidgets.QSpinBox(self.groupBox_layerControl) )
            self.spinBox_minChX[ith].setMinimum(0)
            self.spinBox_minChX[ith].setMaximum(255)
            self.spinBox_minChX[ith].setValue(0)
            self.spinBox_minChX[ith].setObjectName("spinBox_minCh"+str(ith))
            self.gridLayout_2.addWidget(self.spinBox_minChX[ith], ith+1, 2, 1, 1)            
            
            self.spinBox_maxChX.append( QtWidgets.QSpinBox(self.groupBox_layerControl) )
            self.spinBox_maxChX[ith].setObjectName("spinBox_maxCh"+str(ith))
            self.spinBox_maxChX[ith].setMinimum(0)
            self.spinBox_maxChX[ith].setMaximum(255)
            self.spinBox_maxChX[ith].setValue(255)
            self.gridLayout_2.addWidget(self.spinBox_maxChX[ith], ith+1, 4, 1, 1)



        self.gridLayout_3.addWidget(self.groupBox_layerControl, 0, 0, 1, 3)
        
        spacerItem = QtWidgets.QSpacerItem(254, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_3.addItem(spacerItem, 1, 0, 1, 1)
        self.pushButton_reset = QtWidgets.QPushButton(self.scrollAreaWidgetContents)
        self.pushButton_reset.setObjectName("pushButton_reset")
        self.gridLayout_3.addWidget(self.pushButton_reset, 1, 1, 1, 1)
        self.pushButton_close = QtWidgets.QPushButton(self.scrollAreaWidgetContents)
        self.pushButton_close.setObjectName("pushButton_close")
        self.pushButton_close.setEnabled(False)        
        self.gridLayout_3.addWidget(self.pushButton_close, 1, 2, 1, 1)
        self.scrollArea_layerControls.setWidget(self.scrollAreaWidgetContents)
        self.gridLayout.addWidget(self.scrollArea_layerControls, 0, 1, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)


        ################CONNECTIONS#################
        self.pushButton_reset.clicked.connect(self.connect_slider_reset)
        
        
        for iterator in range(len(self.spinBox_minChX)):
            sb = self.spinBox_minChX[iterator]
            sb.valueChanged.connect(lambda _, b=iterator: self.connect_sb_to_slider(ith=b))

            sb = self.spinBox_maxChX[iterator]
            sb.valueChanged.connect(lambda _, b=iterator: self.connect_sb_to_slider(ith=b))
        
            slider = self.horizontalSlider_chX[iterator]
            slider.startValueChanged.connect(lambda _, b=iterator: self.connect_slider_to_sb(ith=b))
            slider.endValueChanged.connect(lambda _, b=iterator: self.connect_slider_to_sb(ith=b))



    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "LayerOptions"))
        self.groupBox_layerControl.setTitle(_translate("Form", ""))
        self.label_chName.setText(_translate("Form", "Ch.Name"))
        self.label_show.setText(_translate("Form", "Show"))
        self.label_min.setText(_translate("Form", "Min"))
        self.label_range.setText(_translate("Form", "Range"))
        self.label_max.setText(_translate("Form", "Max"))
        self.label_auto.setText(_translate("Form", "Auto"))
        self.label_cmap.setText(_translate("Form", "Colormap"))
        # self.label_layername_ch0.setText(_translate("Form", "Layer"))
        # self.label_layername_ch1.setText(_translate("Form", "Layer"))
        # self.label_layername_ch2.setText(_translate("Form", "Layer"))
        self.pushButton_reset.setText(_translate("Form", "Reset"))
        self.pushButton_close.setText(_translate("Form", "Hide"))


    def connect_sb_to_slider(self,ith):
        start = self.spinBox_minChX[ith].value()
        stop = self.spinBox_maxChX[ith].value()
        if start<=stop:
            self.horizontalSlider_chX[ith].setRange(start,stop)

    def connect_slider_reset(self):
        for ith in range(len(self.spinBox_maxChX)):
            self.horizontalSlider_chX[ith].setRange(0,255)
            self.checkBox_show_chX[ith].setChecked(False)
        self.checkBox_show_chX[0].setChecked(True)

    def connect_slider_to_sb(self,ith):
        start = self.horizontalSlider_chX[ith].start()
        stop = self.horizontalSlider_chX[ith].end()
        self.spinBox_minChX[ith].setValue(start)
        self.spinBox_maxChX[ith].setValue(stop)





