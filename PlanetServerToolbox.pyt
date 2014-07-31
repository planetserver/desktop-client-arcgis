# DataType: http://resources.arcgis.com/en/help/main/10.1/index.html#//001500000035000000

import os, sys
import arcpy
import urllib
import urllib2
from arcpy import env

class Toolbox(object):
    def __init__(self):
        """PlanetServer Toolbox"""
        self.label = "PlanetServer Toolbox"
        self.alias = "PlanetServer"

        # List of tool classes associated with this toolbox
        self.tools = [CRISMWCPSSummaryProducts]

class CRISMWCPSSummaryProducts(object):
    def __init__(self):
        """CRISM WCPS Summary Products"""
        self.label = "CRISM WCPS Summary Products"
        self.description = "Derive Summary Products for CRISM data through WCPS"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        # ODE footprints of CRISM in PlanetServer
        in_layer = arcpy.Parameter(
            displayName="ODE Footprints shapefile",
            name="in_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        
        in_layer.value = 'mars_mro_crism_trdr_frthrlhrs07_c0a_planetserver'
        
        # Preset summary products
        spname = arcpy.Parameter(
            displayName="Choose which summary products",
            name="sp_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue=True)
        
        spname.filter.type = "ValueList"
        global sp
        spname.filter.list = sp.keys()
        
        # Output folder
        out_folder = arcpy.Parameter(
            displayName="Output Folder",
            name="out_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")
        
        out_folder.value = 'F:\NoachisTerra\CRISM_WCPS'
        
        parameters = [in_layer, spname, out_folder]
        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        global sp
        wcpsurl = 'http://planetserver.jacobs-university.de:8080/rasdaman/ows'
        proj = 'PROJCS["Mars Equicylindrical clon=0",GEOGCS["GCS_Mars_2000_Sphere",DATUM["D_Mars_2000_Sphere",SPHEROID["Mars_2000_Sphere_IAU_IAG",3396190.0,0.0]],PRIMEM["Reference_Meridian",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Equidistant_Cylindrical"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",0.0],PARAMETER["Standard_Parallel_1",0.0],UNIT["Meter",1.0]]'
        env.addOutputToMap = True
        env.workspace = 'in_memory'
        env.overwriteOutput = 1
        mxd = arcpy.mapping.MapDocument("CURRENT")

        selectedlayer = parameters[0].valueAsText
        spname = parameters[1].valueAsText.split(";")
        folder = parameters[2].valueAsText

        productids = []
        metadata = {}
        #desc = arcpy.Describe(selectedlayer)
        #if desc.fidSet:
        for row in arcpy.SearchCursor(selectedlayer):
            productid = row.ProductId.lower()
            productids.append(productid)
            xmin = float(row.XMIN)
            xmax = float(row.XMAX)
            ymin = float(row.YMIN)
            ymax = float(row.YMAX)
            width = float(row.WIDTH)
            height = float(row.HEIGHT)
            metadata[productid] = [xmin,xmax,ymin,ymax,width,height]

        # crismobs = {}
        # for productid in productids:
            # if not productid[:14] in crismobs.keys():
                # crismobs[productid[:14]] = productid
            # else:
                # crismobs[productid[:14]] = [crismobs[productid[:14]], productid]
                # crismobs[productid[:14]].sort()
        for productid in productids:
            for name in spname:
                name = str(name)
                crism_type = sp[name][0]
                wcps_code = sp[name][1]
                if crism_type + '_trr' in productid:
                    collection = productid + '_1_01'
                    wcpsquery = 'for data in ( ' + collection + ' ) return encode( (float) ' + wcps_code + ', "GTiff", "NODATA=65535;")';

                    values = {'query' : wcpsquery}
                    data = urllib.urlencode(values)
                    req = urllib2.Request(wcpsurl, data)
                    response = urllib2.urlopen(req)

                    wcpstif = os.path.join(folder, productid + '_' + name + '.tif')

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
                        arcpy.DefineProjection_management(wcpstif, proj)
                        arcpy.AddMessage("Successful download: " + wcpstif)
                    else:
                        arcpy.AddMessage("Unsuccessful download: " + wcpstif)
                    
                    # Add to ArcMap
                    df = arcpy.mapping.ListDataFrames(mxd)[0]
                    result = arcpy.MakeRasterLayer_management(wcpstif, productid + '_' + name)
                    layer = result.getOutput(0)
                    arcpy.mapping.AddLayer(df, layer, 'TOP')

        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()
        return

sp = {'bd1900r': ['l','(1 -(((data.138 + data.139 + data.140 + data.141 + data.142 + data.143)) / (data.131 + data.132 + data.133 + data.169 + data.170 + data.171 ) ))'],
      'bd2100': ['l','(1 - ( ( (data.170 + data.173 ) * 0.5 ) / ( (0.3778237893630837 * data.141) + (0.6221762106369163 * data.190) ) ))'],
      'bd2210': ['l','(1 - ( data.184 / ( 0.3530040053404536 * data.173 + 0.6469959946595464 * data.190 ) ))'],
      'd2300': ['l','(1 - ( ((data.196 / (data.124 + ((data.232 - data.124) / (2.52951 - 1.81598)) * (2.29133 - 1.81598))) + (data.200 / (data.124 + ((data.232 - data.124) / (2.52951 - 1.81598)) * (2.31779 - 1.81598))) + (data.202 / (data.124 + ((data.232 - data.124) / (2.52951 - 1.81598)) * (2.33102 - 1.81598)))) / ((data.170 / (data.124 + ((data.232 - data.124) / (2.52951 - 1.81598)) * (2.11948 - 1.81598))) + (data.178 / (data.124 + ((data.232 - data.124) / (2.52951 - 1.81598)) * (2.17233 - 1.81598))) + (data.184 / (data.124 + ((data.232 - data.124) / (2.52951 - 1.81598)) * (2.21199 - 1.81598)))) ))'],
      'sindex': ['l','(1 - ( (data.167 + data.212) / ( 2 * data.196) ))'],
      'bd2500': ['l','(1 - ( (data.228 + data.229) / ( data.234 + data.209 ) ))'],
      'olindex2': ['l','(((((((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)) * 1.054) + (((data.213 + data.212 + data.214) / 3) - (2.404 * ((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750))))) - ((data.8 + data.7 + data.9) / 3)) / ((((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)) * 1.054) + (((data.213 + data.212 + data.214) / 3) - (2.404 * ((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)))))) * 0.1) + (((((((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)) * 1.211) + (((data.213 + data.212 + data.214) / 3) - (2.404 * ((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750))))) - ((data.32 + data.31 + data.33) / 3)) / ((((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)) * 1.211) + (((data.213 + data.212 + data.214) / 3) - (2.404 * ((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)))))) * 0.1) + (((((((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)) * 1.329) + (((data.213 + data.212 + data.214) / 3) - (2.404 * ((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750))))) - ((data.50 + data.50 + data.51) / 3)) / ((((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)) * 1.329) + (((data.213 + data.212 + data.214) / 3) - (2.404 * ((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)))))) * 0.4) + (((((((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)) * 1.474) + (((data.213 + data.212 + data.214) / 3) - (2.404 * ((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750))))) - ((data.72 + data.71 + data.73) / 3)) / ((((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)) * 1.474) + (((data.213 + data.212 + data.214) / 3) - (2.404 * ((((data.213 + data.212 + data.214) / 3) - ((data.114 + data.113 + data.115) / 3)) / (2.404 - 1.750)))))) * 0.4)']}
