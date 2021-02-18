# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'MORE_ImageSelector_ui_001.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets, QtGui
import os, sys
import numpy as np
import dclab
from scipy import ndimage
import traceback

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

VERSION = "0.1.0" #Python 3.5.6 Version
print("YouLabel Version: "+VERSION)

if sys.platform=="darwin":
    icon_suff = ".icns"
else:
    icon_suff = ".ico"


def MyExceptionHook(etype, value, trace):
    """
    Handler for all unhandled exceptions.
 
    :param `etype`: the exception type (`SyntaxError`, `ZeroDivisionError`, etc...);
    :type `etype`: `Exception`
    :param string `value`: the exception error message;
    :param string `trace`: the traceback header, if any (otherwise, it prints the
     standard Python header: ``Traceback (most recent call last)``.
    """
    tmp = traceback.format_exception(etype, value, trace)
    exception = "".join(tmp)
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Information)       
    msg.setText(exception)
    msg.setWindowTitle("Error")
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg.exec_()
    return


def write_rtdc(fname,rtdc_datasets,Indices):
    """
    fname - path+filename of file to be created
    rtdc_datasets - list paths to rtdc data-data-sets
    X_valid - list containing numpy arrays. Each array contains cropped images of individual measurements corresponding to each rtdc_ds
    Indices - list containing numpy arrays. Each array contais index values which refer to the index of the cell in the original rtdc_ds
    """
    #Check if a file with name fname already exists:
    if os.path.isfile(fname):
        os.remove(fname) #delete it

    index_new = np.array(range(1,np.sum(np.array([len(I) for I in Indices]))+1)) #New index. Will replace the existing index in order to support viewing imges in shapeout
    
    Features,Trace_lengths,Mask_dims_x,Mask_dims_y = [],[],[],[]
    for i in range(len(rtdc_datasets)):
        try:
            rtdc_ds = dclab.rtdc_dataset.RTDC_HDF5(rtdc_datasets[i])
        except:
            rtdc_ds = dclab.rtdc_dataset.RTDC_HDF5(rtdc_datasets[i])
        features = rtdc_ds._events.keys()#all features
        Features.append(features)

        #The lengths of the fluorescence traces have to be equal, otherwise those traces also have to be dropped
        if "trace" in features:
            trace_lengths = [(rtdc_ds["trace"][tr][0]).size for tr in rtdc_ds["trace"].keys()]
            Trace_lengths.append(trace_lengths)
        if "mask" in features:
            mask_dim = (rtdc_ds["mask"][0]).shape
            Mask_dims_x.append(mask_dim[0])
            Mask_dims_y.append(mask_dim[1])
 
    #Find common features in all .rtdc sets:
    def commonElements(arr): 
        # initialize result with first array as a set 
        result = set(arr[0]) 
        for currSet in arr[1:]: 
            result.intersection_update(currSet) 
        return list(result)     
    features = commonElements(Features)

    if "trace" in features:
        Trace_lengths = np.concatenate(Trace_lengths)
        trace_lengths = np.unique(np.array(Trace_lengths))            
        if len(trace_lengths)>1:
            ind = np.where(np.array(features)!="trace")[0]
            features = list(np.array(features)[ind])
            print("Dropped traces becasue of unequal lenghts")

    if "mask" in features:
        mask_dim_x = np.unique(np.array(Mask_dims_x))            
        if len(mask_dim_x)>1:
            ind = np.where(np.array(features)!="mask")[0]
            features = list(np.array(features)[ind])
            print("Dropped mask becasue of unequal image sizes")

    if "mask" in features:
        mask_dim_y = np.unique(np.array(Mask_dims_y))            
        if len(mask_dim_y)>1:
            ind = np.where(np.array(features)!="mask")[0]
            features = list(np.array(features)[ind])
            print("Dropped mask becasue of unequal image sizes")
        
    for i in range(len(rtdc_datasets)):
        try:
            rtdc_ds = dclab.rtdc_dataset.RTDC_HDF5(rtdc_datasets[i])
        except:
            rtdc_ds = dclab.rtdc_dataset.RTDC_HDF5(rtdc_datasets[i])

        indices = Indices[i]
        index_new_ = index_new[0:len(indices)]
        index_new = np.delete(index_new,range(len(indices)))
        #get metadata of the dataset
        meta = {}
        # only export configuration meta data (no user-defined config)
        for sec in dclab.definitions.CFG_METADATA:
            if sec in ["fmt_tdms"]:
                # ignored sections
                continue
            if sec in rtdc_ds.config:
                meta[sec] = rtdc_ds.config[sec].copy()
                
        #Adjust the meta for the nr. of stored cells
        meta["experiment"]["event count"] = np.sum(np.array([len(indi) for indi in Indices])) 
        
        #features = rtdc_ds._events.keys() #Get the names of the online features
        compression = 'gzip'    
        
        with dclab.rtdc_dataset.write_hdf5.write(path_or_h5file=fname,meta=meta, mode="append") as h5obj:
            # write each feature individually
            for feat in features:
                # event-wise, because
                # - tdms-based datasets don't allow indexing with numpy
                # - there might be memory issues
                if feat == "contour":
                    cont_list = [rtdc_ds["contour"][ii] for ii in indices]
                    dclab.rtdc_dataset.write_hdf5.write(h5obj,
                          data={"contour": cont_list},
                          mode="append",
                          compression=compression)
                elif feat == "index":
                    dclab.rtdc_dataset.write_hdf5.write(h5obj,
                          data={"index": index_new_},
                          mode="append",
                          compression=compression)
                elif feat in ["mask", "image"]:
                    # store image stacks (reduced file size and save time)
                    m = 64
                    if feat=='mask':
                        im0 = rtdc_ds[feat][0]
                    if feat=="image":
                        im0 = rtdc_ds[feat][0]
                    imstack = np.zeros((m, im0.shape[0], im0.shape[1]),
                                       dtype=im0.dtype)
                    jj = 0
                    if feat=='mask':
                        image_list = [rtdc_ds[feat][ii] for ii in indices]
                    elif feat=='image':
                        image_list = [rtdc_ds[feat][ii] for ii in indices]
                    for ii in range(len(image_list)):
                        dat = image_list[ii]
                        #dat = rtdc_ds[feat][ii]
                        imstack[jj] = dat
                        if (jj + 1) % m == 0:
                            jj = 0
                            dclab.rtdc_dataset.write_hdf5.write(h5obj,
                                  data={feat: imstack},
                                  mode="append",
                                  compression=compression)
                        else:
                            jj += 1
                    # write rest
                    if jj:
                        dclab.rtdc_dataset.write_hdf5.write(h5obj,
                              data={feat: imstack[:jj, :, :]},
                              mode="append",
                              compression=compression)
                elif feat == "trace":
                    for tr in rtdc_ds["trace"].keys():
                        tr0 = rtdc_ds["trace"][tr][0]
                        trdat = np.zeros((len(indices), tr0.size), dtype=tr0.dtype)
                        jj = 0
                        trace_list = [rtdc_ds["trace"][tr][ii] for ii in indices]
                        for ii in range(len(trace_list)):
                            trdat[jj] = trace_list[ii]
                            jj += 1
                        dclab.rtdc_dataset.write_hdf5.write(h5obj,
                              data={"trace": {tr: trdat}},
                              mode="append",
                              compression=compression)
                
                else:
                    dclab.rtdc_dataset.write_hdf5.write(h5obj,
                          data={feat: rtdc_ds[feat][indices]},mode="append")

            if "index" not in feat:
                dclab.rtdc_dataset.write_hdf5.write(h5obj,
                      data={"index": np.array(range(len(indices)))+1}, #ShapeOut likes to start with index=1
                      mode="append",
                      compression=compression)

                
            h5obj.close()


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

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(773, 652)
        sys.excepthook = MyExceptionHook

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName("tabWidget")
        self.LoadFiles = QtWidgets.QWidget()
        self.LoadFiles.setObjectName("LoadFiles")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.LoadFiles)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.tableWidget_loadFiles = MyTable(0,9,self.LoadFiles)
        self.tableWidget_loadFiles.setObjectName("tableWidget_loadFiles")
        self.gridLayout_2.addWidget(self.tableWidget_loadFiles, 0, 0, 1, 1)
        self.tabWidget.addTab(self.LoadFiles, "")
        self.tab_work = QtWidgets.QWidget()
        self.tab_work.setObjectName("tab_work")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.tab_work)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.comboBox_selectFile = QtWidgets.QComboBox(self.tab_work)
        self.comboBox_selectFile.setObjectName("comboBox_selectFile")
        self.horizontalLayout.addWidget(self.comboBox_selectFile)
        self.pushButton_start = QtWidgets.QPushButton(self.tab_work)
        self.pushButton_start.setMinimumSize(QtCore.QSize(75, 28))
        self.pushButton_start.setMaximumSize(QtCore.QSize(75, 28))
        self.pushButton_start.setObjectName("pushButton_start")
        self.horizontalLayout.addWidget(self.pushButton_start)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.splitter = QtWidgets.QSplitter(self.tab_work)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.label_showFullImage = QtWidgets.QLabel(self.splitter)
        self.label_showFullImage.setMinimumSize(QtCore.QSize(462, 131))
        self.label_showFullImage.setMaximumSize(QtCore.QSize(462, 131))
        self.label_showFullImage.setObjectName("label_showFullImage")
        self.label_showCroppedImage = QtWidgets.QLabel(self.splitter)
        self.label_showCroppedImage.setMinimumSize(QtCore.QSize(253, 131))
        self.label_showCroppedImage.setMaximumSize(QtCore.QSize(253, 131))
        self.label_showCroppedImage.setObjectName("label_showCroppedImage")
        self.verticalLayout.addWidget(self.splitter)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.horizontalSlider_index = QtWidgets.QSlider(self.tab_work)
        self.horizontalSlider_index.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_index.setObjectName("horizontalSlider_index")
        self.horizontalLayout_4.addWidget(self.horizontalSlider_index)
        self.spinBox_index = QtWidgets.QSpinBox(self.tab_work)
        self.spinBox_index.setMinimumSize(QtCore.QSize(91, 22))
        self.spinBox_index.setMaximumSize(QtCore.QSize(91, 22))
        self.spinBox_index.setObjectName("spinBox_index")
        self.horizontalLayout_4.addWidget(self.spinBox_index)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.pushButton_true = QtWidgets.QPushButton(self.tab_work)
        self.pushButton_true.setMinimumSize(QtCore.QSize(151, 28))
        self.pushButton_true.setMaximumSize(QtCore.QSize(151, 28))
        self.pushButton_true.setObjectName("pushButton_true")
        self.horizontalLayout_3.addWidget(self.pushButton_true)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.radioButton_true = QtWidgets.QRadioButton(self.tab_work)
        self.radioButton_true.setMinimumSize(QtCore.QSize(21, 20))
        self.radioButton_true.setMaximumSize(QtCore.QSize(21, 20))
        self.radioButton_true.setText("")
        self.radioButton_true.setObjectName("radioButton_true")
        self.horizontalLayout_2.addWidget(self.radioButton_true)
        self.radioButton_false = QtWidgets.QRadioButton(self.tab_work)
        self.radioButton_false.setMinimumSize(QtCore.QSize(21, 20))
        self.radioButton_false.setMaximumSize(QtCore.QSize(21, 20))
        self.radioButton_false.setText("")
        self.radioButton_false.setObjectName("radioButton_false")
        self.horizontalLayout_2.addWidget(self.radioButton_false)
        self.horizontalLayout_3.addLayout(self.horizontalLayout_2)
        self.pushButton_false = QtWidgets.QPushButton(self.tab_work)
        self.pushButton_false.setMinimumSize(QtCore.QSize(151, 28))
        self.pushButton_false.setMaximumSize(QtCore.QSize(151, 28))
        self.pushButton_false.setObjectName("pushButton_false")
        self.horizontalLayout_3.addWidget(self.pushButton_false)
        self.horizontalLayout_4.addLayout(self.horizontalLayout_3)
        self.verticalLayout.addLayout(self.horizontalLayout_4)
        self.gridLayout_5.addLayout(self.verticalLayout, 0, 0, 1, 2)
        self.groupBox_decisions = QtWidgets.QGroupBox(self.tab_work)
        self.groupBox_decisions.setObjectName("groupBox_decisions")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.groupBox_decisions)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.tableWidget_decisions = QtWidgets.QTableWidget(self.groupBox_decisions)
        self.tableWidget_decisions.setObjectName("tableWidget_decisions")
        self.tableWidget_decisions.setColumnCount(0)
        self.tableWidget_decisions.setRowCount(0)
        self.gridLayout_4.addWidget(self.tableWidget_decisions, 0, 0, 1, 1)
        self.gridLayout_5.addWidget(self.groupBox_decisions, 1, 0, 1, 1)
        
        self.groupBox_saving = QtWidgets.QGroupBox(self.tab_work)
        self.groupBox_saving.setObjectName("groupBox_saving")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.groupBox_saving)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.pushButton_saveTrueAs = QtWidgets.QPushButton(self.groupBox_saving)
        self.pushButton_saveTrueAs.setObjectName("pushButton_saveTrueAs")
        self.verticalLayout_2.addWidget(self.pushButton_saveTrueAs)
        self.lineEdit_TrueFname = QtWidgets.QLineEdit(self.groupBox_saving)
        self.lineEdit_TrueFname.setObjectName("lineEdit_TrueFname")
        self.verticalLayout_2.addWidget(self.lineEdit_TrueFname)
        self.gridLayout_3.addLayout(self.verticalLayout_2, 0, 0, 1, 1)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.pushButton_saveFalseAs = QtWidgets.QPushButton(self.groupBox_saving)
        self.pushButton_saveFalseAs.setObjectName("pushButton_saveFalseAs")
        self.verticalLayout_3.addWidget(self.pushButton_saveFalseAs)
        self.lineEdit_FalseFname = QtWidgets.QLineEdit(self.groupBox_saving)
        self.lineEdit_FalseFname.setObjectName("lineEdit_FalseFname")
        self.verticalLayout_3.addWidget(self.lineEdit_FalseFname)
        self.gridLayout_3.addLayout(self.verticalLayout_3, 1, 0, 1, 1)
        self.gridLayout_5.addWidget(self.groupBox_saving, 1, 1, 1, 1)
        self.tabWidget.addTab(self.tab_work, "")

        self.gridLayout.addWidget(self.tabWidget, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 773, 26))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)



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
        self.pushButton_true.clicked.connect(self.true_cell)
        self.pushButton_false.clicked.connect(self.false_cell)

        self.shortcut_next = QtGui.QShortcut(QtGui.QKeySequence("Right"), self.tabWidget)
        self.shortcut_next.activated.connect(self.next_cell)
        self.shortcut_next = QtGui.QShortcut(QtGui.QKeySequence("Left"), self.tabWidget)
        self.shortcut_next.activated.connect(self.previous_cell)

        self.horizontalSlider_index.valueChanged.connect(self.onIndexChange)
        self.spinBox_index.valueChanged.connect(self.onIndexChange)
        
        self.lineEdit_TrueFname.setText("True.rtdc")
        self.lineEdit_FalseFname.setText("False.rtdc")
        self.pushButton_saveTrueAs.clicked.connect(self.save_true_events)
        self.pushButton_saveFalseAs.clicked.connect(self.save_false_events)
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






    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.LoadFiles), _translate("MainWindow", "Load Files"))
        self.pushButton_start.setText(_translate("MainWindow", "Start"))
        self.pushButton_true.setText(_translate("MainWindow", "TRUE!"))
        self.pushButton_false.setText(_translate("MainWindow", "FALSE!"))
        self.groupBox_decisions.setTitle(_translate("MainWindow", "Decisions"))
        self.groupBox_saving.setTitle(_translate("MainWindow", "Saving"))
        self.pushButton_saveTrueAs.setText(_translate("MainWindow", "Save TRUE cells as..."))
        self.pushButton_saveFalseAs.setText(_translate("MainWindow", "Save FALSE cells as..."))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_work), _translate("MainWindow", "Work"))





    def dataDropped(self, l):
        #If there is data stored on ram tell user that RAM needs to be refreshed!
        if len(self.ram)>0:
            self.statusbar.showMessage("Newly added data is not yet in RAM but only RAM data will be used. Use ->Edit->Data to RAM now to update RAM",5000)
        #l is a list of some filenames.
        #check that those are valid files
        filenames = [os.path.exists(url) for url in l]
        ind_true = np.where(np.array(filenames)==True)[0]
        filenames = list(np.array(l)[ind_true]) #select the indices that are valid

        #check if the file can be opened and get some information
        fileinfo = []
        for i in range(len(filenames)):
            rtdc_path = filenames[i]
            try:
                #sometimes there occurs an error when opening hdf files,
                #therefore try this a second time in case of an error.
                #This is very strange, and seems like an unsufficient/dirty solution,
                #but I never saw it failing two times in a row
                try:
                    rtdc_ds = dclab.rtdc_dataset.RTDC_HDF5(rtdc_path)
                except:
                    rtdc_ds = dclab.rtdc_dataset.RTDC_HDF5(rtdc_path)
                    
                features = rtdc_ds.features
                #Make sure that there is "images", "pos_x" and "pos_y" available
                if "image" in features and "pos_x" in features and "pos_y" in features:
                    nr_images = rtdc_ds["image"].len()
                    pix = rtdc_ds.config["imaging"]["pixel size"]
                    fileinfo.append({"rtdc_ds":rtdc_ds,"rtdc_path":rtdc_path,"features":features,"nr_images":nr_images,"pix":pix})
                else:
                    missing = []
                    for feat in ["image","pos_x","pos_y"]:
                        if feat not in features:
                            missing.append(feat)    
                    msg = QtWidgets.QMessageBox()
                    msg.setIcon(QtWidgets.QMessageBox.Information)       
                    msg.setText("Essential feature(s) are missing in data-set")
                    msg.setDetailedText("Data-set: "+rtdc_path+"\nis missing "+str(missing))
                    msg.setWindowTitle("Missing essential features")
                    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
                    msg.exec_()                      
            except:
                pass
        
        #Add the stuff to the combobox on Plot/Peak Tab
        url_list = [fileinfo[iterator]["rtdc_path"] for iterator in range(len(fileinfo))]
        self.comboBox_selectFile.addItems(url_list)
        
        for rowNumber in range(len(fileinfo)):#for url in l:
            url = fileinfo[rowNumber]["rtdc_path"]
            #add to table
            rowPosition = self.tableWidget_loadFiles.rowCount()
            self.tableWidget_loadFiles.insertRow(rowPosition)
            
            columnPosition = 0
            item = QtWidgets.QTableWidgetItem(url) 
            item.setFlags( QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable )
            item.setTextAlignment(QtCore.Qt.AlignCenter) # change the alignment
            #item.setTextAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AnchorRight) # change the alignment
            self.tableWidget_loadFiles.setItem(rowPosition , columnPosition, item ) #

            columnPosition = 1
            spinb = QtWidgets.QSpinBox(self.tableWidget_loadFiles)
            self.tableWidget_loadFiles.setCellWidget(rowPosition, columnPosition, spinb)            

            for columnPosition in range(2,4):
                #for each item, also create 2 checkboxes (train/valid)
                item = QtWidgets.QTableWidgetItem()#("item {0} {1}".format(rowNumber, columnNumber))
                item.setFlags( QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled  )
                item.setCheckState(QtCore.Qt.Unchecked)
                self.tableWidget_loadFiles.setItem(rowPosition, columnPosition, item)
            
            columnPosition = 4
            #Place a button which allows to show a plot (scatter, histo...lets see)
            btn = QtWidgets.QPushButton(self.tableWidget_loadFiles)
            btn.setMinimumSize(QtCore.QSize(50, 30))
            btn.setMaximumSize(QtCore.QSize(50, 30))
            #btn.clicked.connect(self.button_hist)
            btn.setText('Plot')
            self.tableWidget_loadFiles.setCellWidget(rowPosition, columnPosition, btn)            
            self.tableWidget_loadFiles.resizeRowsToContents()

            columnPosition = 5
            #Place a combobox with the available features
            cb = QtWidgets.QComboBox(self.tableWidget_loadFiles)
            cb.addItems(fileinfo[rowNumber]["features"])
            cb.setMinimumSize(QtCore.QSize(70, 30))
            cb.setMaximumSize(QtCore.QSize(70, 30))
            
            width=cb.fontMetrics().boundingRect(max(fileinfo[rowNumber]["features"], key=len)).width()
            cb.view().setFixedWidth(width+30)             

            self.tableWidget_loadFiles.setCellWidget(rowPosition, columnPosition, cb)            

            columnPosition = 6
            #Place a combobox with the available features
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, fileinfo[rowNumber]["nr_images"])
            item.setFlags(item.flags() &~QtCore.Qt.ItemIsEnabled &~ QtCore.Qt.ItemIsSelectable )
            self.tableWidget_loadFiles.setItem(rowPosition, columnPosition, item)

            columnPosition = 7
            #Field to user-define nr. of cells/epoch
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole,100)
            self.tableWidget_loadFiles.setItem(rowPosition, columnPosition, item)

            columnPosition = 8
            #Pixel size
            item = QtWidgets.QTableWidgetItem()
            pix = fileinfo[rowNumber]["pix"]
            item.setData(QtCore.Qt.EditRole,pix)
            self.tableWidget_loadFiles.setItem(rowPosition, columnPosition, item)

    def put_image(self,ind):
        img = self.Images[ind]

        #zoom image such that longest side is 512
        factor = np.round(float(512.0/np.max(img.shape)),0)
        #img_zoom = zoom(img,factor)
        img_zoom = ndimage.zoom(img, zoom=factor,order=0) #Order 0 means nearest neighbor interplation

        img_zoom = np.ascontiguousarray(img_zoom)
        height, width = img_zoom.shape
        qi=QtGui.QImage(img_zoom.data, width, height,width, QtGui.QImage.Format_Indexed8)
        self.label_showFullImage.setPixmap(QtGui.QPixmap.fromImage(qi))
          
        #get the location of the cell
        PIX = self.rtdc_ds.config["imaging"]["pixel size"]
        
        pos_x,pos_y = self.rtdc_ds["pos_x"][ind]/PIX,self.rtdc_ds["pos_y"][ind]/PIX
        cropsize = 64
        y1 = int(round(pos_y))-cropsize/2                
        x1 = int(round(pos_x))-cropsize/2 
        y2 = y1+cropsize                
        x2 = x1+cropsize
        img_crop = img[int(y1):int(y2),int(x1):int(x2)]
        #zoom image such that the height gets the same as for non-cropped img
        factor = float(float(height)/np.max(img_crop.shape[0]))
        if np.isinf(factor):
            factor = 2.5
        #img_crop = zoom(img_crop,factor)
        img_crop = ndimage.zoom(img_crop, zoom=factor,order=0)
        img_crop = np.ascontiguousarray(img_crop)
        height, width = img_crop.shape
        img_crop = np.ascontiguousarray(img_crop)
        height, width = img_crop.shape
        qi=QtGui.QImage(img_crop.data, width, height,width, QtGui.QImage.Format_Indexed8)
        self.label_showCroppedImage.setPixmap(QtGui.QPixmap.fromImage(qi))


    def start_analysis(self):
        rtdc_path = str(self.comboBox_selectFile.currentText())
        print(rtdc_path)
        #get the rtdc_ds
        #sometimes there occurs an error when opening hdf files,
        #therefore try this a second time in case of an error.
        #This is very strange, and seems like an unsufficient/dirty solution,
        #but I never saw it failing two times in a row
        try:
            rtdc_ds = dclab.rtdc_dataset.RTDC_HDF5(rtdc_path)
        except:
            rtdc_ds = dclab.rtdc_dataset.RTDC_HDF5(rtdc_path)
        
        self.rtdc_ds = rtdc_ds
        
        #Load the first image and show on label_showFullImage and label_showCroppedImage
        nr_images = rtdc_ds["image"].len()
        self.spinBox_index.setRange(0,nr_images-1)
        self.horizontalSlider_index.setRange(0,nr_images-1)
        #Set both to zero
        self.spinBox_index.setValue(0)
        self.horizontalSlider_index.setValue(0)
        
        self.Images = rtdc_ds["image"][:]
        self.put_image(ind=0)
        
        #Empty tableWidget_decisions
        self.tableWidget_decisions.setColumnCount(0)        
        self.tableWidget_decisions.setRowCount(0) 
        
        self.tableWidget_decisions.setColumnCount(1)        
        self.tableWidget_decisions.setRowCount(nr_images)
        
        header = [str(i) for i in range(nr_images)]
        self.tableWidget_decisions.setVerticalHeaderLabels(header) 

        
        for row in range(nr_images):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, "True")
            item.setFlags(item.flags() &~QtCore.Qt.ItemIsEnabled &~ QtCore.Qt.ItemIsSelectable )
            self.tableWidget_decisions.setItem(row, 0, item)

        self.radioButton_true.setChecked(True)


        
    def onIndexChange(self,index):
        self.spinBox_index.setValue(index)
        self.horizontalSlider_index.setValue(index)
        
        #Get the current index
        index = int(self.spinBox_index.value())
        #Read from tableWidget_decisions if True or Wrong
        tr_or_wr = self.tableWidget_decisions.item(index, 0).text() 
        
        if tr_or_wr=="True":
            self.radioButton_true.setChecked(True)
        elif tr_or_wr=="False":
            self.radioButton_false.setChecked(True)
            
        #display the corresponding image
        self.put_image(ind=index)
        
        
    def true_cell(self):
        print("True")
        #Current index
        index = int(self.spinBox_index.value())
        #When true is hit, change this row in the table
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.DisplayRole, "True")
        item.setFlags(item.flags() &~QtCore.Qt.ItemIsEnabled &~ QtCore.Qt.ItemIsSelectable )
        self.tableWidget_decisions.setItem(index, 0, item)
        
        #adjust the radiobutton
        self.radioButton_true.setChecked(True)
        #if the current index is not the last index
        if index<len(self.rtdc_ds["pos_x"]):
            self.onIndexChange(index+1)
        
        
    def false_cell(self):
        print("False")
        #Current index
        index = int(self.spinBox_index.value())
        #When true is hit, change this row in the table
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.DisplayRole, "False")
        item.setFlags(item.flags() &~QtCore.Qt.ItemIsEnabled &~ QtCore.Qt.ItemIsSelectable )
        self.tableWidget_decisions.setItem(index, 0, item)
        #adjust the radiobutton
        self.radioButton_false.setChecked(True)
        if index<len(self.rtdc_ds["pos_x"]):
            self.onIndexChange(index+1)

    def next_cell(self):
        index = int(self.spinBox_index.value())
        if index<len(self.rtdc_ds["pos_x"]):
            self.onIndexChange(index+1)

    def previous_cell(self):       
        index = int(self.spinBox_index.value())
        if index<len(self.rtdc_ds["pos_x"]):
            self.onIndexChange(index-1)

    def save_true_events(self):
        #read from table, which events are true
        rows = self.tableWidget_decisions.rowCount()
        decisions = []
        for row in range(rows):
            decisions.append(str(self.tableWidget_decisions.item(row, 0).text()))
        ind = np.where(np.array(decisions)=="True")[0]        
        #what is the filename of the initial file?
        fname = str(self.comboBox_selectFile.currentText())
        rtdc_path = fname
        fname = fname.split(".rtdc")[0]
        #what is the user defined ending?
        ending = str(self.lineEdit_TrueFname.text())
        fname = fname+"_"+ending
        #write_rtdc expects lists of experiments. Here we will only have a single exp. 
        write_rtdc(fname,[rtdc_path],[ind])
        print("Saved true events")


    def save_false_events(self):
        #read from table, which events are true
        rows = self.tableWidget_decisions.rowCount()
        decisions = []
        for row in range(rows):
            decisions.append(str(self.tableWidget_decisions.item(row, 0).text()))
        ind = np.where(np.array(decisions)=="False")[0]        
        #what is the filename of the initial file?
        fname = str(self.comboBox_selectFile.currentText())
        rtdc_path = fname
        fname = fname.split(".rtdc")[0]
        #what is the user defined ending?
        ending = str(self.lineEdit_FalseFname.text())
        fname = fname+"_"+ending
        #write_rtdc expects lists of experiments. Here we will only have a single exp. 
        write_rtdc(fname,[rtdc_path],[ind])
        print("Saved false events")


dir_root = os.getcwd()
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(os.path.join(dir_root,"art","icon_main"+icon_suff)))
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

