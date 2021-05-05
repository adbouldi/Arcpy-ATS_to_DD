#-------------------------------------------------------------------------------
#   *** Requires the AltaLIS V4-1 grid to function ***
#
# Name:         ATS_to_DD
# Purpose:      Using a script tool in ArcMap or ArcCatalog, and an input table containing ATS coordinates, output a feature class / shapefile of the points
#               converted to geographic coordinates. Output feature class will contain:
#                   - (GCS_North_American_1983)
#                   - A SHAPE@XY geometry token
#                   - Optional allowance for an input title field
#                   - LAT_DD field containing a float representation of the Latitude
#                   - LON_DD field containing a float representation of the Longitude
#
#               If this script is used in a code, it is possible to use the ATS_CONTAINER() and ATS_COORDINATE() objects to convert ATS locations and hold geographic
#                   data rather than just creating a shapefile.
#
#               Limits:
#                   - This can only be used for the Alberta Township System at the moment.
#                           - This can be expanded however, as long as grids in the same format are presented for Saskatchewan and Manitoba
#                   - If the coordinate is in the wrong format, it will not be detected and will return 0 and <null> values for the feature class
#
#               Acknowledgements:
#                   - Contains information licensed under the Open Government Licence - Alberta.
#                   - This was created using the AltaLIS V4-1 ATS grid shapefiles aquired from:
#                       http://www.altalis.com/products/property/ats.html
#
# Author:       Adam Boulding
# UCID:         10102514
#
# Created:      20/11/2017
# Completed:    08/12/2017
#-------------------------------------------------------------------------------
import re
import arcpy
from arcpy import AddMessage as am


