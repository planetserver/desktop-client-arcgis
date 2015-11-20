# http://gis.stackexchange.com/questions/73678/getting-xy-map-coordinates-on-mouse-clicks-as-input-variables-into-a-python-scri?rq=1
# http://wiki.scipy.org/Cookbook/Matplotlib/PySide
#
# IF ERROR
#  - Go here: http://es1.planetserver.eu:8080/rasdaman/ows?query=for%20a%20in%20(hrs000119d3_07_if173l_trr3_1_01)%20return%20encode(a.100,%20%22csv%22)
#
# TODO:
#  - Wouter: Het zou handig zijn als je direct kan klikken en dat achter de schermen het juiste beeld wordt geselecteerd, met eventueel een foutmelding / waarschuwing als er geen beeld / meerdere overlappende beelden zijn op die plek
#  - Export a CSV
#  - Check if there is updated shapefile
#  - Maybe alternative for JSON: joining a table?
#  - Allow to change the colouring
#  - Offset doesn't work if you first select some x and then y.
#  - Save WCPS query in JSON
#  - Allow for simple georeferencing (like HiRISE tool), save FROM-TO points in JSON and apply each time user does band math.
#  - When loading zoom to PS footprint extent
#  - Special band depth mode. Extra button in the PySide window?
#  - Load library spectra
#  - Add a reload option where the WCPS spectra are re-downloaded for a selected footprint. This is handy if the user had changed the spectra locations using the ArcGIS Editor.
#  - Change the PS shapefile so it only shows FRTxxxxyyyy as ProductId and one polygon and it always tries to grab IR and VNIR (except if there is no VNIR)
#  - Option to delete data within footprint
#  - When the point shapefile is edited also alter the JSON.
#  - Function for custom band math so user can do things like d2300*bd2500
#  - Make a .lyr for one HRSC and then hack into the .lyr so we can use it for other HRSC orbits too.
#  - If map proj != PS2 do a map transform when deriving spectra
#  - Drop down menu with summary parameters
#  - Add all SPs
#  - Select MRDR rectangle and draw spectra
#  - Offline mode:
#    + OFFLINE SUMMARY PRODUCTS: https://github.com/jlaura/crism
#    + OFFLINE SPECTRA: offline_spectra.py
#
# INTERESTING:
#  - https://github.com/jlaura/arcgis_addins
#
# POST-ALPHA:
#  - 11/3/14: Load standard RGB the way CAT does: IR:233/78/13, VNIR:54/37/27
#  - 21/3/14: Added WMS button which loads on-the-fly WMS layers:
#    + http://resources.arcgis.com/en/help/main/10.1/index.html#//00s300000008000000
#    + http://forums.arcgis.com/threads/8414-ArcGIS-10-user-python-arcpy-to-add-a-WMS-Service
#
# DONE FOR INITIAL ALPHA VERSION RELEASE OF 10/3/14:
#  - Add point shapefile in which the spectra are saved. How to color the points and diagram?
#    + Build the point shapefile from scratch using a .lyr file
#    + On-the-fly recalculation of ratio
#  - Option to only show between 1 and 2.6 micrometer
#  - Load button to load a folder (set wcpsfolder and load .shp and .json)
#  - config.xml: namespace="ps", so in Python window: import ps
#  - Make the PySide window stay on top
#    + https://qt.gitorious.org/pyside/pyside-examples/source/060dca8e4b82f301dfb33a7182767eaf8ad3d024:examples/widgets/windowflags.py
#  - Allow a vertical offset so that the spectra are all shown nicely.
#  - Add extent of footprint and width, height to planetserver shapefile
#  - Spectral ratio button
#  - Add a combo box where the user can select IR, VNIR, IR+VNIR, and one for 1x1, 3x3, 5x5
#  - Band depth by clicking shoulder and bottom of absorption feature
#  - Save the WCPS output folder. I'm saving it in the WCPS_FOLDER environment setting which
#    is saved per user, not for the system. If this would not work please check:
#    http://stackoverflow.com/questions/15030033/how-do-i-open-windows-registry-with-write-access-in-python

import os, sys
import math
import json
import urllib
import urllib2
import zipfile
import arcpy
import pythonaddins
import numpy as np
import matplotlib
matplotlib.use('AGG')
import pylab
matplotlib.rcParams['backend.qt4'] = "PySide"
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QTAgg as NavigationToolbar
from matplotlib.figure import Figure
from PySide import QtCore, QtGui
from matplotlib import pyplot as pp
pp.ion()
arcpy.OverwriteOutput = True

# def FieldExist(featureclass, fieldname):
    # # http://bjorn.kuiper.nu/2011/04/21/tips-tricks-fieldexists-for-arcgis-10-python/
    # fieldList = arcpy.ListFields(featureclass, fieldname)
    # fieldCount = len(fieldList)
    # if (fieldCount == 1):
        # return True
    # else:
        # return False
        
if sys.hexversion > 0x03000000:
    import winreg
else:
    import _winreg as winreg

# http://stackoverflow.com/a/19640752
class Win32Environment:
    """Utility class to get/set windows environment variable"""

    def __init__(self):
        self.root = winreg.HKEY_CURRENT_USER
        self.subkey = 'Environment'

    def getenv(self, name):
        key = winreg.OpenKey(self.root, self.subkey, 0, winreg.KEY_READ)
        try:
            value, _ = winreg.QueryValueEx(key, name)
        except WindowsError:
            value = ''
        return value

    def setenv(self, name, value):
        key = winreg.OpenKey(self.root, self.subkey, 0, winreg.KEY_ALL_ACCESS)
        winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)
        winreg.CloseKey(key)

def SpectraDataExist():
    global wcpsfolder
    global dataname
    exist = True
    if not os.path.exists(os.path.join(wcpsfolder, dataname + '.json')):
        exist = False
    if not arcpy.Exists(os.path.join(wcpsfolder, dataname + ".shp")):
        exist = False
    return exist

def toggle_addin(boolean):
    combobox_1.enabled = boolean
    combobox_2.enabled = boolean
    tool_1.enabled = boolean
    tool_2.enabled = boolean
    button_1.enabled = boolean
    button_2.enabled = boolean
    button_3.enabled = boolean
    button_4.enabled = boolean
    button_5.enabled = boolean
    button_6.enabled = boolean
    button_7.enabled = boolean
    button_8.enabled = boolean
    button_9.enabled = boolean
    # button_10 is the new/change button
    button_11.enabled = boolean
    button_12.enabled = boolean
    button_13.enabled = boolean
    button_14.enabled = boolean
    # button_15.enabled = boolean

