# YouLabel
Software with GUI to view and label images of .rtdc datasets. Multiclass labelling (up to 10 classes) is supported.

# Screenshot
![alt text](art/ScreenShot_v01.png "YouLabel Screenshot")  
Colored rectangles in the image indicate the workflow
1. (Red rectangle) select dataset that should be worked on. After selection the file is loaded and the images of the dataset are displayed.
2. (Orange rectangle) images of the loaded dataset are displayed. In RT-FDC datasets, the midpoint of each tracked object is stored. Based on this midpoint, the full image (left) is cropped (right) to show the tracked object in the center. To display the next or the previous image, the right and left arrow key can be used.    
3. deprecated
4. (Green rectangle) list shows the labelling decisions. Change the label of the shown cell by pressing the key 0-9.  By default, at the beginning, all events are labelled “True” (class 0).  
 
# Installation
YouLabel comes as a standalone executable contained in a zip file. You basically just need to download the .zip and unzip. The following 5 steps explain how this is done:    
* Go to https://github.com/maikherbig/YouLabel/releases
* Download a zip-file (this file contains the **_standalone executable_**)   
* Unzip it  
* Go into the unzipped folder and scroll down until you find an executable (full name is for example "YouLabel_0.1.0.exe")  
* DoubleClick this .exe to run it (no further installation is required)  

# Citing YouLabel  
If you use YouLabel for a scientific publication, citation of the following paper would be appreciated:  
[M. Herbig et al., “Label-free imaging flow cytometry for analysis and sorting of enzymatically dissociated tissues,” Scientific Reports, Jan. 2022.](https://www.nature.com/articles/s41598-022-05007-2)  