class ATS_CONTAINER():
    """
    Container holding coordinate objects in ATS format. Can create a point feature class containing geographic coordinates using the createPointFC() method.

    Constructor Inputs:     -   SHAPE_LIST  : A list containing the AltaLIS V4-1 ATS grid feature classes. These are collected using the
                                                arcpy.ListFeatureClasses() method
                                                - Must contain:
                                                        - V4-1_LSD
                                                        - V4-1_QTR
                                                        - V4-1_SEC
                                                        - V4-1_TWP
                            -   COORD_LIST  : A list containing ATS coordinates in string format (ex. 'TWP-110 RGE-10 MER-4')
                            -   TITLE       : A list containing corresponding titles for the coordinates in COORD_LIST

    Methods:    -   createPointFC(self, outputLocation, outputName, projection):
                        - Returns a point feature class in the output location, under the output name, in the desired projection.

                        *** requires getCentroids() to have been run ***

                -   getCentroids(self):
                        - Assigns X and Y values to the internal Point object of the list of ATS_COORDINATE objects.
                        - Batch process

    """
    class ATS_COORDINATE():
        """
        The ATS_COORDINATE object contains a coordinate in ATS, using the AltaLIS format.

        Constructor Inputs:     -   Coord       : ATS coordinate in string format (ex. 'TWP-110 RGE-10 MER-4')
                                -   SHAPE_LIST  : List of feature classes from the AltaLIS V4-1 ATS grid (i.e. V4-1_TWP, V4-1_SEC, V4-1_QTR, V4-1_LSD)

        Methods:    -   getCentroid(self):
                            - Determines the latitude and longitude of the centroid at the referenced ATS location
        """
        def __init__(self, Coord, SHAPE_LIST):
            # Assigns to 'self' several objects and values including:
            #   - self.Point        -   The ATS_COORDINATE object creates its own Point object
            #   - self.SHAPE_LIST   -   Gets access to the list of AltaLIS feature classes from the parameter SHAPE_LIST
            #   - self.ATS          -   Holds the initial string value of the coordinate from the 'Coord' parameter (i.e. TWP-110 RGE-10 MER-4)
            #   - self.Coord        -   Formats the string value for use in an SQL Query (i.e. 'TWP-110 RGE-10 MER-4')
            #   - sCoord            -   Splits the coordinate into several parts for level query (i.e. LSD, QTR, SEC, or TWP)
            #
            self.Point = arcpy.Point()
            self.SHAPE_LIST = SHAPE_LIST
            self.ATS = Coord
            self.Coord = u"\'{}\'".format(Coord)
            sCoord = Coord.split(" ")

            # Returns a dictionary with the keys 'TWP', 'RGE', 'MER', 'SEC', 'QS', and 'LSD', and the values derived from the string coordinate.
            #   - Only returns values that exist in the coordinate (i.e. there will be no 'LSD' key if there is no LSD value)
            #   - I found out here that list comprehension can be used for dictionaries!!
            #
            self.values = {level:x.replace(level + "-", "")
                                for x in sCoord
                                    for level in ["TWP","RGE","MER","SEC","QS","LSD"]
                                        if level in x }

        def getCentroid(self):
            """
            Retrieves the Latitude and Longitude from the centroid of the corresponding shape in the AltaLIS grid.
                Does not return any value. Rather defines:
                    - self.Point.X
                    - self.Point.Y

            Outputs:    -   None
            """
            # Defines an 'empty' string for use with an SQL query
            #
            empty = "\'\'"

            # Assigns the workspace to a shorter variable name
            #
            direct = arcpy.env.workspace

            # Formats the fields for use in a where_clause
            #   Depending on the database used, the fields will have different parentheses (i.e. [] opposed to '')
            #   This takes the guess work out of it
            #
            field = [arcpy.AddFieldDelimiters(direct, x) for x in ['RA','DESCRIPTOR']]

            # Determines what level the coordinates are at using the values dictionary defined in the __init__() method.
            #   - expression        -   Compiles a SearchCursor where_clause statement from the 'field' list and the formatted coordinate
            #   - shape             -   Denotes the feature class to use from the AltaLIS shapefiles (i.e. LSD, QTR, SEC, TWP)
            #
            #   - If nothing can be determined from the level values, returns an error to the dialogue box, and returns without a value.
            #
            if 'LSD' in self.values:
                expression = u'''{} = {} AND {} = {}'''.format(field[0], empty, field[1], self.Coord)
                shape = "LSD"
            elif 'QS' in self.values:
                expression = u'''{} = {} AND {} = {}'''.format(field[0], empty, field[1], self.Coord)
                shape = "QTR"
            elif 'SEC' in self.values:
                expression = u'''{} = {} AND {} = {}'''.format(field[0], empty, field[1], self.Coord)
                shape = "SEC"
            elif all(x in self.values for x in ['TWP','RGE','MER']):
                expression = u'''{} = {}'''.format(field[1], self.Coord)
                shape = "TWP"
            else:
                arcpy.AddError("\t- [ {} ] Will return a '0' value for latitude and longitude in the Feature Class. It may be in an incorrect format".format(self.Coord))
                return

            # Using a search cursor built with the above expression and shape, get the centroid and apply it to the self.Point object created in __init__()
            #   - Creates the seach cursor with only the geometry token for use in finding the centroid.
            #   - Uses a 'with' statement in order to easily deal with the search cursor object.
            #
            with arcpy.da.SearchCursor(self.SHAPE_LIST[shape], ["SHAPE@"], where_clause=expression) as cursor:
                for c in cursor:
                    # Try to set the Point object coordinates to the centroid of the grid parcel from the AltaLIS shapefile.
                    #
                    try:
                        self.Point.X = c[0].centroid.X
                        self.Point.Y = c[0].centroid.Y

                    # If it is unable to do this, or the geometry token is corrupt, raise an error and display it to the user.
                    #   - This is mainly a precaution, as I don't know exactly what would throw this exception...
                    #
                    except Exception as e:
                        arcpy.AddError(str(e))

                    # Breaks the loop
                    #   *** This created a substantial increase in performance for the script. ***
                    #
                    break

                # As an added measure to increase performance, delete the search cursor while it is still in memory.
                #
                del cursor

    def __init__(self, SHAPE_LIST, COORD_LIST, TITLE=None):
        # Assigns the TITLE list to an internal variable
        #       - Assigned as None if nothing passed through
        #
        self.TITLE = TITLE

        self.COORDTPYE = None;

        # Creates an internal dictionary SHAPE_LIST containing the AltaLIS grid shapefiles under the relevant header (i.e. 'TWP','SEC','QTR','LSD')
        #
        self.SHAPE_LIST = {level:x for x in SHAPE_LIST for level in ["TWP","SEC","QTR","LSD"] if level in x}

        # Assigns the list of ATS coordinates to an internal list
        #
        self.COORD_LIST = COORD_LIST

        # Reports to the user the status
        am("\n[ Building List... ]")

        # Create a new internal list COORDINATES containing an ATS_COORDINATE object for each coordinate in the COORD_LIST list
        #
        self.COORDINATES = [self.ATS_COORDINATE(x, self.SHAPE_LIST) for x in self.COORD_LIST]

        # Report to the user the status of the script
        am("\tComplete")

    def createPointFC(self, outputLocation, outputName, projection):
        """
        Creates a shapefile in a location designated by the user, with a designated name, and the projection determined by the user of this object.
        Inputs:     -   outputLocation  : path to a database (string)
                    -   outputName      : name of the featureclass (string)
                    -   projection      : projection determined by the user of this object (projection object)
                                             default: GCS_North_American_1983

        Outputs:    -   None
        """
        am("\n[ Creating Shapefile... ]")

        # Determine the length of the COORDINATES list for use with the progression bar
        c_num = len(self.COORDINATES)

        # Set the progressor starting at 0 with the max number being the length of the COORDINATE list.
        arcpy.SetProgressor("step", "Creating Feature Class", 0, c_num, 1)

        # Create a feature class using the output location determined by the user, and the name determined by the user, in a "Point" feature class type.
        #
        createFeatureClass = arcpy.CreateFeatureclass_management(outputLocation, outputName, geometry_type="POINT")

        # As the CreateFeatureclass function assigns only a 'result' object, it cannot be used for any follow up functions looking to use it.
        #   This code instead assigns the output location (this being the first item in the 'getOutput(0)' tuple) to a representation 'shpFile' that
        #   can be used in other functions.
        #
        shpFile = createFeatureClass.getOutput(0)

        # Defines the projection of the feature class as the projection passed through the method.
        #   *** By Default, it is the AltaLIS shapefile projection (GCS_North_American_1983) ***
        #
        arcpy.DefineProjection_management(shpFile, projection)

        # Adds to the feature class a series of fields for future reference including:
        #   - "ATS"     -   String value that contains the original ATS coordinate.
        #   - "LAT_DD"  -   Float value holding the latitude value in decimal degrees.
        #   - "LON_DD"  -   Float value holding the Longitude value in decimal degrees.
        #
        arcpy.AddField_management(shpFile, "ATS", "TEXT")
        arcpy.AddField_management(shpFile, "LAT_DD", 'FLOAT')
        arcpy.AddField_management(shpFile, "LON_DD", 'FLOAT')

        # Checks if the field "Id" is contained in the feature class, and if so,
        #   Remove it using the DeleteField function in the Management module.
        #   - This would cause problems if a shapefile already existed...
        #
        if ("Id" in x.name for x in arcpy.ListFields(shpFile)):
            arcpy.DeleteField_management(shpFile, "Id")

        # Checks if a title field was passed through by the user.
        #
        if self.TITLE != None:
            # If there was, add a field "TITLE" to the feature class
            arcpy.AddField_management(shpFile, "TITLE", "TEXT")

            # Creates an insert cursor using the featureclass location with the fields ['SHAPE@XY','ATS',"LAT_DD","LON_DD",'TITLE']
            #
            fc = arcpy.da.InsertCursor(shpFile, ['SHAPE@XY','ATS',"LAT_DD","LON_DD",'TITLE'])

            # For each coordinate in the COORDINATE list, insert the coordinate in to the attribute table.
            #
            for i, coordinate in enumerate(self.COORDINATES):
                # Sets the progressor label to the object number using the enumerated list
                arcpy.SetProgressorLabel("Writing {} / {}...".format(str(i+1), c_num))

                # Try adding the coordinate using the insertRow method, unless something went horribly wrong, this should pass most of the time
                #
                try:
                    fc.insertRow([coordinate.Point,coordinate.ATS,coordinate.Point.Y,coordinate.Point.X,self.TITLE[i]])

                # If it does not work, report to the user which value could not be written.
                #
                except:
                    arcpy.AddError("Entry {} : [ {} : {} ] could not write to the feature class. This Error should not throw...".format(i+1,self.TITLE[i],coordinate.ATS))

                # Resets the progressor position
                arcpy.SetProgressorPosition()
        else:
            # If there was no title field passed by the user, create an insert cursor without 'TITLE'
            #
            fc = arcpy.da.InsertCursor(shpFile, ['SHAPE@XY','ATS',"LAT_DD","LON_DD"])

            # For each coordinate in the COORDINATE list, insert the coordinate in to the attribute table.
            #
            for i, coordinate in enumerate(self.COORDINATES):
                # Sets the progressor label to the object number using the enumerated list
                arcpy.SetProgressorLabel("Writing {} / {}...".format(str(i+1), c_num))

                # Try adding the coordinate using the insertRow method, unless something went horribly wrong, this should pass most of the time
                #
                try:
                    fc.insertRow([coordinate.Point,coordinate.ATS,coordinate.Point.Y,coordinate.Point.X])

                # If it does not work, report to the user which value could not be written.
                #
                except:
                    arcpy.AddError("Entry {} : [ {} ] could not write to the feature class. It may not be in the correct format.".format(i+1,coordinate.ATS))

                # Resets the progressor position
                arcpy.SetProgressorPosition()

        # Resets the progressor when the loop is finished
        arcpy.ResetProgressor()

        # Deletes the feature class insert cursor
        del fc

        # Reports the method complete to the user
        am("\tComplete")

    def getCentroids(self):
        """
        Batch process of the getCentroid() method of the internal ATS_COORDINATE object.
        Inputs:     -   None
        Outputs:    -   None
        """
        # Gets the total amount of numbers in the list of coordinates for the progress bar.
        c_num = len(self.COORDINATES)

        # Sets the progressor to start at 0 with a maximum of the list length determined above
        arcpy.SetProgressor("step", "Converting to Lat/Lon", 0, c_num, 1)
        am("\n[ Finding Centroids... ]")

        # For each coordinate in the COORDINATES list, get the centroid
        #
        for i,coord in enumerate(self.COORDINATES):
            # Sets the progressor label to the object number using the enumerate list function
            arcpy.SetProgressorLabel("Converting {} / {}...".format(str(i+1), c_num))

            # Uses the ATS_COORDINATE method 'getCentroid()' to set the coordinates Point.X and Point.Y values
            #
            coord.getCentroid()

            # Sets the progressor to the new position
            arcpy.SetProgressorPosition()

        # Reports the method complete to the user
        am("\tComplete")

        # Resets the progressor position
        arcpy.ResetProgressor()

    def getExtents(self):
        pass

    def getATS(self):
        pass