def CreateAddShapefile():
    global wcpsfolder
    global dataname
    global ps2proj
    
    # PS:2 spatial reference
    spatialRef = arcpy.SpatialReference()
    spatialRef.loadFromString(ps2proj)

    # Create shapefile
    arcpy.CreateFeatureclass_management(wcpsfolder, dataname + ".shp", "POINT", "", "DISABLED", "DISABLED", spatialRef)
    fullpath = os.path.join(wcpsfolder, dataname + ".shp")
    arcpy.AddField_management(fullpath, "Number", "SHORT", 4, "", "", "", "NULLABLE")
    arcpy.AddField_management(fullpath, "ProductId", "TEXT", "", "", 11)
    
    # Remove the layer again
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = arcpy.mapping.ListDataFrames(mxd,"*")[0]
    for lyr in arcpy.mapping.ListLayers(mxd, "", df):
        if lyr.name == dataname:
            arcpy.mapping.RemoveLayer(df, lyr)

    # Add the standard Numbers as FAKE points
    cursor = arcpy.da.InsertCursor(fullpath,("Number", "ProductId", "SHAPE@XY"))
    cursor.insertRow((-1, "", (0, 0)))
    cursor.insertRow((1, "", (0, 0)))
    cursor.insertRow((2, "", (0, 0)))
    cursor.insertRow((3, "", (0, 0)))
    cursor.insertRow((4, "", (0, 0)))
    cursor.insertRow((5, "", (0, 0)))
    cursor.insertRow((6, "", (0, 0)))
    cursor.insertRow((7, "", (0, 0)))
    cursor.insertRow((8, "", (0, 0)))
    cursor.insertRow((9, "", (0, 0)))
    cursor.insertRow((10, "", (0, 0)))
    del cursor
    
    # Apply the symbology from the .LYR
    spectralayer = arcpy.mapping.Layer(fullpath)
    # http://resources.arcgis.com/en/help/main/10.1/index.html#/Essential_Python_add_in_concepts/014p0000001p000000/
    symbologylayerpath = os.path.join(os.path.dirname(__file__), dataname + '.lyr')
    arcpy.ApplySymbologyFromLayer_management(spectralayer, symbologylayerpath)
    
    # Remove the FAKE points again
    with arcpy.da.UpdateCursor(fullpath, ["Number", "ProductId", "SHAPE@XY"]) as cursor:
        for row in cursor:
            cursor.deleteRow()
            
    # Refresh MXD
    arcpy.RefreshTOC()
    arcpy.RefreshActiveView()

def LoadFootprintLayer():
    global crismfootprintlayer
    global wcpsfolder
    
    # Download footprint shapefile if it doesn't exist
    footprints = os.path.join(wcpsfolder, crismfootprintlayer + ".shp")
    if not arcpy.Exists(footprints):
        url = 'http://es1.planetserver.eu/data/' + crismfootprintlayer + '.zip'
        zip = os.path.join(wcpsfolder, crismfootprintlayer + '.zip')
        try:
            handle = urllib2.urlopen(urllib2.Request(url))
            req = urllib2.urlopen(url)
            CHUNK = 16 * 1024
            with open(zip, 'wb') as fp:
                while True:
                    chunk = req.read(CHUNK)
                    if not chunk: break
                    fp.write(chunk)
            z = zipfile.ZipFile(zip)
            z.extractall(wcpsfolder)
            z.close()
            os.unlink(zip)
        except urllib2.HTTPError, e:
            pythonaddins.MessageBox("The PlanetServer CRISM shapefile couldn't be downloaded! Please try again later. If the problem persists please contact the PlanetServer developers.", 'Warning', 0)

    # Load footprint shapefile
    if arcpy.Exists(footprints):
        if LayerInTOC(crismfootprintlayer) != 2:
            LoadLayer(crismfootprintlayer)
    
def LayerInTOC(name):
    global wcpsfolder
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = arcpy.mapping.ListDataFrames(mxd,"*")[0]
    exist = 0
    for lyr in arcpy.mapping.ListLayers(mxd, "", df):
        if lyr.name == name:
            exist = 1
            if os.path.dirname(lyr.dataSource) == wcpsfolder:
                exist = 2
    return exist

def RemoveFromTOC(name):    
    # Remove the layer from the TOC if it would exist
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = arcpy.mapping.ListDataFrames(mxd,"*")[0]
    for lyr in arcpy.mapping.ListLayers(mxd, "", df):
        if lyr.name == name:
            arcpy.mapping.RemoveLayer(df, lyr)

def LoadLayer(name):
    global wcpsfolder
    
    # Apply the symbology from the .LYR
    layer = arcpy.mapping.Layer(os.path.join(wcpsfolder, name + ".shp"))
    # http://resources.arcgis.com/en/help/main/10.1/index.html#/Essential_Python_add_in_concepts/014p0000001p000000/
    symbologylayerpath = os.path.join(os.path.dirname(__file__), name + '.lyr')
    arcpy.ApplySymbologyFromLayer_management(layer, symbologylayerpath)
    
    # Refresh MXD
    arcpy.RefreshTOC()
    arcpy.RefreshActiveView()

def UpdateShapefile(count, pid, x, y):
    global wcpsfolder
    global dataname
    
    sfpath = os.path.join(wcpsfolder, dataname + '.shp')
    exist = 0
    for row in arcpy.da.SearchCursor(sfpath, "Number", """"ProductId" = '""" + pid + """'"""):
        if row[0] == count:
            exist = 1
    if exist == 0:
        cursor = arcpy.da.InsertCursor(sfpath,("Number", "ProductId", "SHAPE@XY"))
        cursor.insertRow((count, pid, (x, y)))
        del cursor
    else:
        with arcpy.da.UpdateCursor(sfpath, ["Number", "ProductId", "SHAPE@XY"], """"Number" = """ + str(count) + """ AND "ProductId" = '""" + pid + """'""") as cursor:
            for row in cursor:
                row[0] = count
                row[1] = pid
                row[2] = (x, y)
                cursor.updateRow(row)

def RemoveOutliers(list):
    # check for outliers:
    smooth = []
    mean = np.mean(filter(None, list))
    std_dev = np.std(filter(None, list))
    for s in list:
        if s != None:
            if abs(s - mean) <= 2 * std_dev:
                smooth.append(s)
            else:
                smooth.append(None)
        else:
            smooth.append(None)
    return smooth

def OnClickDiagram(event):
    global banddepthdata
    global enable_bd
    if enable_bd:
        if len(banddepthdata) < 2:
            banddepthdata.append(event.xdata)
        else:
            banddepthdata.append(event.xdata)
            # check s or l
            irvnir = 0
            #pythonaddins.MessageBox(str(irvnir),"click")
            if banddepthdata[0] > min(wavelength['l']):
                if banddepthdata[1] > min(wavelength['l']):
                    if banddepthdata[2] > min(wavelength['l']):
                        irvnir = 'l'
            #pythonaddins.MessageBox(str(irvnir),"click")
            if banddepthdata[0] < max(wavelength['s']):
                if banddepthdata[1] < max(wavelength['s']):
                    if banddepthdata[2] < max(wavelength['s']):
                        irvnir = 's'
            #pythonaddins.MessageBox(str(irvnir),"click")
            if irvnir in ['s','l']:
                string = wcps_banddepth(banddepthdata[0], banddepthdata[1], banddepthdata[2], irvnir)
                #pythonaddins.MessageBox(string, "string")
                name = "banddepth_" + str(round(banddepthdata[0], 2)) + "_" + str(round(banddepthdata[1], 2)) + "_" + str(round(banddepthdata[2], 2))
                get_wcpsimage(name, [string], irvnir)
                #pythonaddins.MessageBox(str(irvnir),"click")
            banddepthdata = []
            #pythonaddins.MessageBox(str(banddepthdata),"click")
        #pythonaddins.MessageBox('button=%d, x=%d, y=%d, xdata=%f, ydata=%f'%(event.button, event.x, event.y, event.xdata, event.ydata),"click")
        #pythonaddins.MessageBox(str(banddepthdata),"click")

def checkEqual(iterator):
    # http://stackoverflow.com/questions/3844801/check-if-all-elements-in-a-list-are-identical
    return len(set(iterator)) <= 1

