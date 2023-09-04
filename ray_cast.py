import bpy
import math
from mathutils import Vector
from bpy_extras.object_utils import object_data_add


def raycast(x, y):
    result, location, normal, index, object, matrix = bpy.context.scene.ray_cast(
        bpy.context.view_layer.depsgraph,
        Vector((x, y, 32800)),
        Vector((0, 0, -1)),
        distance=40000,
    )
    return location.z


SCENE_SCALE = bpy.context.scene.unit_settings.scale_length

ZONE_SIZE = 15360

SQUARE_SIZE = ZONE_SIZE / 120

ZONE_OFFSET = [0, 1]


for x in range(120):
    for y in range(120):
        print(f'Square: {x},{y}')
        rect_mesh = bpy.data.meshes.new(f"S_x{x}y{y}")
        rect = bpy.data.objects.new(f"S_x{x}y{y}", rect_mesh)
        rect.location.x = (
            x * (ZONE_SIZE / 120) + ZONE_OFFSET[0] * ZONE_SIZE
        ) / SCENE_SCALE
        rect.location.y = (
            y * (ZONE_SIZE / 120) + ZONE_OFFSET[1] * ZONE_SIZE
        ) / SCENE_SCALE

        square_points = [
            # [0, 0, 0],
            # [0, SQUARE_SIZE / SCENE_SCALE, 0],
            # [SQUARE_SIZE / SCENE_SCALE, SQUARE_SIZE / SCENE_SCALE, 0],
            # [SQUARE_SIZE / SCENE_SCALE, 0, 0],
        ]
        square_edges = []  # [[0,1],[1,2],[2,3],[3,0]]
        square_faces = []  # [[0,1,2,3,0]]

        for cx in range(8):
            for cy in range(8):
                cell_x = (cx + 0.5) * (16 / SCENE_SCALE)
                cell_y = (cy + 0.5) * (16 / SCENE_SCALE)
                z = raycast(cell_x + rect.location.x, cell_y + rect.location.y)
                square_points.append([cell_x, cell_y, round(z, 1)])

        rect_mesh.from_pydata(square_points, square_edges, square_faces)
        bpy.context.scene.collection.objects.link(rect)


# result, location, normal, index, object, matrix = bpy.context.scene.ray_cast(bpy.context.view_layer.depsgraph, bpy.data.objects['Empty'].location , Vector((0,0,-1)), distance=10000)

# loc_obj = bpy.data.objects.new('loc', None)
# loc_obj.location = location
# bpy.context.scene.collection.objects.link(loc_obj)

# print(result)
# print(location)
# print(normal)
# print(index)
# print(object)
# print(matrix)