def verifyFormat(ATS_LIST):
    """
    Matches a list of input ATS coordinates against the AltaLIS format in a regex.
    Returns True if any of the coordinates match the regex,
        False if none return.
    """
    # Defines a list of expressions to check against the coordinates.
    #   Anything in square brackets represents a range (i.e. [0-9][0-9] represents anything from 00-99)
    #   Anything in curly brackets represents a required number of items (i.e. [0-9][0-9]{1} will not pass if a number from 00-99 is not inputted)
    #   Anything outside of the brackets (ex. 'SEC-') are checked literally, and will only pass if they are in the expression in that position.
    #   *** Regex are great.
    #
    reList =    [   re.compile("^(TWP-[0-9][0-9][0-9]{1} RGE-[0-9][0-9]{1} MER-[4-7]{1})$"),
                    re.compile("^(SEC-[0-9][0-9]{1} TWP-[0-9][0-9][0-9]{1} RGE-[0-9][0-9]{1} MER-[4-7]{1})$"),
                    re.compile("^(QS-[neswNEWS]{2} SEC-[0-9][0-9]{1} TWP-[0-9][0-9][0-9]{1} RGE-[0-9][0-9]{1} MER-[4-7]{1})$"),
                    re.compile("^(LSD-[0-9][0-9]{1} SEC-[0-9][0-9]{1} TWP-[0-9][0-9][0-9]{1} RGE-[0-9][0-9]{1} MER-[4-7]{1})$")
                ]

    # Uses a broad sweeping check for the coordinates. This is mostly to check whether the right column was inputted.
    #   Returns True if any coordinates match any of the expressions.
    #   Returns False if none of the coordinates match.
    #
    if any(r.match(x) for x in ATS_LIST for r in reList):
        return True
    else:
        return False