def get_crism_info():
    global crismfootprintlayer
    pids = []
    metadata = {}
    for row in arcpy.SearchCursor(crismfootprintlayer):
        productid = row.ProductId.lower()
        pids.append(productid)
        xmin = float(row.XMIN)
        xmax = float(row.XMAX)
        ymin = float(row.YMIN)
        ymax = float(row.YMAX)
        width = float(row.WIDTH)
        height = float(row.HEIGHT)
        metadata[productid] = [xmin,xmax,ymin,ymax,width,height]
    return pids, metadata

def xy2imagecrs(x, y, metadata):
    [xmin,xmax,ymin,ymax,width,height] = metadata
    imx = (x - xmin) * (width / (xmax - xmin))
    imy = (ymax - y) * (height / (ymax - ymin)) # The WCPS CRS:1 origin is top-left, so reverse order.
    imx = int(math.floor(imx))
    imy = int(math.floor(imy))
    return imx, imy

def inextent(x, y, metadata):
    [xmin,xmax,ymin,ymax,width,height] = metadata
    if x > xmin and x < xmax and y > ymin and y < ymax:
        return True
    else:
        return False

def getbin(data):
    global nodata_value
    data = data.replace("{","")
    data = data.replace("}","")
    data = data.replace("\"","")
    
    # for n,i in enumerate(data):
        # if i == str(nodata_value):
            # data[n] = None
        # elif i == '0':
            # data[n] = None
                        
    binlist = data.split(",")
    spectrabin = []
    k = 0
    for i in range(0, len(binlist)):
        temp = binlist[i].split(" ")
        numbers = []
        count = 0
        for j in range(0, len(temp)):
            if temp[j] == str(nodata_value) or temp[j] == '0':
                numbers.append(None)
                count += 1
            else:
                try:
                    numbers.append(float(temp[j]))
                except ValueError:
                    print data
                    return -1
        if count != len(numbers):
            spectrabin.append(numbers)
            k += 1
    if k > 0:
        return spectrabin
    else:
        return -1

def avgbin(spectrabin):
    numbers = []
    for i in range(0, len(spectrabin[0])):
        sum = 0
        count = len(spectrabin)
        for j in range(0, len(spectrabin)):
            if spectrabin[j][i] == None:
                count -= 1
            else:
                sum = sum + spectrabin[j][i]
        try:
            number = float(sum) / float(count)
            if math.isnan(number):
                number = None
        except:
            number = None
        numbers.append(number)
    return numbers

def nm2band(mm, irvnir):
    # Similar as mro_crism_lookupwv.pro
    data = wavelength[irvnir]
    bandnr = 0
    #mm = nm / 1000
    for j in range(0, len(data)):
        if data[j] >= mm:
            if bandnr == 0:
                bandnr = j
    # Take band with minimum distance from mm:
    if abs(data[(bandnr - 1)] - mm) <= abs(data[bandnr] - mm):
        bandnr = bandnr - 1
    return 'data.' + str(bandnr)

def nm2wavelength(mm, irvnir) :
    # Similar as mro_crism_lookupwv.pro
    data = wavelength[irvnir]
    bandnr = 0
    #mm = nm / 1000
    for j in range(0, len(data)):
        if data[j] >= mm:
            if bandnr == 0:
                bandnr = j
    # Take band with minimum distance from mm:
    if abs(data[(bandnr - 1)] - mm) <= abs(data[bandnr] - mm):
        return data[bandnr - 1]
    else:
        return data[bandnr]

def wcps_banddepth(low, center, high, irvnir):
    RLow = nm2band(low, irvnir)
    WL = nm2wavelength(low, irvnir)
    RCenter = nm2band(center, irvnir)
    WC = nm2wavelength(center, irvnir)
    RHigh = nm2band(high, irvnir)
    WH = nm2wavelength(high, irvnir)
    a = (WC-WL)/(WH-WL)
    b = 1 - a
    string = '(1 - (' + str(RCenter) + ' / ((' + str(b) + ' * ' + str(RLow) + ') + (' + str(a) + ' * ' + str(RHigh) + '))))'
    return string

def get_wcpsimage(name, bandmathdata, irvnir):
    global pswcpsurl
    global ps2proj
    global crismfootprintlayer
    pids = []
    metadata = {}
    mxd = arcpy.mapping.MapDocument("CURRENT")
    layers = arcpy.mapping.ListLayers(mxd)
    for layer in layers:
        if layer.name == crismfootprintlayer:
            for row in arcpy.SearchCursor(layer):
                productid = row.ProductId.lower()
                pids.append(productid)
                xmin = float(row.XMIN)
                xmax = float(row.XMAX)
                ymin = float(row.YMIN)
                ymax = float(row.YMAX)
                width = float(row.WIDTH)
                height = float(row.HEIGHT)
                metadata[productid] = [xmin,xmax,ymin,ymax,width,height]
    for productid in pids:
        if irvnir + '_trr' in productid:
            collection = productid + '_1_01'
            
            if len(bandmathdata) == 1:
                # greyscale
                wcpsquery = 'for data in ( ' + collection + ' ) return encode( (float) ' + bandmathdata[0] + ', "GTiff", "NODATA=65535;")'
            elif len(bandmathdata) == 3:
                red = bandmathdata[0]
                green = bandmathdata[1]
                blue = bandmathdata[2]
                wcpsquery = 'for data in ( ' + collection + ' ) return encode( {red: (float) ' + red + '; green: (float) ' + green + '; blue: (float) ' + blue + '}, "GTiff", "NODATA=65535;65535;65535" )'
            
            values = {'query' : wcpsquery}
            data = urllib.urlencode(values)
            req = urllib2.Request(pswcpsurl, data)
            response = urllib2.urlopen(req)

            global wcpsfolder
            wcpstif = os.path.join(wcpsfolder, productid + '_' + name + '.tif')

            # download
            CHUNK = 16 * 1024
            with open(wcpstif, 'wb') as fp:
                while True:
                    chunk = response.read(CHUNK)
                    if not chunk: break
                    fp.write(chunk)
            
            # tfw
            [xmin,xmax,ymin,ymax,width,height] = metadata[productid]
            res = abs(xmax - xmin) / width
            tfw = open(wcpstif[:-4] + ".tfw","w")
            tfw.write("%s\n0\n0\n-%s\n%s\n%s\n" %(res,res,xmin,ymax))
            tfw.close()
            
            if os.path.exists(wcpstif):
                # Georef
                arcpy.DefineProjection_management(wcpstif, ps2proj)
            else:
                print "Unsuccessful download: " + wcpstif
                # alert window?
            
            # Add to ArcMap
            #df = arcpy.mapping.ListDataFrames(mxd)[0]
            #result = arcpy.MakeRasterLayer_management(wcpstif, collection)
            #layer = result.getOutput(0)
            #arcpy.mapping.AddLayer(df, layer, 'TOP')
                    
            # Refresh MXD
            #arcpy.RefreshTOC()
            #arcpy.RefreshActiveView()

# def create_crism_dict(list):
    # obslist = []

    # for i in list:
        # if not i[:11] in obslist:
            # obslist.append(i[:11])

    # dict = {}
    # for i in obslist:
        # temp = []
        # for j in list:
            # if i in j:
                # temp.append(j)

        # dict[i] = temp

    # return dict

def check_selected_crism(list):
    obslist = []

    for i in list:
        if not i[:11] in obslist:
            obslist.append(i[:11])
    
    if len(obslist) > 1:
        pythonaddins.MessageBox("Please select the IR and/or VNIR of one observation", "Warning")
        return -1
    else:
        return list
    
