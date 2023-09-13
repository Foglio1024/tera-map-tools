import bpy
import os
import xml.etree.ElementTree as ET
import math
import os
import sys

dir = os.path.dirname(bpy.data.filepath)
if not dir in sys.path:
    sys.path.append(dir)

from bpy_extras.object_utils import object_data_add
from lib.scene_utils import SceneUtils

def parse_sections(xsections):
    for section in xsections:
        fences = []

        xfences = section.findall('Fence')
        for fence in xfences:
            fences.append(fence)
        
        sections.append(fences)

        # parse_sections(section.findall('FlySection'))
        

map_name = 'HNC_A_P'
continent_id = 9002

# PATH = 'E:\\TERA_DEV\\Server\\Executable\\Bin\\Datasheet\\AreaData\\AreaData_7031_RNW_C_P.xml'
# PATH = 'E:\\TERA_DEV\\Server\\Executable\\Bin\\Datasheet\\ClimbingTerritory_7031_RNW_B_P.xml'
PATH = f'E:\\TERA_DEV\\Server\\Executable\\Bin\\Datasheet\\ShieldTerritory_{continent_id}_{map_name}.xml'

ROOT = ET.parse(PATH).getroot()

sections = []
print(ROOT)

# xsections = ROOT.findall('FlySection')
xsections = ROOT.findall('Territory')

print(f'Found {str(len(xsections))} sections')

parse_sections(xsections)

fence_coll = SceneUtils.find_or_create_collection('Fences')

# pivot = bpy.data.objects.new("Pivot", None)
# fence_coll.objects.link(pivot)

meshes = []
idx = 0
for section in sections:

    vectors = []
    edges = []

    for fence in section:
        str_comp = fence.attrib.get('pos').split(',')
        p = []
        c = 0
        for v in str_comp:
            f = float(v)
            p.append(f)
        vectors.append(p)
        for c in range(0, len(vectors)):
            edges.append([c, c + 1])
        
    edges[len(edges) -  1][1] = 0

    mesh = bpy.data.meshes.new("Fence " + str(idx))
    mesh.from_pydata(vectors, edges, [])
    obj = bpy.data.objects.new("Fence " + str(idx), mesh)
    # obj.parent = pivot
    obj.scale.x = 4
    obj.scale.y = 4
    obj.scale.z = 4
    fence_coll.objects.link(obj)

    idx = idx + 1

SceneUtils.reframe(fence_coll)