am("\n###==============================###")

# Allows overwriting of tool output for progress bar
arcpy.env.overwriteOutput = True

# Get Parameters from script tool GUI. Required inputs are:
#       - (1) Location of the AltaLIS V4.1 ATS Shapefiles including:
#               - V4-1_TWP
#               - V4-1_SEC
#               - V4-1_QTR
#               - V4-1_LSD
#       - (2) Table including ATS coordinates up to the resolution of Legal SubDivision.
#               - The table must include headers
#               - The ATS coordinates must be in the AltaLIS format.
#                   - ex. TWP-110 RGE-10 MER-4
#       - (3) Field denoting the header for the ATS coordinate
#       - (4) An Output location to a geodatabase or a folder
#       - (5) A name for the output feature class
#
arcpy.env.workspace = arcpy.GetParameter(0)
coordsIn = arcpy.GetParameterAsText(1)
titleField = arcpy.GetParameterAsText(2)
CoordinateField = arcpy.GetParameterAsText(3)
outputLocation = arcpy.GetParameterAsText(4)
outputName = arcpy.GetParameterAsText(5)

# For each of the fields (Title, ATS Coordinate) provided by the user in the script tool ui, create a SearchCursor
#   of the .csv file and return a dictionary with the fields as keys, and the values stored in a list within it.
#   - List comprehensions are a beautiful thing.
#
fDict = { l:[ r[0] for r in arcpy.da.SearchCursor(coordsIn, [l]) ]
                for l in [titleField, CoordinateField] }