class MatplotlibWidget(FigureCanvas):
    """
    MatplotlibWidget inherits PySide.QtGui.QWidget
    and matplotlib.backend_bases.FigureCanvasBase
    
    Options: option_name (default_value)
    -------    
    parent (None): parent widget
    title (''): figure title
    xlabel (''): X-axis label
    ylabel (''): Y-axis label
    xlim (None): X-axis limits ([min, max])
    ylim (None): Y-axis limits ([min, max])
    xscale ('linear'): X-axis scale
    yscale ('linear'): Y-axis scale
    width (4): width in inches
    height (3): height in inches
    dpi (100): resolution in dpi
    hold (False): if False, figure will be cleared each time plot is called
    
    Widget attributes:
    -----------------
    figure: instance of matplotlib.figure.Figure
    axes: figure axes
    
    Example:
    -------
    self.widget = MatplotlibWidget(self, yscale='log', hold=True)
    from numpy import linspace
    x = linspace(-10, 10)
    self.widget.axes.plot(x, x**2)
    self.wdiget.axes.plot(x, x**3)
    """
    def __init__(self, parent=None, title='', xlabel='', ylabel='',
                 xlim=None, ylim=None, xscale='linear', yscale='linear',
                 width=5, height=5, dpi=100, hold=True, X = None, Y = None, Z = None):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.figure.add_subplot(111)
        self.axes.set_title(title)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        if xscale is not None:
            self.axes.set_xscale(xscale)
        if yscale is not None:
            self.axes.set_yscale(yscale)
        if xlim is not None:
            self.axes.set_xlim(*xlim)
        if ylim is not None:
            self.axes.set_ylim(*ylim)
        self.axes.hold(hold)

        if X is not None:
          self.X = X
        if Y is not None:
          self.Y = Y
        if Z is not None:
          self.Z = Z

        FigureCanvas.__init__(self, self.figure)
        if parent is not None:
          self.setParent(parent)

        #Canvas.setSizePolicy(self, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def sizeHint(self):
        w, h = self.get_width_height()
        return QtCore.QSize(w, h)

    def minimumSizeHint(self):
        return QtCore.QSize(10, 10)

class MatplotlibInteractiveWidget(QtGui.QWidget):
    """
    A subclass of QtGui.QWidget, the MatplotlibInteractiveWidget is a container
    for two child widgets: a MatplotlibWidget and a NavigationToolbar.  The
    navigation toolbar allows the user to edit the plot parameters such as 
    title, x/y scale, labels, etc. from the GUI, a capability that is not
    present in the bare MatplotlibWidget.  The interactive widget is similar
    to the window that the user sees when calling matplotlib.show()
    """
    def __init__(self, parent = None):
        """
        Initializer for the MatplotlibInteractiveWidget.  Currently only takes
        an optional parameter for a parent widget.
        """
        super(MatplotlibInteractiveWidget, self).__init__()
        self.main_layout = QtGui.QVBoxLayout()
        self.plot_widget = MatplotlibWidget()
        self.plot_widget.mpl_connect('button_press_event', OnClickDiagram)
        self.navigation_toolbar = NavigationToolbar(self.plot_widget, self)
        self.main_layout.addWidget(self.plot_widget)
        self.main_layout.addWidget(self.navigation_toolbar)
        self.setLayout(self.main_layout)
        # https://qt.gitorious.org/pyside/pyside-examples/source/060dca8e4b82f301dfb33a7182767eaf8ad3d024:examples/widgets/windowflags.py
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("CRISM Spectral Analysis")
        
        clearbutton = QtGui.QPushButton('Clear diagram', self)
        clearbutton.move(10, 10)
        clearbutton.clicked.connect(self.cleardiagram)
        
        bdbutton = QtGui.QPushButton('Band depth', self)
        bdbutton.move(120, 10)
        bdbutton.clicked.connect(self.banddepth)
        
    def cleardiagram(self):
        self.get_axes().clear()
        self.get_figure().canvas.draw()
        
    def banddepth(self):
        global banddepthdata
        global enable_bd
        if enable_bd:
            enable_bd = False
        else:
            banddepthdata = []
            enable_bd = True

    def get_axes(self):
        """Returns the axes of the child MatplotlibWidget
        :returns: @todo

        """
        return self.plot_widget.axes
    def get_figure(self):
        """Returns the axes of the child MatplotlibWidget
        :returns: @todo

        """
        return self.plot_widget.figure

def DrawDiagram(pid):
    global main_widget
    global spectradict
    global colors
    global useoffset
    global crismtype
    # global enable_bd
    # if enable_bd:
        # bd = "on"
    # else:
        # bd = "off"
    
    if spectradict.get(pid, 0) == 0:
        # No data available yet
        pass
    else:
        yspectra = 0
        if spectradict[pid].get("-1", 0) != 0:
            yspectra = spectradict[pid]["-1"]
            
        # Empty diagram
        main_widget.get_axes().clear()
        main_widget.get_figure().canvas.draw()
        
        if useoffset == 1:
            yranges = []
            for count in spectradict[pid].keys():
                if count not in ["-1", "count"]:
                    [graphxlist, graphylist] = spectradict[pid][count]
                    if len(graphylist) == 1:
                        graphy = graphylist[0]
                    else:
                        graphy = graphylist[0] + graphylist[1]
                    min = 9999
                    max = -9999
                    for value in graphy:
                        if value != None:
                            if value > max:max = value
                            if value < min:min = value
                    yrange = max - min
                    yranges.append(yrange)
            offset = np.mean(yranges)
                    
        for count in spectradict[pid].keys():
            if count not in ["-1", "count"]:
                [graphxlist, graphylist] = spectradict[pid][count]
                
                # If present calculate ratio'ed spectra
                if yspectra != 0:
                    i = 0
                    ratioedlist = []
                    for item in graphylist:
                        ratiospectrum = []
                        j = 0
                        for xvalue in item:
                            yvalue = yspectra[i][j]
                            if xvalue != None and yvalue != None:
                                ratiovalue = float(xvalue) / float(yvalue)
                                ratiospectrum.append(ratiovalue)
                            else:
                                ratiospectrum.append(None)
                            j += 1
                        ratioedlist.append(ratiospectrum)
                        i += 1
                    graphylist = ratioedlist
                
                # VNIR/IR only or both?
                if len(graphxlist) == 1:
                    graphx = graphxlist[0]
                    graphy = graphylist[0]
                else:
                    if crismtype == "1 - 2.6":
                        # only look at the IR
                        maxx = np.amax(np.array(graphxlist[0]))
                        if maxx > 2:
                            graphx = graphxlist[0]
                            graphy = graphylist[0]
                        else:
                            graphx = graphxlist[1]
                            graphy = graphylist[1]
                    else:
                        graphx = graphxlist[0] + graphxlist[1]
                        graphy = graphylist[0] + graphylist[1]
                
                if useoffset == 1:
                    offsetgraphy = []
                    for value in graphy:
                        if value != None:
                            offsetgraphy.append(value + (offset * (float(count) - 1)))
                        else:
                            offsetgraphy.append(None)
                    graphy = offsetgraphy
                
                # plotting
                ax = main_widget.get_axes()
                ax.plot(graphx, graphy, color = colors[int(count)]) #, label = r'$%s,%s$' % (x,y)) #x,y,label = r'$\mathrm{Sinc} \left ( x \right )$')
                ax.set_xlabel(r'$wavelength$')
                ax.set_ylabel(r'$I$')
                ax.set_title(r'Spectral Diagram')
                
                # Set the range
                if len(graphxlist) == 1:
                    minx = np.amin(np.array(graphx))
                    maxx = np.amax(np.array(graphx))
                    if maxx > 2 and crismtype == "1 - 2.6":
                        # Single IR (haven't seen this yet)
                        ax.set_xlim([1, 2.6])
                    else:
                        # Single VNIR
                        ax.set_xlim([minx, maxx])
                else:
                    if crismtype == "Both":
                        ax.set_xlim([0.4, 3.8])
                    elif crismtype == "VNIR":
                        ax.set_xlim([0.4, 1])
                    elif crismtype == "IR":
                        ax.set_xlim([1, 3.8])
                    elif crismtype == "1 - 2.6":
                        ax.set_xlim([1, 2.6])

                # http://stackoverflow.com/questions/4700614/how-to-put-the-legend-out-of-the-plot
                #box = ax.get_position()
                #ax.set_position([box.x0, box.y0, box.width * 0.95, box.height])
                #ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
                
                # http://stackoverflow.com/questions/15876011/add-information-to-matplotlib-navigation-toolbar-status-bar
                ax.format_coord = lambda x, y: 'x=%1.4f y=%1.4f, count=%s'%(x, y, spectradict[pid]["count"])
                main_widget.get_figure().canvas.draw()

                main_widget.show()

