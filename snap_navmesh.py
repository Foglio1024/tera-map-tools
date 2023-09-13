import bpy
from bpy import context as C
from bpy import data as D

nodes_mesh = D.objects["Nodes"].data
cells_mesh = D.objects["x993y1008_0"].data


def get_cell_z(vertex):
    for cell in cells_mesh.vertices:
        if (abs(cell.co.x - vertex.co.x) <= 0.01 
        and abs(cell.co.y - vertex.co.y) <= 0.01):
            return cell
    return None


for vert in nodes_mesh.vertices:
    cell = get_cell_z(vert)
    if cell != None:
        vert.co.x = cell.co.x
        vert.co.y = cell.co.y
        vert.co.z = cell.co.z

    else:
        print(f'MISSED {vert.co}')    
        vert.co.z = 0

    try:
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
    except:
        pass

