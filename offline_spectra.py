import arcpy
import sys, time
##from osgeo import gdal
##from gdalconst import *

startTime = time.time()

# coordinates to get pixel values for
x = 2426138.926
y = -1180474.529
##
### register all of the drivers
##gdal.AllRegister()
##
### open the image
##ds = gdal.Open(r'F:\4Jessica\FelsicVolcanic\Area1Graben\hrl0000d025_07_if181l_trr3_CAT_scale_trial_p.img', GA_ReadOnly)
##if ds is None:
##    print 'Could not open image'
##    sys.exit(1)
##
### get image size
##rows = ds.RasterYSize
##cols = ds.RasterXSize
##
### get georeference info
##transform = ds.GetGeoTransform()
##x_origin = transform[0]
##y_origin = transform[3]
##pixel_width = transform[1]
##pixel_height = transform[5]
##
### compute pixel offset
##x_offset = int((x - x_origin) / pixel_width)
##y_offset = int((y - y_origin) / pixel_height)
##
### read data
##for i in range(ds.RasterCount):
##    band = ds.GetRasterBand(i + 1)
##    data = band.ReadAsArray(x_offset, y_offset, 1, 1)
##    print data[0,0]
##
##ds = None
##
##print 'script took', time.time() - startTime, 'seconds to run'
startTime = time.time()

result = arcpy.GetCellValue_management(r'F:\4Jessica\FelsicVolcanic\Area1Graben\hrl0000d025_07_if181l_trr3_CAT_scale_trial_p.img', '%s %s' % (x, y))

# View the result in execution log
print result.getOutput(0)
print 'script took', time.time() - startTime, 'seconds to run'