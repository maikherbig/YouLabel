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

VERSION = "0.2.0_dev2" #Python 3.7.10 Version
print("YouLabel Version: "+VERSION)

if sys.platform=="darwin":
    icon_suff = ".icns"
else:
    icon_suff = ".ico"

dir_root = os.getcwd()

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

def store_trace(h5group, data, compression):
    firstkey = sorted(list(data.keys()))[0]
    if len(data[firstkey].shape) == 1:
        # single event
        for dd in data:
            data[dd] = data[dd].reshape(1, -1)
    # create trace group
    grp = h5group.require_group("trace")

    for flt in data:
        # create traces datasets
        if flt not in grp:
            maxshape = (None, data[flt].shape[1])
            #chunks = (CHUNK_SIZE, data[flt].shape[1])
            grp.create_dataset(flt,
                               data=data[flt],
                               maxshape=maxshape,
                               fletcher32=True,
                               chunks = True,
                               compression=compression)
        else:
            dset = grp[flt]
            oldsize = dset.shape[0]
            dset.resize(oldsize + data[flt].shape[0], axis=0)
            dset[oldsize:] = data[flt]


def write_rtdc(fname,rtdc_path,indices,decisions):
    """
    fname - path+filename of file to be created
    rtdc_path - string; path to rtdc data-sets
    X_valid - numpy array containing images of individual cells
    Indices - numpy array with index values which refer to the index of the cell in the original rtdc_ds
    """
    #Check if a file with name fname already exists:
    if os.path.isfile(fname):
        print("Following file already exists and will be overwritten: "+fname)
        os.remove(fname) #delete it
    
    #copy the template file Empty.rtdc
    shutil.copy(os.path.join(dir_root,"Empty.rtdc"),fname)

    #load original .rtdc (hdf5) file
    h5_orig = h5py.File(rtdc_path, 'r')

    #load each feature contained in the .rtdc file, filter it, and append
    keys = ["label"] + list(h5_orig["events"].keys())

    #Find pixel size of original file:
    pixel_size = h5_orig.attrs["imaging:pixel size"]

    #Open target hdf5 file
    h5_targ = h5py.File(fname,'a')

    # Write data
    for key in keys:

        if key == "index":
            values = np.array(range(len(indices)))+1
            h5_targ.create_dataset("events/"+key, data=values,dtype=values.dtype)

        elif key == "index_orig":
            values = h5_orig["events"]["index"][indices]
            h5_targ.create_dataset("events/"+key, data=values,dtype=values.dtype)

        elif key == "label":
            h5_targ.create_dataset("events/"+key, data=decisions,dtype=decisions.dtype)

        elif key == "mask":
            mask = h5_orig["events"]["mask"][indices]
            mask = np.asarray(mask, dtype=np.uint8)
            if mask.max() != 255 and mask.max() != 0 and mask.min() == 0:
                mask = mask / mask.max() * 255
            maxshape = (None, mask.shape[1], mask.shape[2])
            dset = h5_targ.create_dataset("events/"+key, data=mask, dtype=np.uint8,maxshape=maxshape,fletcher32=True,chunks=True)
            dset.attrs.create('CLASS', np.string_('IMAGE'))
            dset.attrs.create('IMAGE_VERSION', np.string_('1.2'))
            dset.attrs.create('IMAGE_SUBCLASS', np.string_('IMAGE_GRAYSCALE'))

        elif "image" in key:
            images = h5_orig["events"][key][indices]
            maxshape = (None, images.shape[1], images.shape[2])
            dset = h5_targ.create_dataset("events/"+key, data=images, dtype=np.uint8,maxshape=maxshape,fletcher32=True,chunks=True)
            dset.attrs.create('CLASS', np.string_('IMAGE'))
            dset.attrs.create('IMAGE_VERSION', np.string_('1.2'))
            dset.attrs.create('IMAGE_SUBCLASS', np.string_('IMAGE_GRAYSCALE'))
        
        elif key == "contour":
            print("Omitting")
            # contours = h5_orig["events"][key]
            # contours = [contours[i][:] for i in contours.keys()]
            # contours = list(np.array(contours)[ind])
            # for ii, cc in enumerate(contours):
            #     h5_targ.create_dataset("events/contour/"+"{}".format(ii),
            #     data=cc.reshape(cc.shape[0],cc.shape[1]),
            #     fletcher32=True)
        
        elif key == "trace":
            # create events group
            events = h5_targ.require_group("events")
            store_trace(h5group=events,
                        data=h5_orig["events"]["trace"][indices],
                        compression="gzip")

        else:
            values = h5_orig["events"][key][indices]
            h5_targ.create_dataset("events/"+key, data=values,dtype=values.dtype)
    
    #Adjust metadata:
    #"experiment:event count" = Nr. of images
    h5_targ.attrs["experiment:event count"] = len(indices)
    h5_targ.attrs["experiment:sample"] = rtdc_path
    h5_targ.attrs["experiment:date"] = time.strftime("%Y-%m-%d")
    h5_targ.attrs["experiment:time"] = time.strftime("%H:%M:%S")
    h5_targ.attrs["imaging:pixel size"] = pixel_size
    h5_targ.attrs["setup:identifier"] = h5_orig.attrs["setup:identifier"]
    h5_targ.attrs["experiment:original_file"] = rtdc_path


    h5_targ.close()
    h5_orig.close()