# Display to the user the paths of the parameters chosen
#
am("\nPolygon Folder\t\t:\t{}".format(arcpy.env.workspace))
am("Input Coordinates\t:\t{}".format(coordsIn))
am("Output Coordinates\t:\t{}".format(outputLocation + "\\" + outputName))
am("")

# Get the list of AltaLIS ATS shapefiles in the folder provided. REQUIRED!!
#
ATS_Polygons = arcpy.ListFeatureClasses()

# Defines an error switch that will flip if any errors are encountered when checking inputs.
#
error_check = False

# Determines whether the ATS coordinates are valid (possibly passed an incorrect column as the coordinates).
#   If the coordinates are in a valid format, proceed.
#
if not verifyFormat(fDict[CoordinateField]):
    # Passes an error message, and completes the script without calling any functions or methods.
    arcpy.AddError("\n[ ERROR ]\nNo coordinates in the column are of a valid format. An incorrect field may have been passed, or there are no ATS coordinates in the column...")
    error_check = True

# Checks whether the pathway to the AltaLIS Directory is correct and contains all the required featureclasses.
#   Unless all the required featureclasses are contained in the folder, the script will not run.
#   Uses the replace method for the shapes in ATS_Polygons in case the user chose to put these shapefiles in a personal geodatabase.
#
if not all(x in [l.replace(".shp","") for l in ATS_Polygons] for x in ['V4-1_LSD','V4-1_QTR','V4-1_SEC','V4-1_TWP']):
    # Passes an error message, and completes the script without calling any functions or methods.
    arcpy.AddError("\n[ ERROR ]\nPathway to AltaLIS shapefiles incorrect, please restart with correct path.")
    error_check = True

# If the file exists... Chastise the user, and throw an error so the user doesn't have to restart the script tool.
#
if arcpy.Exists(outputLocation + "\\" + outputName):
    arcpy.AddError("[ File exists in the selected output database. Please use a different output name. ]")
    error_check = True

# If no errors were passed, continue.
#
if error_check == False:
        # The Actual script. The following lines of code complete in order:
        # - Determines the projection of the AltaLIS polygons for use with creating a feature class
        # - Defines 'ATS' as an ATS_CONTAINER object using the ATS grid feature classes, a list containing ATS Coordinates in string format, and an optional list of corresponding titles.
        # - Uses the getCentroids() method of the ATS_CONTAINER object to assign Latitude and Longitude values to the ATS coordinate list
        # - Uses the createPointFC() method of the ATS_CONTAINER object to create a point feature class using the inputted location, name, and the projection used by the AltaLIS grid feature classes.
        #
        projection = arcpy.Describe(ATS_Polygons[0]).spatialReference
        ATS = ATS_CONTAINER(ATS_Polygons, fDict[CoordinateField], TITLE=fDict[titleField])
        ATS.getCentroids()
        ATS.createPointFC(outputLocation,outputName,projection)

# Passes and completes the script if there is an error.
#
else:
    pass
