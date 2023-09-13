import struct
import bpy
import sys
import os

dir = os.path.dirname(bpy.data.filepath)
if not dir in sys.path:
    sys.path.append(dir)

import bmesh
from bpy import context as C
from bpy import data as D
from lib.topology import Point2D
from lib.topology import Node

base_pos = Point2D((995 - 1000) * 614.4, (1007 - 1000) * 614.4)

output_path = "E:/TERA_DEV/out"
name = "pathdata_Rucmia_P"

nodes_obj = D.objects["Nodes"]
nodes_mesh = nodes_obj.data
bm = bmesh.from_edit_mesh(nodes_mesh)


def sign(a):
    if a == 0:
        return 0
    return a // abs(a)


def find_direction(current, linked):
    # rel_pos = Point2D(linked.co.y - current.co.y, linked.co.x - current.co.x) # already swapped for export

    # if rel_pos.x < 0:
    #     if rel_pos.y > abs(rel_pos.x):
    #         return 6
    #     elif rel_pos.y <= 0 and abs(rel_pos.y) > abs(rel_pos.x):
    #         return 0
    #     elif rel_pos.y <= rel_pos.x:
    #         return 1

    x = linked.co.y - current.co.y  # swapped
    y = linked.co.x - current.co.x

    match [sign(x), sign(y), sign(x + y), sign(x - y)]:
        case [-1, (-1 | 0), _, -1]:
            return 0
        case [-1, (-1 | 0), _, (0 | 1)]:
            return 1
        case [(0 | 1), -1, -1, _]:
            return 2
        case [(0 | 1), -1, (0 | 1), _]:
            return 3
        case [1, (0 | 1), _, -1]:
            return 4
        case [1, (0 | 1), _, (0 | 1)]:
            return 5
        case [(-1 | 0), 1, -1, _]:
            return 6
        case [(-1 | 0), 1, (0 | 1), _]:
            return 7
        case _:
            raise ...  # should be unreachable. Probably.


sq_size = 614.4 / 120


def is_node_in_square(x, y, say, sax):
    # print(f'node: {x},{y} sq:{sax},{say} s:{sq_size}')
    return abs(x - sax) < sq_size and abs(y - say) < sq_size


def get_nodes_per_square(zx, zy, sx, sy, nodes):
    sq_pos_x = base_pos.x + sx * sq_size + zx * 614.4
    sq_pos_y = base_pos.y + sy * sq_size + zy * 614.4

    ret = 0

    for n in nodes:
        node = nodes[n]
        if is_node_in_square(node.x, node.y, sq_pos_x, sq_pos_y):
            ret += 1
            # print(f"node: {node.x},{node.y} sq:{sq_pos_x},{sq_pos_y} s:{sq_size}")

    return ret


nodes = {}

for v in bm.verts:
    node = Node(v.index, v.co.x, v.co.y, v.co.z)
    node.neighbors = [-1, -1, -1, -1, -1, -1, -1, -1]
    node.distances = [
        2147483647,
        2147483647,
        2147483647,
        2147483647,
        2147483647,
        2147483647,
        2147483647,
        2147483647,
    ]

    found_linked = []

    for e in v.link_edges:
        other = e.other_vert(v)

        if other.index in found_linked:
            continue
        found_linked.append(other.index)

        # skip if the target node is already connected to this node
        if other in nodes and v.index in nodes[other].neighbors:
            continue

        dir = find_direction(v, other)
        # print(f'Linking {v.index} -> {other.index}')
        node.neighbors[dir] = other.index
        node.distances[dir] = e.calc_length() * 25

    nodes[v.index] = node
    print(f"Added node {v.index} with n{node.neighbors} d{node.distances}")

gdi_file = open(f"{output_path}/{name}.gdi", "wb")
gdi_file.write(struct.pack("I", 994))
gdi_file.write(struct.pack("I", 1007))
gdi_file.write(struct.pack("I", 995))
gdi_file.write(struct.pack("I", 1007))

nod_file = open(f"{output_path}/{name}.nod", "wb")

gdi_file.write(struct.pack("I", len(nodes)))

indices_array = []
for zx in range(2):
    for zy in range(1):
        for sx in range(120):
            for sy in range(120):
                nps = get_nodes_per_square(zx, zy, sx, sy, nodes)
                gdi_file.write(struct.pack("H", nps))
                indices_array.append(nps)


tot_idx = 0
for idx in indices_array:
    gdi_file.write(struct.pack("I", tot_idx))
    tot_idx += idx


for n in nodes:
    node = nodes[n]

    nod_file.write(struct.pack("f", round(node.y * 25)))  # swapped
    nod_file.write(struct.pack("f", round(node.x * 25)))
    nod_file.write(struct.pack("f", round(node.z * 25)))

    for nb in node.neighbors:
        nod_file.write(struct.pack("i", nb))
    for nd in node.distances:
        nod_file.write(struct.pack("I", int(nd)))


gdi_file.close()
nod_file.close()