## this crashes ArcGIS
# def get_folder_name():
    # application = QtGui.QApplication(sys.argv)
    # folderdialog = QtGui.QFileDialog()
    # folderdialog.setFileMode(QtGui.QFileDialog.Directory)
    # folderdialog.setOption(QtGui.QFileDialog.ShowDirsOnly)
    # folderdialog.exec_()
    # return folderdialog.selectedFiles()[0]

# http://resources.arcgis.com/en/help/main/10.1/index.html#/Combo_Box/014p00000024000000/
class ComboBoxClass1(object):
    """Implementation for ArcGISPlanetServer_addin.combobox_1 (ComboBox)"""
    def __init__(self):
        global crismtype
        global enable_addin
        self.value = crismtype
        self.items = ["IR", "VNIR", "Both", "1 - 2.6"]
        self.editable = True
        self.enabled = enable_addin
        self.dropdownWidth = 'WWWWWW'
        self.width = 'WWWWWW'
    def onSelChange(self, selection):
        global crismtype
        global main_widget
        crismtype = selection
        pids, metadata = get_crism_info()
        # do a check that either 1 or 2 features are selected and if 2, they only differ in 's' and 'l'
        pids = check_selected_crism(pids)
        if pids == -1:
            pass
        else:
            DrawDiagram(pids[0][:11])

class ComboBoxClass2(object):
    """Implementation for ArcGISPlanetServer_addin.combobox_2 (ComboBox)"""
    def __init__(self):
        global binvalue
        global enable_addin
        self.value = "%sx%s" % (binvalue, binvalue)
        self.items = ["1x1", "3x3", "5x5"]
        self.editable = True
        self.enabled = enable_addin
        self.dropdownWidth = 'WWWWWW'
        self.width = 'WWWWWW'
    def onSelChange(self, selection):
        global binvalue
        binvalue = int(selection[0])
        pass

# class ButtonClass0(object):
    # """Implementation for ArcGISPlanetServer_addin.button_0 (Button)"""
    # def __init__(self):
        # self.enabled = True
        # self.checked = False

    # def onClick(self):
        # global crismtype
        # combobox_1.value = crismtype
        # combobox_1.items = ["IR", "VNIR", "Both"]
        # combobox_1.editable = True
        # combobox_1.refresh()
        # combobox_1.editable = False
        # print crismtype

class ButtonClass1(object):
    """Implementation for ArcGISPlanetServer_addin.button_1 (Button)"""
    def __init__(self):
        global enable_addin
        self.enabled = enable_addin
        self.checked = False

    def onClick(self):
        global sp
        name = 'olindex2'
        get_wcpsimage(name, [sp[name]], 'l')
        
class ButtonClass2(object):
    """Implementation for ArcGISPlanetServer_addin.button_2 (Button)"""
    def __init__(self):
        global enable_addin
        self.enabled = enable_addin
        self.checked = False

    def onClick(self):
        global sp
        name = 'bd1900r'
        get_wcpsimage(name, [sp[name]], 'l')
        pass

class ButtonClass3(object):
    """Implementation for ArcGISPlanetServer_addin.button_3 (Button)"""
    def __init__(self):
        global enable_addin
        self.enabled = enable_addin
        self.checked = False

    def onClick(self):
        global sp
        name = 'bd2100'
        get_wcpsimage(name, [sp[name]], 'l')
        pass

class ButtonClass4(object):
    """Implementation for ArcGISPlanetServer_addin.button_4 (Button)"""
    def __init__(self):
        global enable_addin
        self.enabled = enable_addin
        self.checked = False

    def onClick(self):
        global sp
        name = 'bd2210'
        get_wcpsimage(name, [sp[name]], 'l')
        pass

class ButtonClass5(object):
    """Implementation for ArcGISPlanetServer_addin.button_5 (Button)"""
    def __init__(self):
        global enable_addin
        self.enabled = enable_addin
        self.checked = False

    def onClick(self):
        global sp
        name = 'd2300'
        get_wcpsimage(name, [sp[name]], 'l')
        pass

class ButtonClass6(object):
    """Implementation for ArcGISPlanetServer_addin.button_6 (Button)"""
    def __init__(self):
        global enable_addin
        self.enabled = enable_addin
        self.checked = False

    def onClick(self):
        global sp
        name = 'sindex'
        get_wcpsimage(name, [sp[name]], 'l')
        pass

class ButtonClass7(object):
    """Implementation for ArcGISPlanetServer_addin.button_7 (Button)"""
    def __init__(self):
        global enable_addin
        self.enabled = enable_addin
        self.checked = False

    def onClick(self):
        global sp
        name = 'bd2500'
        get_wcpsimage(name, [sp[name]], 'l')
        pass

class ButtonClass8(object):
    """Implementation for ArcGISPlanetServer_addin.button_8 (Button)"""
    def __init__(self):
        global enable_addin
        self.enabled = enable_addin
        self.checked = False

    def onClick(self):
        global sp
        name = 'd2300*bd2500'
        get_wcpsimage(name, [sp['d2300'] + ' * ' + sp['bd2500']], 'l')
        pass
        
