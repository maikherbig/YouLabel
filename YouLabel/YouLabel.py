# -*- coding: utf-8 -*-

"""
YouLabel: Software with GUI to view and label images of hdf5 datasets
"""
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets, QtGui
import os, sys
import numpy as np
rand_state = np.random.RandomState(13) #to get the same random number on diff. PCs 
import traceback
import cv2
import h5py,shutil,time,hdf5plugin
import frontend

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

__version__ = "0.2.7" #Python 3.7.10 Version
print("YouLabel Version: "+__version__)

if sys.platform=="darwin":
    icon_suff = ".icns"
else:
    icon_suff = ".ico"

dir_root = os.path.dirname(__file__)

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

def load_rtdc(rtdc_path):
    """
    This function load .rtdc files using h5py and takes care of catching all
    errors
    """
    try:
        try:
            #sometimes there occurs an error when opening hdf files,
            #therefore try opening a second time in case of an error.
            #This is very strange, and seems like a dirty solution,
            #but I never saw it failing two times in a row
            rtdc_ds = h5py.File(rtdc_path, 'r')
        except:
            rtdc_ds = h5py.File(rtdc_path, 'r')
        return False,rtdc_ds #failed=False
    except Exception as e:
        #There is an issue loading the files!
        return True,e


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
    
    #Add thekey label (if it does not already exist)
    if "label" not in h5_orig["events"].keys():
        keys = ["label"] + list(h5_orig["events"].keys())
    else:
        keys = list(h5_orig["events"].keys())

    #Find pixel size of original file:
    pixel_size = h5_orig.attrs["imaging:pixel size"]

    #Open target hdf5 file
    h5_targ = h5py.File(fname,'a')

    # Write data
    for key in keys:

        if key == "index":
            values = np.array(range(len(indices)))+1
            h5_targ.create_dataset("events/"+key, data=values,dtype=values.dtype)

        elif key == "index_online":
            if "index_online" in h5_orig["events"].keys():
                values = h5_orig["events"]["index_online"][indices]
            elif "index" in h5_orig["events"].keys():
                values = h5_orig["events"]["index"][indices]
            else:
                break
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
    sample = os.path.basename(rtdc_path)
    sample = os.path.splitext(sample)[0]
    h5_targ.attrs["experiment:sample"] = sample
    h5_targ.attrs["experiment:date"] = time.strftime("%Y-%m-%d")
    h5_targ.attrs["experiment:time"] = time.strftime("%H:%M:%S")
    h5_targ.attrs["imaging:pixel size"] = pixel_size
    #h5_targ.attrs["experiment:original_file"] = rtdc_path
    meta_keys = list(h5_orig.attrs.keys())
    if "setup:identifier" in meta_keys:
         h5_targ.attrs["setup:identifier"] = rtdc_path

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

def clip_contrast(img,low,high,auto=False):
    if auto==True:
        low,high = np.min(img),np.max(img)
    # limit_lower = limits[0]
    # limit_upper = limits[1]
    img[:,:] = np.clip(img[:,:],a_min=low,a_max=high)
    mini,maxi = np.min(img[:,:]),np.max(img[:,:])/255
    img[:,:] = (img[:,:]-mini)/maxi
    return img

