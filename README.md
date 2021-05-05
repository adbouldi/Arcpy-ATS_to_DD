# Arcpy-ATS_to_DD
Batch converts ATS coordinates to DD using the Altalis ATS v4.1 Polygons

*** Requires the AltaLIS V4-1 grid to function ***

# Purpose
Using a script tool in ArcMap or ArcCatalog, and an input table containing ATS coordinates, output a feature class / shapefile of the points converted to geographic coordinates. Output feature class will contain:
  - (GCS_North_American_1983)
  - A SHAPE@XY geometry token
  - Optional allowance for an input title field
  - LAT_DD field containing a float representation of the Latitude
  - LON_DD field containing a float representation of the Longitude

If this script is used in a code, it is possible to use the ATS_CONTAINER() and ATS_COORDINATE() objects to convert ATS locations and hold geographic data rather than just creating a shapefile.

# Limits
This can only be used for the Alberta Township System at the moment. This can be expanded however, as long as grids in the same format are presented for Saskatchewan and Manitoba.

If the coordinate is in the wrong format, it will not be detected and will return 0 and <null> values for the feature class

# Acknowledgements
Contains information licensed under the Open Government Licence - Alberta.
This was created using the free AltaLIS V4-1 ATS grid shapefiles aquired from:
http://www.altalis.com

Author:       Adam Boulding
Completed:    08/12/2017
