
import bpy
import os
import sys

dir = os.path.dirname(bpy.data.filepath)
if not dir in sys.path:
    sys.path.append(dir)

from lib.map_importer import MapImporter

map = 'HNC_A_P'

importer = MapImporter(
    source_dir="E:\\TERA_DEV\\test_re_export\\cli", map_name=map
)
importer.import_map(import_meshes=True, import_agg_geoms=False, hide=True)