class ToolClass1(object):
    """Implementation for ArcGISPlanetServer_addin.tool_1 (Tool)"""
    def __init__(self):
        global main_widget
        global enable_addin
        global application
        self.enabled = enable_addin
        #self.shape = "NONE" # Can set to "Line", "Circle" or "Rectangle" for interactive shape drawing and to activate the onLine/Polygon/Circle event sinks.
        self.cursor = 3
        try:
            application = QtGui.QApplication(sys.argv)
        except:
            application = QtGui.QApplication.instance()
        main_widget = MatplotlibInteractiveWidget()
        
    def onMouseDownMap(self, x, y, button, shift):
        #global data
        global pswcpsurl
        global wavelength
        global binvalue
        global spectradict
        global colors
        global wcpsfolder
        global dataname
        
        self.x = x
        self.y = y
    
        pids, metadata = get_crism_info()
        # do a check that either 1 or 2 features are selected and if 2, they only differ in 's' and 'l'
        pids = check_selected_crism(pids)
        if pids == -1:
            pass
        else:
            graphxlist = []
            graphylist = []
            for productid in pids:
                if inextent(x,y,metadata[productid]):
                    imx, imy = xy2imagecrs(x,y,metadata[productid])
                    i = math.floor(binvalue / 2)
                    binxplus = int(imx + i)
                    binxmin = int(imx - i)
                    binyplus = int(imy + i)
                    binymin = int(imy - i)

                    collection = productid + '_1_01'
                    wcpsquery = 'for data in ( %s ) return encode( (data[E:"CRS:1"(%s:%s),N:"CRS:1"(%s:%s)]), "csv")' % (collection, binxmin, binxplus, binymin, binyplus)
                    print wcpsquery
                    values = {'query' : wcpsquery}
                    data = urllib.urlencode(values)
                    try:
                        req = urllib2.Request(pswcpsurl, data)
                        response = urllib2.urlopen(req)
                        data = response.read()
                        spectrabin = getbin(data)
                    except URLError, e:
                        print e.reason
                        spectrabin = -1

                    # check if data is str or filled with None
                    # if not checkEqual(data):
                        # if not isinstance(data[0], basestring):
                    if spectrabin != -1:
                        graphxlist.append(wavelength[productid[20]])
                        graphylist.append(RemoveOutliers(avgbin(spectrabin)))
            if graphxlist != []:
                pid = pids[0][:11]
                
                # Initialize spectradict
                if spectradict.get(pid, 0) == 0:
                    spectradict[pid] = {}
                
                # How many spectra have been collected so far?
                if spectradict[pid].get("count", 0) == 0:
                    spectradict[pid]["count"] = 1
                    count = 1
                else:
                    value = int(spectradict[pid]["count"])
                    # colors length is 11 because of extra ratio, therefore len(colors) - 1
                    if value == len(colors) - 1:
                        count = 1
                    else:
                        count = value + 1
                    spectradict[pid]["count"] = count
                
                # Add the spectra to spectradict
                spectradict[pid][str(count)] = [graphxlist, graphylist]
                
                # Save shapefile and JSON
                UpdateShapefile(count, pid, x, y)
                with open(os.path.join(wcpsfolder, dataname + '.json'), 'wb') as fp:
                    json.dump(spectradict, fp)
                    
                # Draw or redraw the diagram
                DrawDiagram(pid)
                    
                # Refresh MXD
                arcpy.RefreshTOC()
                arcpy.RefreshActiveView()

class ToolClass2(object):
    """Implementation for ArcGISPlanetServer_addin.tool_2 (Tool)"""
    def __init__(self):
        global enable_addin
        self.enabled = enable_addin
        #self.shape = "NONE" # Can set to "Line", "Circle" or "Rectangle" for interactive shape drawing and to activate the onLine/Polygon/Circle event sinks.
        self.cursor = 3
        #application = QtGui.QApplication(sys.argv)
        #main_widget = MatplotlibInteractiveWidget()
        
    def onMouseDownMap(self, x, y, button, shift):
        #global data
        global pswcpsurl
        global wavelength
        global binvalue
        global spectradict
        global wcpsfolder
        global dataname
        
        self.x = x
        self.y = y
        #crs = 'http://kahlua.eecs.jacobs-university.de:8080/def/crs/PS/0/2/'
    
        pids, metadata = get_crism_info()
        # do a check that either 1 or 2 features are selected and if 2, they only differ in 's' and 'l'
        pids = check_selected_crism(pids)
        if pids == -1:
            pass
        else:
            yspectra = []
            for productid in pids:
                if inextent(x,y,metadata[productid]):
                    imx, imy = xy2imagecrs(x,y,metadata[productid])
                    i = math.floor(binvalue / 2)
                    binxplus = int(imx + i)
                    binxmin = int(imx - i)
                    binyplus = int(imy + i)
                    binymin = int(imy - i)

                    collection = productid + '_1_01'
                    wcpsquery = 'for data in ( %s ) return encode( (data[E:"CRS:1"(%s:%s),N:"CRS:1"(%s:%s)]), "csv")' % (collection, binxmin, binxplus, binymin, binyplus)
                    values = {'query' : wcpsquery}
                    data = urllib.urlencode(values)
                    try:
                        req = urllib2.Request(pswcpsurl, data)
                        response = urllib2.urlopen(req)
                        data = response.read()
                        spectrabin = getbin(data)
                    except URLError, e:
                        print e.reason
                        spectrabin = -1

                    # check if data is str or filled with None
                    # if not checkEqual(data):
                        # if not isinstance(data[0], basestring):
                    if spectrabin != -1:
                        yspectra.append(RemoveOutliers(avgbin(spectrabin)))
                        
            spectradict[pids[0][:11]]["-1"] = yspectra
            
            # Draw or redraw the diagram
            DrawDiagram(pids[0][:11])
            
            # Update shapefile and JSON
            UpdateShapefile(-1, pids[0][:11], x, y)
            with open(os.path.join(wcpsfolder, dataname + '.json'), 'wb') as fp:
                json.dump(spectradict, fp)
                
            # Refresh MXD
            arcpy.RefreshTOC()
            arcpy.RefreshActiveView()

class ButtonClass9(object):
    """Implementation for ArcGISPlanetServer_addin.button_9 (Button)"""
    def __init__(self):
        self.enabled = False
        self.checked = False

    def onClick(self):
        global ps2proj
        global crismfootprintlayer
        arcpy.SelectLayerByLocation_management(crismfootprintlayer, 'COMPLETELY_CONTAINS', 'mask_test')
        pids, metadata = get_crism_info()
        list = arcpy.CopyFeatures_management("mask_test", arcpy.Geometry())
        # only expect one polygon:
        mask = list[0]
        spatialRef = arcpy.SpatialReference()
        spatialRef.loadFromString(ps2proj)
        ps2mask = mask.projectAs(spatialRef)
        wkt = ps2mask.WKT
        #wkt.replace("MULTIPOLYGON", "POLYGON")
        
        makemaskurl = "http://es1.planetserver.eu/cgi-bin/makemask.cgi?"
        for productid in pids:
            if "l_" in productid:
                [xmin,xmax,ymin,ymax,width,height] = metadata[productid]
                res = abs(xmax - xmin) / width
                values = {'res': res,
                          'xmin': xmin,
                          'xmax': xmax,
                          'ymin': ymin,
                          'ymax': ymax,
                          'ncols': width,
                          'nrows': height,
                          'wkt': wkt}
                data = urllib.urlencode(values)
                req = urllib2.Request(makemaskurl, data)
                response = urllib2.urlopen(req)
                data = response.read()
        pass