def image_adjust_channels(images,channels_targ=1):
    """
    Check the number of channels of images.
    Transform images (if needed) to get to the desired number of channels
    
    Parameters
    ----------
    images: numpy array of dimension (nr.images,height,width) for grayscale,
    or of dimension (nr.images,height,width,channels) for RGB images

    channels_targ: int
        target number of channels
        can be one of the following:
        
        - 1: target is a grayscale image. In case RGB images are 
        provided, the luminosity formula is used to convert of RGB to 
        grayscale
        - 3: target is an RGB image. In case grayscale images are provided,
        the information of each image is copied to all three channels to 
        convert grayscale to RGB"
    
    Returns
    ----------
    images: numpy array
        images with adjusted number of channels
    """

    #images.shape is (N,H,W) for grayscale, or (N,H,W,C) for RGB images
    #(N,H,W,C) means (nr.images,height,width,channels)

    #Make sure either (N,H,W), or (N,H,W,C) is provided
    assert len(images.shape)==4 or len(images.shape)==3, "Shape of 'images' \
    is not supported: " +str(images.shape) 

    if len(images.shape)==4:#Provided images are RGB
        #Mare sure there are 1, 2, or 3 channels (RGB)
        assert images.shape[-1] in [1,2,3], "Images have "+str(images.shape[-1])+" channels. This is (currently) not supported!"

        if channels_targ==1:#User wants Grayscale -> use the luminosity formula
            images = (0.21 * images[:,:,:,:1]) + (0.72 * images[:,:,:,1:2]) + (0.07 * images[:,:,:,-1:])
            images = images[:,:,:,0] 
            images = images.astype(np.uint8)           
            print("Used luminosity formula to convert RGB to Grayscale")
            
    if len(images.shape)==3:#Provided images are Grayscale
        if channels_targ==3:#User wants RGB -> copy the information to all 3 channels
            images = np.stack((images,)*3, axis=-1)
            print("Copied information to all three channels to convert Grayscale to RGB")
    return images

def vstripes_removal(image):
    """
    Backgound in IACS shows vertical stripes
    Get this pattern using top and bottom 5 pixels
    and remove that from original image
    """
    ##Background finding & removal
    if len(image.shape)==2:
        channels=1
    elif len(image.shape)==3:
        height, width, channels = image.shape

    if channels==1:
        #get a slice of 88x5pix at top and bottom of image
        #and put both stripes in one array
        bg = np.r_[image[0:5,:],image[-5:,:]]
        #vertical mean
        bg = cv2.reduce(bg, 0, cv2.REDUCE_AVG)
        #stack to get it back to 100x88 pixel image
        bg = np.tile(bg,(100,1))
        #remove the background and return
        image = cv2.subtract(image,bg)

    else:
        for ch in range(channels):
            #get a slice of 88x5pix at top and bottom of image
            #and put both stripes in one array
            bg = np.r_[image[0:5,:,ch],image[-5:,:,ch]]
            #vertical mean
            bg = cv2.reduce(bg, 0, cv2.REDUCE_AVG)
            #stack to get it back to 100x88 pixel image
            bg = np.tile(bg,(100,1))
            #remove the background
            image[:,:,ch] = cv2.subtract(image[:,:,ch],bg)
    return image


