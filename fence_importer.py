import bpy
import os
import xml.etree.ElementTree as ET
import math
from bpy_extras.object_utils import object_data_add

PATH = 'E:\\TERA_DEV\\Server\\Executable\\Bin\\Datasheet\\AreaData\\AreaData_7031_RNW_C_P.xml'

AREA = ET.parse(PATH).getroot()

sections = []
print(AREA)

xsections = AREA.findall('FlySection')

print(f'Found {str(len(xsections))} sections')


def parse_sections(xsections):
    for section in xsections:
        fences = []

        xfences = section.findall('Fence')
        for fence in xfences:
            fences.append(fence)
        
        sections.append(fences)

        parse_sections(section.findall('FlySection'))
        

parse_sections(xsections)


pivot = bpy.data.objects.new("Pivot", None)
bpy.context.scene.collection.objects.link(pivot)


def reframe():

    pivot.scale.x *= 0.01 * (-1)
    pivot.scale.y *= 0.01
    pivot.scale.z *= 0.01

    pivot.rotation_euler[2] = math.radians(-90)

    bpy.context.evaluated_depsgraph_get().update()
    for child in pivot.children:
        pwm = child.matrix_world.copy()
        child.parent = None
        child.matrix_world = pwm

    bpy.data.objects.remove(bpy.data.objects[pivot.name])

def find_or_create_collection(coll_name):
    found = None
    for c in bpy.data.collections:
        if c.name == coll_name:
            found = c
    if found == None:
        found = bpy.data.collections.new(coll_name)
        bpy.context.scene.collection.children.link(found)

    return found


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

    mesh = bpy.data.meshes.new("FlySection " + str(idx))
    mesh.from_pydata(vectors, edges, [])
    obj = bpy.data.objects.new("FlySection " + str(idx), mesh)
    obj.parent = pivot
    obj.scale.x = 4
    obj.scale.y = 4
    obj.scale.z = 4
    bpy.context.scene.collection.objects.link(obj)

    # for point in points:
    #     empty = bpy.data.objects.new('Fence' , None)
    #     empty.location.x = point[0]*4
    #     empty.location.y = point[1]*4
    #     empty.location.z = point[2]*4
    #     coll.objects.link(empty)
    
    idx = idx + 1

reframe()