class ButtonClass10(object):
    """Implementation for ArcGISPlanetServer_addin.button_10 (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False

    def onClick(self):
        global winenv
        global spectradict
        global wcpsfolder
        global dataname
        
        text = "<Please go to folder and click Save>"
        folder = pythonaddins.SaveDialog("Folder to save WCPS derived imagery", text, "")
        if folder == None:
            pythonaddins.MessageBox('You need to set a folder before the PlanetServer add-in will work!', 'Warning', 0)
        else:
            wcpsfolder = os.path.dirname(folder)
            winenv.setenv('WCPS_FOLDER', wcpsfolder)
            arcpy.env.workspace = wcpsfolder

            if not SpectraDataExist():
                # Create the shapefile + .JSON and add to map
                CreateAddShapefile()
                
                spectradict = {}
                with open(os.path.join(wcpsfolder, dataname + '.json'), 'wb') as fp:
                    json.dump(spectradict, fp)
            else:
                # Load the shapefile + .JSON and add to map
                button_11.onClick()
            
            LoadFootprintLayer()
            toggle_addin(True)
        
class ButtonClass11(object):
    """Implementation for ArcGISPlanetServer_addin.button_11 (Button)"""
    def __init__(self):
        global winenv
        if winenv.getenv('WCPS_FOLDER') == '':
            self.enabled = False
        else:
            self.enabled = True
        self.checked = False

    def onClick(self):
        global wcpsfolder
        global dataname
        global winenv
        global spectradict
        
        # Check if WCPS_FOLDER exists and dataname JSON and shapefile exist in wcpsfolder
        if winenv.getenv('WCPS_FOLDER') != '':
            wcpsfolder = winenv.getenv('WCPS_FOLDER')
            arcpy.env.workspace = wcpsfolder
            if SpectraDataExist():
                # Load spectradict
                with open(os.path.join(wcpsfolder, dataname + '.json'), 'rb') as fp:
                    spectradict = json.load(fp)
                
                if not LayerInTOC(dataname) == 2:
                    LoadLayer(dataname)
                    
                LoadFootprintLayer()
                toggle_addin(True)
                
                print "You can get access to the PlanetServer add-in:"
                print "from ps import *"
                print "or"
                print "import ps"
            else:
                choice = pythonaddins.MessageBox('The PlanetServer data has been removed from the earlier saved folder. Would you like to create and load new data?', 'No data in folder', 3)
                if choice == "Yes":
                    button_10.onClick()
        else:
            # New folder
            pass
        
class ButtonClass12(object):
    """Implementation for ArcGISPlanetServer_addin.button_12 (Button)"""
    def __init__(self):
        global enable_addin
        self.enabled = enable_addin
        self.checked = False

    def onClick(self):
        pids, metadata = get_crism_info()
        # do a check that either 1 or 2 features are selected and if 2, they only differ in 's' and 'l'
        pids = check_selected_crism(pids)
        if pids == -1:
            pass
        else:
            DrawDiagram(pids[0][:11])

class ButtonClass13(object):
    """Implementation for ArcGISPlanetServer_addin.button_13 (Button)"""
    def __init__(self):
        global enable_addin
        self.enabled = enable_addin
        self.checked = False

    def onClick(self):
        get_wcpsimage("ir_phy", [sp['d2300'],sp['bd2210'],sp['bd1900r']], 'l')

class ButtonClass14(object):
    """Implementation for ArcGISPlanetServer_addin.button_14 (Button)"""
    def __init__(self):
        global enable_addin
        self.enabled = enable_addin
        self.checked = False

    def onClick(self):
        # IR:233/78/13
        get_wcpsimage("ir_rgb", ['data.232', 'data.77', 'data.12'], 'l')
        # VNIR:54/37/27
        get_wcpsimage("vnir_rgb", ['data.53', 'data.36', 'data.26'], 's')

class ButtonClass15(object):
    """Implementation for ArcGISPlanetServer_addin.button_15 (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False

    def onClick(self):
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0] 
        wmslyrpath = os.path.join(os.path.dirname(__file__), 'PlanetServerWMS.lyr')
        wmslyr = arcpy.mapping.Layer(wmslyrpath)
        arcpy.mapping.AddLayer(df, wmslyr)

pswcpsurl = 'http://es1.planetserver.eu:8080/rasdaman/ows'
crs_ps1 = 'http://es1.planetserver.eu:8080/def/crs/PS/0/1/'
crs_ps2 = 'http://es1.planetserver.eu:8080/def/crs/PS/0/2/'
winenv = Win32Environment()
main_widget = ""
#data = ""
useoffset = 1

nodata_value = 65535
binvalue = 3
crismfootprintlayer = "mars_mro_crism_trdr_frthrlhrs07_c0a_planetserver"
spectradict = {}
crismtype = "Both"
dataname = 'PlanetServerSpectra'
ps2proj = 'PROJCS["Mars Equicylindrical clon=0",GEOGCS["GCS_Mars_2000_Sphere",DATUM["D_Mars_2000_Sphere",SPHEROID["Mars_2000_Sphere_IAU_IAG",3396190.0,0.0]],PRIMEM["Reference_Meridian",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Equidistant_Cylindrical"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",0.0],PARAMETER["Standard_Parallel_1",0.0],UNIT["Meter",1.0]]'
wcpsfolder = ''
banddepthdata = []
enable_addin = False
enable_bd = False