def pad_arguments_np2cv(padding_mode):
    """
    NumPy's pad and OpenCVs copyMakeBorder can do the same thing, but the 
    function arguments are called differntly.

    This function takes numpy padding_mode argument and returns the 
    corresponsing borderType for cv2.copyMakeBorder

    Parameters
    ---------- 
    padding_mode: str; numpy padding mode
        - "constant" (default): Pads with a constant value.
        - "edge": Pads with the edge values of array.
        - "linear_ramp": Pads with the linear ramp between end_value and the array edge value.
        - "maximum": Pads with the maximum value of all or part of the vector along each axis.
        - "mean": Pads with the mean value of all or part of the vector along each axis.
        - "median": Pads with the median value of all or part of the vector along each axis.
        - "minimum": Pads with the minimum value of all or part of the vector along each axis.
        - "reflect": Pads with the reflection of the vector mirrored on the first and last values of the vector along each axis.
        - "symmetric": Pads with the reflection of the vector mirrored along the edge of the array.
        - "wrap": Pads with the wrap of the vector along the axis. The first values are used to pad the end and the end values are used to pad the beginning.

    Returns
    ----------   
    str: OpenCV borderType, or "delete" or "alternate"    
        - "cv2.BORDER_CONSTANT": iiiiii|abcdefgh|iiiiiii with some specified i 
        - "cv2.BORDER_REFLECT": fedcba|abcdefgh|hgfedcb
        - "cv2.BORDER_REFLECT_101": gfedcb|abcdefgh|gfedcba
        - "cv2.BORDER_DEFAULT": same as BORDER_REFLECT_101
        - "cv2.BORDER_REPLICATE": aaaaaa|abcdefgh|hhhhhhh
        - "cv2.BORDER_WRAP": cdefgh|abcdefgh|abcdefg
    """
    #Check if padding_mode is already an OpenCV borderType
    padmodes_cv = ["cv2.BORDER_CONSTANT","cv2.BORDER_REFLECT",
                   "cv2.BORDER_REFLECT_101","cv2.BORDER_DEFAULT",
                   "cv2.BORDER_REPLICATE","cv2.BORDER_WRAP"]
    padmodes_cv += ["delete","alternate"]
    #padmodes_cv = [a.lower() for a in padmodes_cv]
    
    #If padding_mode is already one of those, just return the identity
    if padding_mode in padmodes_cv:
        return padding_mode
    
    if "cv2" in padding_mode and "constant" in padding_mode:
        return "cv2.BORDER_CONSTANT"
    elif "cv2" in padding_mode and "replicate" in padding_mode:
        return "cv2.BORDER_REPLICATE"    
    elif "cv2" in padding_mode and "reflect_101" in padding_mode:
        return "cv2.BORDER_REFLECT_101"    
    elif "cv2" in padding_mode and "reflect" in padding_mode:
        return "cv2.BORDER_REFLECT"    
    elif "cv2" in padding_mode and "wrap" in padding_mode:
        return "cv2.BORDER_WRAP" 

    #Check that the padding_mode is actually supported by OpenCV
    supported = ["constant","edge","reflect","symmetric","wrap","delete","alternate"]
    assert padding_mode.lower() in supported, "The padding mode: '"+padding_mode+"' is not supported"
    
    #Otherwise, return the an OpenCV borderType corresponding to the numpy pad mode
    if padding_mode=="constant":
        return "cv2.BORDER_CONSTANT"
    if padding_mode=="edge":
        return "cv2.BORDER_REPLICATE"
    if padding_mode=="reflect":
        return "cv2.BORDER_REFLECT_101"
    if padding_mode=="symmetric":
        return "cv2.BORDER_REFLECT"
    if padding_mode=="wrap":
        return "cv2.BORDER_WRAP"


