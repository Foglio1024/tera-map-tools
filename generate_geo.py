import bpy
import sys
import os

dir = os.path.dirname(bpy.data.filepath)
if not dir in sys.path:
    sys.path.append(dir)

from lib.ray_cast import generate_geo
from lib.topology import Point2D
from lib.map_importer import MapImporter

map_name = "Rucmia_P"

importer = MapImporter("E:\\TERA_DEV\\test_re_export\\cli", map_name)
importer.import_map()

generate_geo(map_name, Point2D(993, 1008), Point2D(1000, 1000), "E:/TERA_DEV")