wavelength = {'l': [1.001350,1.007900,1.014450,1.021000,1.027550,1.034100,1.040650,1.047200,1.053750,1.060300,1.066850,1.073410,1.079960,1.086510,1.093070,1.099620,1.106170,1.112730,1.119280,1.125840,1.132390,1.138950,1.145510,1.152060,1.158620,1.165180,1.171730,1.178290,1.184850,1.191410,1.197970,1.204530,1.211090,1.217650,1.224210,1.230770,1.237330,1.243890,1.250450,1.257010,1.263570,1.270140,1.276700,1.283260,1.289830,1.296390,1.302950,1.309520,1.316080,1.322650,1.329210,1.335780,1.342340,1.348910,1.355480,1.362050,1.368610,1.375180,1.381750,1.388320,1.394890,1.401450,1.408020,1.414590,1.421160,1.427730,1.434310,1.440880,1.447450,1.454020,1.460590,1.467160,1.473740,1.480310,1.486880,1.493460,1.500030,1.506610,1.513180,1.519760,1.526330,1.532910,1.539480,1.546060,1.552640,1.559210,1.565790,1.572370,1.578950,1.585520,1.592100,1.598680,1.605260,1.611840,1.618420,1.625000,1.631580,1.638160,1.644740,1.651330,1.657910,1.664490,1.671070,1.677660,1.684240,1.690820,1.697410,1.703990,1.710580,1.717160,1.723750,1.730330,1.736920,1.743510,1.750090,1.756680,1.763270,1.769850,1.776440,1.783030,1.789620,1.796210,1.802800,1.809390,1.815980,1.822570,1.829160,1.835750,1.842340,1.848930,1.855520,1.862120,1.868710,1.875300,1.881900,1.888490,1.895080,1.901680,1.908270,1.914870,1.921460,1.928060,1.934650,1.941250,1.947850,1.954440,1.961040,1.967640,1.974240,1.980840,1.987430,1.994030,2.000630,2.007230,2.013830,2.020430,2.027030,2.033630,2.040240,2.046840,2.053440,2.060040,2.066640,2.073250,2.079850,2.086450,2.093060,2.099660,2.106270,2.112870,2.119480,2.126080,2.132690,2.139300,2.145900,2.152510,2.159120,2.165720,2.172330,2.178940,2.185550,2.192160,2.198770,2.205380,2.211990,2.218600,2.225210,2.231820,2.238430,2.245040,2.251650,2.258270,2.264880,2.271490,2.278100,2.284720,2.291330,2.297950,2.304560,2.311180,2.317790,2.324410,2.331020,2.337640,2.344260,2.350870,2.357490,2.364110,2.370720,2.377340,2.383960,2.390580,2.397200,2.403820,2.410440,2.417060,2.423680,2.430300,2.436920,2.443540,2.450170,2.456790,2.463410,2.470030,2.476660,2.483280,2.489900,2.496530,2.503120,2.509720,2.516320,2.522920,2.529510,2.536110,2.542710,2.549310,2.555910,2.562510,2.569110,2.575710,2.582310,2.588910,2.595510,2.602120,2.608720,2.615320,2.621920,2.628530,2.635130,2.641740,2.648340,2.654950,2.661550,2.668160,2.674760,2.681370,2.687980,2.694580,2.701190,2.760680,2.767290,2.773900,2.780520,2.787130,2.793740,2.800350,2.806970,2.813580,2.820200,2.826810,2.833430,2.840040,2.846660,2.853280,2.859890,2.866510,2.873130,2.879750,2.886360,2.892980,2.899600,2.906220,2.912840,2.919460,2.926080,2.932700,2.939320,2.945950,2.952570,2.959190,2.965810,2.972440,2.979060,2.985680,2.992310,2.998930,3.005560,3.012180,3.018810,3.025440,3.032060,3.038690,3.045320,3.051950,3.058570,3.065200,3.071830,3.078460,3.085090,3.091720,3.098350,3.104980,3.111610,3.118250,3.124880,3.131510,3.138140,3.144780,3.151410,3.158040,3.164680,3.171310,3.177950,3.184580,3.191220,3.197850,3.204490,3.211130,3.217760,3.224400,3.231040,3.237680,3.244320,3.250960,3.257600,3.264240,3.270880,3.277520,3.284160,3.290800,3.297440,3.304080,3.310730,3.317370,3.324010,3.330660,3.337300,3.343950,3.350590,3.357240,3.363880,3.370530,3.377170,3.383820,3.390470,3.397120,3.403760,3.410410,3.417060,3.423710,3.430360,3.437010,3.443660,3.450310,3.456960,3.463610,3.470260,3.476920,3.483570,3.490220,3.496870,3.503530,3.510180,3.516840,3.523490,3.530150,3.536800,3.543460,3.550110,3.556770,3.563430,3.570080,3.576740,3.583400,3.590060,3.596720,3.603380,3.610040,3.616700,3.623360,3.630020,3.636680,3.643340,3.650000,3.656670,3.663330,3.669990,3.676650,3.683320,3.689980,3.696650,3.703310,3.709980,3.716640,3.723310,3.729980,3.736640,3.743310,3.749980,3.756650,3.763310,3.769980,3.776650,3.783320,3.789990,3.796660,3.803330,3.810000,3.816670,3.823350,3.830020,3.836690,3.843360,3.850040,3.856710,3.863390,3.870060,3.876730,3.883410,3.890080,3.896760,3.903440,3.910110,3.916790,3.923470,3.930150,3.936820,4.000000], 's' : [0.364620,0.371120,0.377620,0.384120,0.390620,0.397120,0.403620,0.410120,0.416620,0.423120,0.429630,0.436130,0.442630,0.449140,0.455640,0.462150,0.468650,0.475160,0.481670,0.488170,0.494680,0.501190,0.507700,0.514210,0.520720,0.527230,0.533740,0.540250,0.546760,0.553270,0.559780,0.566290,0.572810,0.579320,0.585830,0.592350,0.598860,0.605380,0.611890,0.618410,0.624920,0.631440,0.637960,0.644480,0.650990,0.657510,0.664030,0.670550,0.677070,0.683590,0.690110,0.696630,0.703160,0.709680,0.716200,0.722720,0.729250,0.735770,0.742300,0.748820,0.755350,0.761870,0.768400,0.774920,0.781450,0.787980,0.794510,0.801040,0.807560,0.814090,0.820620,0.827150,0.833680,0.840220,0.846750,0.853280,0.859810,0.866340,0.872880,0.879410,0.885950,0.892480,0.899020,0.905550,0.912090,0.918620,0.925160,0.931700,0.938240,0.944770,0.951310,0.957850,0.964390,0.970930,0.977470,0.984010,0.990550,0.997100,1.003640,1.010180,1.016720,1.023270,1.029810,1.036360,1.042900,1.049450,1.055990]}

colors = {-1: '#000000',
          1: '#00ff00',
          2: '#ffff00',
          3: '#00ffff',
          4: '#ffaa00',
          5: '#bb00ff',
          6: '#ff00c5',
          7: '#267300',
          8: '#004da8',
          9: '#ff0000',
          10: '#9c9c9c'}

sp = {'bd1900r': '(1 -(((data.138 + data.139 + data.140 + data.141 + data.142 + data.143)) / (data.131 + data.132 + data.133 + data.169 + data.170 + data.171 ) ))',
      'bd2100': '(1 - ( ( (data.170 + data.173 ) * 0.5 ) / ( (0.3778237893630837 * data.141) + (0.6221762106369163 * data.190) ) ))',
      'bd2210': '(1 - ( data.184 / ( 0.3530040053404536 * data.173 + 0.6469959946595464 * data.190 ) ))',
      'd2300': '(1 - ( ((data.196 / (data.124 + ((data.232 - data.124) / (2.52951 - 1.81598)) * (2.29133 - 1.81598))) + (data.200 / (data.124 + ((data.232 - data.124) / (2.52951 - 1.81598)) * (2.31779 - 1.81598))) + (data.202 / (data.124 + ((data.232 - data.124) / (2.52951 - 1.81598)) * (2.33102 - 1.81598)))) / ((data.170 / (data.124 + ((data.232 - data.124) / (2.52951 - 1.81598)) * (2.11948 - 1.81598))) + (data.178 / (data.124 + ((data.232 - data.124) / (2.52951 - 1.81598)) * (2.17233 - 1.81598))) + (data.184 / (data.124 + ((data.232 - data.124) / (2.52951 - 1.81598)) * (2.21199 - 1.81598)))) ))',
      'sindex': '(1 - ( (data.167 + data.212) / ( 2 * data.196) ))',
      'bd2500': '(1 - ( (data.228 + data.229) / ( data.234 + data.209 ) ))',
      'olindex2': '(((((((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)) * 1.054) + (((data.213 + data.212 + data.214) / 3) - (2.404 * ((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750))))) - ((data.8 + data.7 + data.9) / 3)) / ((((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)) * 1.054) + (((data.213 + data.212 + data.214) / 3) - (2.404 * ((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)))))) * 0.1) + (((((((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)) * 1.211) + (((data.213 + data.212 + data.214) / 3) - (2.404 * ((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750))))) - ((data.32 + data.31 + data.33) / 3)) / ((((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)) * 1.211) + (((data.213 + data.212 + data.214) / 3) - (2.404 * ((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)))))) * 0.1) + (((((((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)) * 1.329) + (((data.213 + data.212 + data.214) / 3) - (2.404 * ((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750))))) - ((data.50 + data.50 + data.51) / 3)) / ((((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)) * 1.329) + (((data.213 + data.212 + data.214) / 3) - (2.404 * ((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)))))) * 0.4) + (((((((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)) * 1.474) + (((data.213 + data.212 + data.214) / 3) - (2.404 * ((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750))))) - ((data.72 + data.71 + data.73) / 3)) / ((((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)) * 1.474) + (((data.213 + data.212 + data.214) / 3) - (2.404 * ((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)))))) * 0.4)'}

# Enabling tools/buttons/etc which are in a menu will not work if they are not pre-initialized
# http://forums.arcgis.com/threads/87894-Python-Add-in-puzzler-with-menus-on-a-toolbar
#combobox_1 = ComboBoxClass1()
#combobox_2 = ComboBoxClass2()
tool_1 = ToolClass1()
tool_2 = ToolClass2()
button_1 = ButtonClass1()
button_2 = ButtonClass2()
button_3 = ButtonClass3()
button_4 = ButtonClass4()
button_5 = ButtonClass5()
button_6 = ButtonClass6()
button_7 = ButtonClass7()
button_8 = ButtonClass8()
button_9 = ButtonClass9()
button_12 = ButtonClass12()
button_13 = ButtonClass13()
button_14 = ButtonClass14()
button_15 = ButtonClass15()

application = ""