def image_crop_pad_cv2(images,pos_x,pos_y,pix,final_h,final_w,padding_mode="cv2.BORDER_CONSTANT"):
    """
    Function takes a list images (list of numpy arrays) an resizes them to 
    equal size by center cropping and/or padding.

    Parameters
    ----------
    images: list of images of arbitrary shape
    (nr.images,height,width,channels) 
        can be a single image or multiple images
    pos_x: float or ndarray of length N
        The x coordinate(s) of the centroid of the event(s) [um]
    pos_y: float or ndarray of length N
        The y coordinate(s) of the centroid of the event(s) [um]
        
    final_h: int
        target image height [pixels]
    
    final_w: int
        target image width [pixels]
        
    padding_mode: str; OpenCV BorderType
        Perform the following padding operation if the cell is too far at the 
        border such that the  desired image size cannot be 
        obtained without going beyond the order of the image:
                
        #the following text is copied from 
        https://docs.opencv.org/3.4/d2/de8/group__core__array.html#ga209f2f4869e304c82d07739337eae7c5        
        - "cv2.BORDER_CONSTANT": iiiiii|abcdefgh|iiiiiii with some specified i 
        - "cv2.BORDER_REFLECT": fedcba|abcdefgh|hgfedcb
        - "cv2.BORDER_REFLECT_101": gfedcb|abcdefgh|gfedcba
        - "cv2.BORDER_DEFAULT": same as BORDER_REFLECT_101
        - "cv2.BORDER_REPLICATE": aaaaaa|abcdefgh|hhhhhhh
        - "cv2.BORDER_WRAP": cdefgh|abcdefgh|abcdefg

        - "delete": Return empty array (all zero) if the cell is too far at border (delete image)
        - "alternate": randomize the padding operation
    Returns
    ----------
    images: list of images. Each image is a numpy array of shape 
    (final_h,final_w,channels) 

    """
    #Convert position of cell from "um" to "pixel index"
    #pos_x,pos_y = pos_x/pix,pos_y/pix  
    padding_modes = ["cv2.BORDER_CONSTANT","cv2.BORDER_REFLECT","cv2.BORDER_REFLECT_101","cv2.BORDER_REPLICATE","cv2.BORDER_WRAP"]
    
    for i in range(len(images)):
        image = images[i]
    
        #Compute the edge-coordinates that define the cropped image
        y1 = np.around(pos_y[i]-final_h/2.0)              
        x1 = np.around(pos_x[i]-final_w/2.0) 
        y2 = y1+final_h               
        x2 = x1+final_w

        #Are these coordinates within the oringinal image?
        #If not, the image needs padding
        pad_top,pad_bottom,pad_left,pad_right = 0,0,0,0

        if y1<0:#Padding is required on top of image
            pad_top = int(abs(y1))
            y1 = 0 #set y1 to zero and pad pixels after cropping
            
        if y2>image.shape[0]:#Padding is required on bottom of image
            pad_bottom = int(y2-image.shape[0])
            y2 = image.shape[0]
        
        if x1<0:#Padding is required on left of image
            pad_left = int(abs(x1))
            x1 = 0
        
        if x2>image.shape[1]:#Padding is required on right of image
            pad_right = int(x2-image.shape[1])
            x2 = image.shape[1]
        
        #Crop the image
        temp = image[int(y1):int(y2),int(x1):int(x2)]

        if pad_top+pad_bottom+pad_left+pad_right>0:
            if padding_mode.lower()=="delete":
                temp = np.zeros_like(temp)
            else:
                #Perform all padding operations in one go
                if padding_mode.lower()=="alternate":
                    ind = rand_state.randint(low=0,high=len(padding_modes))
                    padding_mode = padding_modes[ind]
                    temp = cv2.copyMakeBorder(temp, pad_top, pad_bottom, pad_left, pad_right, eval(padding_modes[ind]))
                else:
                    temp = cv2.copyMakeBorder(temp, pad_top, pad_bottom, pad_left, pad_right, eval(padding_mode))
        
        images[i] = temp
            
    return images


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
        MainWindow.setObjectName("YouLabel_v"+VERSION)
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
        
        self.label_showFullImage = pg.ImageView(self.splitter)
        self.label_showFullImage.setMinimumSize(QtCore.QSize(0, 200))
        self.label_showFullImage.setMaximumSize(QtCore.QSize(9999999, 200))
        self.label_showFullImage.ui.histogram.hide()
        self.label_showFullImage.ui.roiBtn.hide()
        self.label_showFullImage.ui.menuBtn.hide()

        self.label_showFullImage.setObjectName("label_showFullImage")
        self.label_showCroppedImage = pg.ImageView(self.splitter)
        self.label_showCroppedImage.setMinimumSize(QtCore.QSize(0, 200))
        self.label_showCroppedImage.setMaximumSize(QtCore.QSize(9999999, 200))
        self.label_showCroppedImage.ui.histogram.hide()
        self.label_showCroppedImage.ui.roiBtn.hide()
        self.label_showCroppedImage.ui.menuBtn.hide()

        
        self.label_showCroppedImage.setObjectName("label_showCroppedImage")
        self.verticalLayout.addWidget(self.splitter)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.horizontalSlider_channel = QtWidgets.QSlider(self.tab_work)
        self.horizontalSlider_channel.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_channel.setObjectName("horizontalSlider_channel")
        self.horizontalLayout_4.addWidget(self.horizontalSlider_channel)
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
        self.radioButton_true.setEnabled(False)
        
        self.radioButton_true.setObjectName("radioButton_true")
        self.horizontalLayout_2.addWidget(self.radioButton_true)
        self.radioButton_false = QtWidgets.QRadioButton(self.tab_work)
        self.radioButton_false.setMinimumSize(QtCore.QSize(21, 20))
        self.radioButton_false.setMaximumSize(QtCore.QSize(21, 20))
        self.radioButton_false.setText("")
        self.radioButton_false.setEnabled(False)
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
        
        
        
        
        self.verticalLayout_4 = QtWidgets.QVBoxLayout()
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.groupBox_imgProc = QtWidgets.QGroupBox(self.groupBox_decisions)
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
        
        self.label_CropIcon_2.setPixmap(QtGui.QPixmap(os.path.join(dir_root,"art","cropping.png")))
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
        self.label_colorModeIcon.setPixmap(QtGui.QPixmap(os.path.join(dir_root,"art","color_mode.png")))
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
        self.label_padIcon.setPixmap(QtGui.QPixmap(os.path.join(dir_root,"art","padding.png")))
        self.label_padIcon.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_padIcon.setObjectName("label_padIcon")
        self.horizontalLayout_nrEpochs.addWidget(self.label_padIcon)
        self.label_paddingMode = QtWidgets.QLabel(self.groupBox_imgProc)
        self.label_paddingMode.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_paddingMode.setObjectName("label_paddingMode")
        self.horizontalLayout_nrEpochs.addWidget(self.label_paddingMode)
        self.gridLayout_49.addLayout(self.horizontalLayout_nrEpochs, 1, 0, 1, 1)
        self.comboBox_BgRemove = QtWidgets.QComboBox(self.groupBox_imgProc)
        self.comboBox_BgRemove.setMinimumSize(QtCore.QSize(200, 0))
        self.comboBox_BgRemove.setObjectName("comboBox_BgRemove")
        self.comboBox_BgRemove.addItem("")
        self.comboBox_BgRemove.addItem("")

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
        self.gridLayout_49.addWidget(self.comboBox_paddingMode, 1, 1, 1, 1)
        self.horizontalLayout_normalization = QtWidgets.QHBoxLayout()
        self.horizontalLayout_normalization.setObjectName("horizontalLayout_normalization")
        self.label_NormalizationIcon = QtWidgets.QLabel(self.groupBox_imgProc)
        self.label_NormalizationIcon.setText("")
        self.label_NormalizationIcon.setPixmap(QtGui.QPixmap(os.path.join(dir_root,"art","normalzation.png")))
        self.label_NormalizationIcon.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_NormalizationIcon.setObjectName("label_NormalizationIcon")
        self.horizontalLayout_normalization.addWidget(self.label_NormalizationIcon)
        self.label_Normalization = QtWidgets.QLabel(self.groupBox_imgProc)
        self.label_Normalization.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.label_Normalization.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_Normalization.setObjectName("label_Normalization")
        self.horizontalLayout_normalization.addWidget(self.label_Normalization)
        self.gridLayout_49.addLayout(self.horizontalLayout_normalization, 0, 3, 1, 1)
        self.verticalLayout_4.addWidget(self.groupBox_imgProc)
        
        self.groupBox_saving = QtWidgets.QGroupBox(self.groupBox_decisions)
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
        self.verticalLayout_4.addWidget(self.groupBox_saving)
        self.gridLayout_4.addLayout(self.verticalLayout_4, 0, 1, 1, 1)
        self.gridLayout_5.addWidget(self.groupBox_decisions, 1, 0, 1, 1)
        self.tabWidget.addTab(self.tab_work, "")
        self.gridLayout.addWidget(self.tabWidget, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1082, 25))
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
        self.shortcut_channel = QtGui.QShortcut(QtGui.QKeySequence("C"), self.tabWidget)
        self.shortcut_channel.activated.connect(self.next_channel)

        self.pushButton_true.clicked.connect(self.true_cell)
        self.pushButton_false.clicked.connect(self.false_cell)

        self.shortcut_next = QtGui.QShortcut(QtGui.QKeySequence("Right"), self.tabWidget)
        self.shortcut_next.activated.connect(self.next_cell)
        self.shortcut_next = QtGui.QShortcut(QtGui.QKeySequence("Left"), self.tabWidget)
        self.shortcut_next.activated.connect(self.previous_cell)

        self.horizontalSlider_index.valueChanged.connect(self.onIndexChange)
        self.spinBox_index.valueChanged.connect(self.onIndexChange)
        self.spinBox_cropsize.valueChanged.connect(lambda ind: self.put_image(self.spinBox_index.value()))
        self.comboBox_paddingMode.currentIndexChanged.connect(lambda ind: self.put_image(self.spinBox_index.value()))
        self.comboBox_BgRemove.currentIndexChanged.connect(lambda ind: self.put_image(self.spinBox_index.value()))
        self.horizontalSlider_channel.valueChanged.connect(lambda ind: self.put_image(self.spinBox_index.value()))
        self.comboBox_GrayOrRGB.currentIndexChanged.connect(lambda ind: self.put_image(self.spinBox_index.value()))
        
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
        MainWindow.setWindowTitle(_translate("MainWindow", "YouLabel_v"+VERSION))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.LoadFiles), _translate("MainWindow", "Load Files"))
        self.pushButton_start.setText(_translate("MainWindow", "Start"))
        self.pushButton_true.setText(_translate("MainWindow", "TRUE!"))
        self.pushButton_true.setToolTip(_translate("MainWindow", "Shortcut: T"))
        self.pushButton_false.setText(_translate("MainWindow", "FALSE!"))
        self.pushButton_false.setToolTip(_translate("MainWindow", "Shortcut: F"))
        self.horizontalSlider_index.setToolTip(_translate("MainWindow", "Shortcut: Left/Right arrow"))
        self.horizontalSlider_channel.setToolTip(_translate("MainWindow", "Shortcut: C"))

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

        self.comboBox_GrayOrRGB.setItemText(0, _translate("MainWindow", "Grayscale"))
        self.comboBox_GrayOrRGB.setItemText(1, _translate("MainWindow", "RGB"))

        self.comboBox_BgRemove.setItemText(0, _translate("MainWindow", "None"))
        self.comboBox_BgRemove.setItemText(1, _translate("MainWindow", "vstripes_removal"))
       
        self.label_Normalization.setToolTip(_translate("MainWindow", "Define, if a particular backgound removal algorithm should be applied (chnages only the appearance of the displayed image. Has no effect during saving (original images are saved)"))
        self.label_Normalization.setText(_translate("MainWindow", "Background removal"))
        self.groupBox_saving.setTitle(_translate("MainWindow", "Saving"))
        self.pushButton_saveTrueAs.setText(_translate("MainWindow", "Save TRUE cells as..."))
        self.pushButton_saveTrueAs.setToolTip(_translate("MainWindow", "File is saved into same directory as original file."))
        self.pushButton_saveFalseAs.setText(_translate("MainWindow", "Save FALSE cells as..."))
        self.pushButton_saveFalseAs.setToolTip(_translate("MainWindow", "File is saved into same directory as original file."))

        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_work), _translate("MainWindow", "Label Images"))




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
                    rtdc_ds = h5py.File(rtdc_path, 'r')
                except:
                    rtdc_ds = h5py.File(rtdc_path, 'r')
                    
                features = list(rtdc_ds["events"].keys())
                #Make sure that there is "images", "pos_x" and "pos_y" available
                if "image" in features and "pos_x" in features and "pos_y" in features:
                    nr_images = rtdc_ds["events"]["image"].len()
                    pix = rtdc_ds.attrs["imaging:pixel size"]
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
        if len(img.shape)==2:
            print("Invalid image shape "+str(img.shape))
            return
            #channels = 1 #actually that case should not never exist as np.expand_dims was used before to get images in format (NHWC)
        elif len(img.shape)==3:
            height, width, channels = img.shape
            print("Img.shape"+str(img.shape))
        else:
            print("Invalid image format: "+str(img.shape))
            return

        channel_targ = int(self.horizontalSlider_channel.value())
        color_mode = str(self.comboBox_GrayOrRGB.currentText())
        if channel_targ<img.shape[-1]:
            img = img[:,:,channel_targ] #select single channel which is displayed

        #if the slider is on the very right: create superposition of all channels
        elif channel_targ>=img.shape[-1]:
            if color_mode=="Grayscale":
                #if Color_Mode is grayscale, convert RGB to grayscale
                #simply by taking the mean across all channels
                img = np.mean(img,axis=-1).astype(np.uint8)
            elif color_mode=="RGB":
                if channels==1:
                    #there is just one channel provided, but for displyaing, 
                    #3 channels are needed: add two zero-channels
                    zeros = np.zeros(img.shape[:2]+(1,))
                    img = np.c_[img,zeros,zeros]
                    print("Added 2nd and 3rd channel: "+str(img.shape))

                elif channels==2:
                    #there are just two channel provided, but for displyaing, 
                    #3 channels are needed add one zero-channel
                    zeros = np.zeros(img.shape[:2]+(1,))
                    img = np.c_[img,zeros]
                    print("Added 3rd channel: "+str(img.shape))

        #Background removal:
        if str(self.comboBox_BgRemove.currentText())=="":
            img = img#no removal
        elif str(self.comboBox_BgRemove.currentText())=="vstripes_removal":
            img = vstripes_removal(img)

        #zoom image such that longest side is 200
        factor = np.round(float(200/np.max(img.shape)),0)
        img_zoom =  cv2.resize(img, dsize=None,fx=factor, fy=factor, interpolation=cv2.INTER_LINEAR)

        img_zoom = np.ascontiguousarray(img_zoom)
        print("Shape of zoomed image: "+str(img_zoom.shape))
        
        if color_mode=="Grayscale":
            self.label_showFullImage.setImage(img_zoom.T,autoRange=False)
        elif color_mode=="RGB":
            self.label_showFullImage.setImage(np.swapaxes(img_zoom,0,1),autoRange=False)
            
        self.label_showFullImage.ui.histogram.hide()
        self.label_showFullImage.ui.roiBtn.hide()
        self.label_showFullImage.ui.menuBtn.hide()

        #get the location of the cell
        PIX = self.rtdc_ds.attrs["imaging:pixel size"]
        
        pos_x,pos_y = self.rtdc_ds["events"]["pos_x"][ind]/PIX,self.rtdc_ds["events"]["pos_y"][ind]/PIX
        cropsize = self.spinBox_cropsize.value()
        
        padding_mode = str(self.comboBox_paddingMode.currentText())
        padding_mode = pad_arguments_np2cv(padding_mode)
        img_crop = image_crop_pad_cv2([img],[pos_x],[pos_y],PIX,cropsize,cropsize,padding_mode=padding_mode)
        img_crop = img_crop[0]
        #zoom image such that the height gets the same as for non-cropped img
        factor = float(float(height)/np.max(img_crop.shape[0]))
        if np.isinf(factor):
            factor = 2.5
        img_crop =  cv2.resize(img_crop, dsize=None,fx=factor, fy=factor, interpolation=cv2.INTER_LINEAR)

        img_crop = np.ascontiguousarray(img_crop)

        if color_mode=="Grayscale":
            self.label_showCroppedImage.setImage(img_crop.T,autoRange=False)
        elif color_mode=="RGB":
            self.label_showCroppedImage.setImage(np.swapaxes(img_crop,0,1),autoRange=False)
            
        self.label_showCroppedImage.ui.histogram.hide()
        self.label_showCroppedImage.ui.roiBtn.hide()
        self.label_showCroppedImage.ui.menuBtn.hide()


    def start_analysis(self):
        rtdc_path = str(self.comboBox_selectFile.currentText())
        print(rtdc_path)
        #get the rtdc_ds
        #sometimes there occurs an error when opening hdf files,
        #therefore try this a second time in case of an error.
        #This is very strange, and seems like an unsufficient/dirty solution,
        #but I never saw it failing two times in a row
        try:
            rtdc_ds = h5py.File(rtdc_path, 'r')
        except:
            rtdc_ds = h5py.File(rtdc_path, 'r')
        
        self.rtdc_ds = rtdc_ds
        
        #Load the first image and show on label_showFullImage and label_showCroppedImage
        image_shape = rtdc_ds["events"]["image"].shape
        nr_images = image_shape[0]
        self.spinBox_index.setRange(0,nr_images-1)
        self.horizontalSlider_index.setRange(0,nr_images-1)
        #Set both to zero
        self.spinBox_index.setValue(0)
        self.horizontalSlider_index.setValue(0)
        
        
        #check if there other channels available
        h5 = h5py.File(rtdc_path, 'r')
        keys = list(h5["events"].keys())
        ind_ch = np.array(["image_ch" in key for key in keys])
        channels = np.sum(ind_ch) #1+ is because there is always at least one channel (rtdc_ds["image"])
        ind_ch = np.where(ind_ch==True)[0]
        keys_ch = list(np.array(keys)[ind_ch])
        #Set the slider such that every channel can be selected
        self.horizontalSlider_channel.setRange(0,channels+1) #add one more dimension for a "blending"/superposition channel
        #Define variable on self that carries all image information
        if channels==0:
            self.Images = np.expand_dims(rtdc_ds["events"]["image"][:],-1)
        elif channels>0:
            self.Images = np.stack( [rtdc_ds["events"]["image"][:]] + [h5["events"][key][:] for key in keys_ch] ,axis=-1)            

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
            self.radioButton_false.setChecked(False)

        elif tr_or_wr=="False":
            self.radioButton_false.setChecked(True)
            self.radioButton_true.setChecked(False)

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
        if index<len(self.rtdc_ds["events"]["pos_x"]):
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
        if index<len(self.rtdc_ds["events"]["pos_x"]):
            self.onIndexChange(index+1)

    def next_cell(self):
        index = int(self.spinBox_index.value())
        if index<len(self.rtdc_ds["events"]["pos_x"]):
            self.onIndexChange(index+1)

    def previous_cell(self):       
        index = int(self.spinBox_index.value())
        if index<len(self.rtdc_ds["events"]["pos_x"]):
            self.onIndexChange(index-1)

    def next_channel(self):
        "Shift the slider horizontalSlider_channel to the next location"
        
        #Only continue, if a dataset was already loaded:
        if self.comboBox_selectFile.count()<1:
            return
        
        #get current location of slider
        slider_current = int(self.horizontalSlider_channel.value())
        #get the maximum position
        slider_max = self.horizontalSlider_channel.maximum()
        
        if slider_current == slider_max:
            self.horizontalSlider_channel.setValue(0)
        else:
            self.horizontalSlider_channel.setValue(slider_current+1)            
        
        
    def save_true_events(self):
        #read from table, which events are true
        rows = self.tableWidget_decisions.rowCount()
        decisions = []
        for row in range(rows):
            decisions.append(str(self.tableWidget_decisions.item(row, 0).text()))
        decisions = [dec=="True" for dec in decisions]

        ind = np.where(np.array(decisions)==True)[0]        
        #what is the filename of the initial file?
        fname = str(self.comboBox_selectFile.currentText())
        rtdc_path = fname
        fname = fname.split(".rtdc")[0]
        #what is the user defined ending?
        ending = str(self.lineEdit_TrueFname.text())
        fname = fname+"_"+ending
        
        #write information about these events to excel file
        #fname_excel = fname.split(".rtdc")[0]+".csv"        
        
        #write_rtdc expects lists of experiments. Here we will only have a single exp. 
        write_rtdc(fname,rtdc_path,ind,np.array(decisions))
        print("Saved true events")


    def save_false_events(self):
        #read from table, which events are true
        rows = self.tableWidget_decisions.rowCount()
        decisions = []
        for row in range(rows):
            decisions.append(str(self.tableWidget_decisions.item(row, 0).text()))
        decisions = [dec=="True" for dec in decisions]

        ind = np.where(np.array(decisions)==False)[0]        
        #what is the filename of the initial file?
        fname = str(self.comboBox_selectFile.currentText())
        rtdc_path = fname
        fname = fname.split(".rtdc")[0]
        #what is the user defined ending?
        ending = str(self.lineEdit_FalseFname.text())
        fname = fname+"_"+ending
        #write_rtdc expects lists of experiments. Here we will only have a single exp. 
        write_rtdc(fname,rtdc_path,ind,np.array(decisions))
        print("Saved false events")


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(os.path.join(dir_root,"art","icon_main"+icon_suff)))
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

