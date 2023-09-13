import bpy
from bpy_extras.object_utils import object_data_add
import array
import math

from lib.topology import Node
from lib.printer import Printer

P = Printer()

name = 'RNW_C_P'

gdi_path = f"E:\\TERA_DEV\\Server\\Topology\\pathdata_{name}.gdi"
nod_path = f"E:\\TERA_DEV\\Server\\Topology\\pathdata_{name}.nod"

node_count = 0

with open(gdi_path, "rb") as gdi:
    x1 = array.array("I", gdi.read(4))[0]
    y1 = array.array("I", gdi.read(4))[0]
    x2 = array.array("I", gdi.read(4))[0]
    y2 = array.array("I", gdi.read(4))[0]

    size_x = x2 - x1 + 1
    size_y = y2 - y1 + 1

    node_count = array.array("I", gdi.read(4))[0]

nodes = {}
with open(nod_path, "rb") as nod:
    for n in range(node_count):
        idx = int(nod.tell() / 76)
        coords = array.array("f", nod.read(3 * 4))
        neighbors = array.array("i", nod.read(8 * 4))
        distances = array.array("i", nod.read(8 * 4))
        node = Node(idx, coords[0], coords[1], coords[2], neighbors, distances)
        nodes[idx] = node

vectors = []
edges = []
for node in nodes.values():
    vectors.append([node.x, node.y, node.z])
    P.reprint(f'{node.idx}/{len(nodes.values())}')
    for neighbor in node.neighbors:
        if neighbor in nodes.keys():
            edges.append([node.idx, neighbor])


mesh = bpy.data.meshes.new("Nodes")
mesh.from_pydata(vectors, edges, [])

obj = bpy.data.objects.new("Nodes", mesh)
bpy.context.scene.collection.objects.link(obj)

scale = 0.04
obj.scale.x *= scale * -1
obj.scale.y *= scale
obj.scale.z *= scale

obj.rotation_euler[2] = math.radians(-90)