class MyPopup(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi()

    def setupUi(self):
        frontend.setup_main_ui(self)
    
    def retranslateUi(self):
        frontend.retranslate_main_ui(self,__version__)

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
            failed,rtdc_ds = load_rtdc(rtdc_path)
            if failed:
                frontend.message("Error occurred during loading file","Error")
                return
                
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
            #Place a combobox with the available features
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, fileinfo[rowNumber]["nr_images"])
            item.setFlags(item.flags() &~QtCore.Qt.ItemIsEnabled &~ QtCore.Qt.ItemIsSelectable )
            self.tableWidget_loadFiles.setItem(rowPosition, columnPosition, item)

            columnPosition = 2
            #Pixel size
            item = QtWidgets.QTableWidgetItem()
            pix = fileinfo[rowNumber]["pix"]
            item.setData(QtCore.Qt.EditRole,pix)
            self.tableWidget_loadFiles.setItem(rowPosition, columnPosition, item)

        

    def put_image(self,ind):
        #Function puts new image on the screen
        
        #Only perform after each 30ms (faster is useless)
        if time.time() - self.time_show_img<0.03:
            return #return if less than 30ms time difference
        
        self.time_show_img = time.time() #update time-tag

        if ind==None:
            ind = int(self.spinBox_index.value())
        img = self.Images[ind]
        
        if len(img.shape)==2: #actually, that case should never occur as np.expand_dims was used before to get images in format (NHWC)
            print("Invalid image shape "+str(img.shape))
            return
            #channels = 1 
        elif len(img.shape)==3:
            height, width, channels = img.shape
        else:
            print("Invalid image format: "+str(img.shape))
            return

        #Retrieve the setting from self.popup_layercontrols_ui
        ui_item = self.popup_layercontrols_ui
        layer_names = [obj.text() for obj in ui_item.label_layername_chX]
        layer_active = [obj.isChecked() for obj in ui_item.checkBox_show_chX]
        layer_range = [obj.getRange() for obj in ui_item.horizontalSlider_chX]
        layer_auto = [obj.isChecked() for obj in ui_item.checkBox_auto_chX]
        layer_cmap = [obj.currentText() for obj in ui_item.comboBox_cmap_chX]

        #Assemble the image according to the settings in self.popup_layercontrols_ui
        #Find activated layers for each color:
        ind_active_r,ind_active_g,ind_active_b = [],[],[]
        for ch in range(len(layer_cmap)):
        #for color,active in zip(layer_cmap,layer_active):
            if layer_cmap[ch]=="Red" and layer_active[ch]==True:
                ind_active_r.append(ch)
            if layer_cmap[ch]=="Green" and layer_active[ch]==True:
                ind_active_g.append(ch)
            if layer_cmap[ch]=="Blue" and layer_active[ch]==True:
                ind_active_b.append(ch)
        if len(ind_active_r)>0:
            img_ch = img[:,:,np.array(ind_active_r)]
            layer_range_ch = np.array(layer_range)[np.array(ind_active_r)] #Range of all red channels 
            layer_auto_ch = np.array(layer_auto)[np.array(ind_active_r)] #Automatic range
            #Scale each red channel according to layer_range
            for layer in range(img_ch.shape[-1]):
                limits,auto = layer_range_ch[layer],layer_auto_ch[layer]
                img_ch[:,:,layer] = clip_contrast(img=img_ch[:,:,layer],low=limits[0],high=limits[1],auto=auto)
            img_r = np.mean(img_ch,axis=-1).astype(np.uint8)
        else:
            img_r = np.zeros(shape=(img.shape[0],img.shape[1]),dtype=np.uint8)
            
        if len(ind_active_g)>0:
            img_ch = img[:,:,np.array(ind_active_g)]
            layer_range_ch = np.array(layer_range)[np.array(ind_active_g)] #Range of all red channels 
            layer_auto_ch = np.array(layer_auto)[np.array(ind_active_g)] #Automatic range
            #Scale each red channel according to layer_range
            for layer in range(img_ch.shape[-1]):
                limits,auto = layer_range_ch[layer],layer_auto_ch[layer]
                img_ch[:,:,layer] = clip_contrast(img=img_ch[:,:,layer],low=limits[0],high=limits[1],auto=auto)
            img_g = np.mean(img_ch,axis=-1).astype(np.uint8)
        else:
            img_g = np.zeros(shape=(img.shape[0],img.shape[1]),dtype=np.uint8)

        if len(ind_active_b)>0:
            img_ch = img[:,:,np.array(ind_active_b)]
            layer_range_ch = np.array(layer_range)[np.array(ind_active_b)] #Range of all red channels 
            layer_auto_ch = np.array(layer_auto)[np.array(ind_active_b)] #Automatic range
            #Scale each red channel according to layer_range
            for layer in range(img_ch.shape[-1]):
                limits,auto = layer_range_ch[layer],layer_auto_ch[layer]
                img_ch[:,:,layer] = clip_contrast(img=img_ch[:,:,layer],low=limits[0],high=limits[1],auto=auto)
            img_b = np.mean(img_ch,axis=-1).astype(np.uint8)
        else:
            img_b = np.zeros(shape=(img.shape[0],img.shape[1]),dtype=np.uint8)
        
        #Assemble image by stacking all layers
        img = np.stack([img_r,img_g,img_b],axis=-1)
        # channel_targ = 0#int(self.horizontalSlider_channel.value())
        color_mode = str(self.comboBox_GrayOrRGB.currentText())
        
        if color_mode=="Grayscale":
            #if Color_Mode is grayscale, convert RGB to grayscale
            #simply by taking the mean across all channels
            img = np.mean(img,axis=-1).astype(np.uint8)
            
            #Normalize the image back to match range 0-255
            mult = float(self.doubleSpinBox_brightness.value())
            img = mult*img
            # mini,maxi = np.min(img),np.max(img)/255
            # img = (img-mini)/maxi

        
        
        #Background removal:
        if str(self.comboBox_BgRemove.currentText())=="":
            img = img#no removal
        elif str(self.comboBox_BgRemove.currentText())=="vstripes_removal":
            img = vstripes_removal(img)

        img_zoom = np.ascontiguousarray(img)
        if color_mode=="Grayscale":
            self.label_showFullImage.setImage(img_zoom.T,autoRange=False)#,autoLevels=False)
            self.label_showFullImage.setLevels(0,255)
        elif color_mode=="RGB":
            self.label_showFullImage.setImage(np.swapaxes(img_zoom,0,1),autoRange=False)#,autoLevels=False)
            self.label_showFullImage.setLevels(0,255)

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

        img_crop = np.ascontiguousarray(img_crop)
        if color_mode=="Grayscale":
            self.label_showCroppedImage.setImage(img_crop.T,autoRange=False)#,autoLevels=False)
            self.label_showCroppedImage.setLevels(0,255)
        elif color_mode=="RGB":
            img_show = np.swapaxes(img_crop,0,1)
            self.label_showCroppedImage.setImage(img_show,autoRange=False)#,autoLevels=False)
            self.label_showCroppedImage.setLevels(0,255)
            
            #self.label_showCroppedImage.setLevels(min=None,max=None,rgba=[(0,255),(0,255),(0,255),(0,100)])
        self.label_showCroppedImage.ui.histogram.hide()
        self.label_showCroppedImage.ui.roiBtn.hide()
        self.label_showCroppedImage.ui.menuBtn.hide()


    def start_analysis(self):
        rtdc_path = str(self.comboBox_selectFile.currentText())
        print(rtdc_path)
        #get the rtdc_ds
        failed,rtdc_ds = load_rtdc(rtdc_path)        
        self.rtdc_ds = rtdc_ds
        
        self.layercontrols_show_nr = 0
        self.time_show_img = time.time()

        #Load the first image and show on label_showFullImage and label_showCroppedImage
        image_shape = rtdc_ds["events"]["image"].shape
        nr_images = image_shape[0]
        self.spinBox_index.setRange(0,nr_images-1)
        self.horizontalSlider_index.setRange(0,nr_images-1)
        #Set both to zero
        self.spinBox_index.setValue(0)
        self.horizontalSlider_index.setValue(0)
                
        #check which channels are available
        keys = list(rtdc_ds["events"].keys())
        #find keys of image_channels
        keys_image = []
        for key in keys:
            if type(rtdc_ds["events"][key])==h5py._hl.dataset.Dataset:
                shape = rtdc_ds["events"][key].shape
                if len(shape)==3: #images have special shape (2D arrays)
                    keys_image.append(key)
        #Sort keys_image: "image" first; "mask" last 
        keys_image.insert(0, keys_image.pop(keys_image.index("image")))
        if 'mask' in keys_image:
            keys_image.insert(len(keys_image), keys_image.pop(keys_image.index("mask")))

        #initialize a layer-options-popup-window
        self.init_layercontrols(keys_image)

        channels = len(keys_image)
        #Set the slider such that every channel can be selected
        #self.horizontalSlider_channel.setRange(0,channels+1) #add one more dimension for a "blending"/superposition channel
        #Define variable on self that carries all image information
        if channels==0: 
            self.Images = np.expand_dims(rtdc_ds["events"]["image"][:],-1)
        elif channels>0:
            self.Images = np.stack( [rtdc_ds["events"][key][:] for key in keys_image] ,axis=-1)            

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
            item.setData(QtCore.Qt.DisplayRole, "0")
            item.setFlags(item.flags() &~QtCore.Qt.ItemIsEnabled &~ QtCore.Qt.ItemIsSelectable )
            self.tableWidget_decisions.setItem(row, 0, item)

        
    def onIndexChange(self,index):
        self.spinBox_index.setValue(index)
        self.horizontalSlider_index.setValue(index)
        
        #Get the current index
        index = int(self.spinBox_index.value())
        #Read from tableWidget_decisions if True or Wrong
        tr_or_wr = self.tableWidget_decisions.item(index, 0).text() 
        
        if index%25==0:
            self.fill_class_combobox()
        
        #display the corresponding image
        self.put_image(ind=index)
        
        
    def true_cell(self):
        #Current index
        index = int(self.spinBox_index.value())
        #When false is triggered, change this row in the table
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.DisplayRole, "1")
        item.setFlags(item.flags() &~QtCore.Qt.ItemIsEnabled &~ QtCore.Qt.ItemIsSelectable )
        self.tableWidget_decisions.setItem(index, 0, item)
        if index<len(self.rtdc_ds["events"]["pos_x"]):
            self.onIndexChange(index+1)
        
    def false_cell(self):
        #Current index
        index = int(self.spinBox_index.value())
        #When false is triggered, change this row in the table
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.DisplayRole, "0")
        item.setFlags(item.flags() &~QtCore.Qt.ItemIsEnabled &~ QtCore.Qt.ItemIsSelectable )
        self.tableWidget_decisions.setItem(index, 0, item)
        if index<len(self.rtdc_ds["events"]["pos_x"]):
            self.onIndexChange(index+1)


    def keyPressEvent(self, event):
        numbers = [QtCore.Qt.Key_0,QtCore.Qt.Key_1,QtCore.Qt.Key_2,QtCore.Qt.Key_3,\
        QtCore.Qt.Key_4,QtCore.Qt.Key_5,QtCore.Qt.Key_6,QtCore.Qt.Key_7,QtCore.Qt.Key_8,\
        QtCore.Qt.Key_9]
        ind = np.where(np.array(numbers)==event.key())[0]
        if len(ind)==1:
            self.number_pressed(ind[0])

    def number_pressed(self,value):
        #Current index
        index = int(self.spinBox_index.value())
        #When true is hit, change this row in the table
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.DisplayRole, str(value))
        item.setFlags(item.flags() &~QtCore.Qt.ItemIsEnabled &~ QtCore.Qt.ItemIsSelectable )
        self.tableWidget_decisions.setItem(index, 0, item)
        
        #got to the next cell, if the current index is not the last index
        if index<len(self.rtdc_ds["events"]["pos_x"]):
            self.onIndexChange(index+1)
        else:#In case its the last cell, fill the combobox
            self.fill_class_combobox()

        
    def next_cell(self):
        index = int(self.spinBox_index.value())
        if index<len(self.rtdc_ds["events"]["pos_x"]):
            self.onIndexChange(index+1)
        else:#In case its the last cell, fill the combobox
            self.fill_class_combobox()

    def previous_cell(self):       
        index = int(self.spinBox_index.value())
        if index<len(self.rtdc_ds["events"]["pos_x"]):
            self.onIndexChange(index-1)
        
   
    def save_events(self):
        #Which class should be saved?
        class_save = self.comboBox_Class.currentText()
        #read from table, which events belong to that class
        rows = self.tableWidget_decisions.rowCount()
        decisions = []
        for row in range(rows):
            decisions.append(str(self.tableWidget_decisions.item(row, 0).text()))
        decisions = [dec==class_save for dec in decisions]

        ind = np.where(np.array(decisions)==True)[0]       
        #what is the filename of the initial file?
        fname = str(self.comboBox_selectFile.currentText())
        rtdc_path = fname
        filename, file_extension = os.path.splitext(fname)
        fname = fname.split(file_extension)[0]
        #what is the user defined ending?
        ending = str(self.lineEdit_Savename.text())
        fname = fname+"_"+ending
        
        #write information about these events to excel file
        #fname_excel = fname.split(".rtdc")[0]+".csv"        
        
        #write_rtdc expects lists of experiments. Here we will only have a single exp. 
        write_rtdc(fname,rtdc_path,ind,np.array(decisions))
        print("Saved events")


    def fill_class_combobox(self):
        #get the content of tableWidget_decisions
        rows = self.tableWidget_decisions.rowCount()
        decisions = []
        for row in range(rows):
            decisions.append(int(self.tableWidget_decisions.item(row, 0).text()))
        decisions = set(decisions)
        decisions = [str(d) for d in decisions]
        #First delete all content of the combobox
        self.comboBox_Class.clear()
        #Populate comboBox_Class
        self.comboBox_Class.addItems(decisions)
        self.lineEdit_Savename.setEnabled(True)
        self.pushButton_Save.setEnabled(True)

    def init_layercontrols(self,keys_image):
        self.popup_layercontrols = MyPopup()
        self.popup_layercontrols_ui = frontend.Ui_LayerControl()
        self.popup_layercontrols_ui.setupUi(self.popup_layercontrols,keys_image) #open a popup

    def show_layercontrols(self):
        self.layercontrols_show_nr += 1
        #self.popup_layercontrols_ui.pushButton_close.clicked.connect(self.visualization_settings)
        if self.layercontrols_show_nr==1:
            for iterator in range(len(self.popup_layercontrols_ui.spinBox_minChX)):
                slider = self.popup_layercontrols_ui.horizontalSlider_chX[iterator]
                slider.startValueChanged.connect(lambda _, b=None: self.put_image(ind=b))
                slider.endValueChanged.connect(lambda _, b=None: self.put_image(ind=b))
                checkBox = self.popup_layercontrols_ui.checkBox_show_chX[iterator]
                checkBox.stateChanged.connect(lambda _, b=None: self.put_image(ind=b))
                comboBox = self.popup_layercontrols_ui.comboBox_cmap_chX[iterator]
                comboBox.currentIndexChanged.connect(lambda _, b=None: self.put_image(ind=b))
                checkBox = self.popup_layercontrols_ui.checkBox_auto_chX[iterator]
                checkBox.stateChanged.connect(lambda _, b=None: self.put_image(ind=b))

        self.popup_layercontrols.show()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(os.path.join(dir_root,"art","icon_main"+icon_suff)))
    #MainWindow = QtWidgets.QMainWindow()
    ui = MainWindow()
    #ui.setupUi(MainWindow)
    ui.show()
    sys.exit(app.exec_())

