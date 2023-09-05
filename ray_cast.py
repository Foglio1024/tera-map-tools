import time
import math
import bpy
from mathutils import Vector
from bpy_extras.object_utils import object_data_add

class Printer:
    def __init__(self):
        self.text = ''

    def reprint(self, text):
        empty = ''
        for c in self.text:
            empty += ' '
        print(empty, end='\r')
        print(text, end='\r')
        self.text = text

    def print(self, text):
        self.reprint(text + '\n')

printer = Printer()

def raycast(x, y):
    result, location, normal, index, object, matrix = bpy.context.scene.ray_cast(
        bpy.context.view_layer.depsgraph,
        Vector((x, y, 32800)),
        Vector((0, 0, -1)),
        distance=40000,
    )
    return result, location.z, object


SCENE_SCALE = bpy.context.scene.unit_settings.scale_length

ZONE_SIZE = 15360

SQUARE_SIZE = ZONE_SIZE / 120

ZONE_OFFSET = Vector([0, 1, 0])

SRC_COLLECTION = 'RNW_C_P'
done_coll = bpy.data.collections.new(SRC_COLLECTION + '_hit')
geo_coll = bpy.data.collections.new(SRC_COLLECTION + '_geo')
bpy.context.scene.collection.children.link(done_coll)
bpy.context.scene.collection.children.link(geo_coll)
bpy.context.window.view_layer.layer_collection.children[geo_coll.name].exclude = True
bpy.context.window.view_layer.layer_collection.children[done_coll.name].exclude = True

objects_hit = []

volume_idx = 0

num_squares = 120
num_cells = 8

# missed_points = []
missed_points = {}
start = time.time()
while True:

    volume_start = time.time()
    volume_squares = []
    volume_name = f'Volume_{volume_idx}'
    volume_mesh = bpy.data.meshes.new(volume_name)
    volume_obj = bpy.data.objects.new(volume_name, volume_mesh)
    volume_points = []
    volume_data = []

    for sx in range(num_squares):
        for sy in range(num_squares):
            # printer.reprint(f'Square: {x},{y} @ {volume_idx}')
            square_location_x = (
                sx * (ZONE_SIZE / 120) + ZONE_OFFSET.x * ZONE_SIZE
            ) / SCENE_SCALE
            square_location_y = (
                sy * (ZONE_SIZE / 120) + ZONE_OFFSET.y * ZONE_SIZE
            ) / SCENE_SCALE

            cell_times = []

            for cx in range(num_cells):
                for cy in range(num_cells):
                    cell_x = (cx + 0.5) * ((128/num_cells) / SCENE_SCALE)
                    cell_y = (cy + 0.5) * ((128/num_cells) / SCENE_SCALE)

                    abs_x = cell_x + square_location_x
                    abs_y = cell_y + square_location_y

                    cell_idx = cx + (num_cells * cy) + (sx + (num_squares * sy)) * num_cells * num_cells

                    # point_key = f'{abs_x}_{abs_y}'

                    if cell_idx in missed_points: continue
                    cell_start = time.time()
                    result, z, obj = raycast(abs_x, abs_y)
                    if result:
                        volume_points.append([abs_x, abs_y, z])
                        if obj.name not in objects_hit:
                            objects_hit.append(obj.name)
                    else:
                        # missed_points.append([abs_x, abs_y])
                        missed_points[cell_idx] = True
                    cell_end = time.time()
                    cell_times.append(cell_end - cell_start)

            avg = 0
            if len(cell_times) != 0:
                avg = sum(cell_times)/len(cell_times)
            printer.reprint(f'Square: {sx},{sy} @ {volume_idx} ({avg}s ray cast average)')


    if len(volume_points) != 0:
        volume_mesh.from_pydata(volume_points, [], [])
        geo_coll.objects.link(volume_obj)
        volume_squares.append(volume_obj)

    objects_hit_count = len(objects_hit)

    if len(objects_hit) != 0:
        for hit_object_name in objects_hit:
            done_coll.objects.link(bpy.data.objects[hit_object_name])
            bpy.data.collections[SRC_COLLECTION].objects.unlink(bpy.data.objects[hit_object_name])

        objects_hit.clear()

        volume_end = time.time()
        printer.print(f'Volume {volume_idx} done in {volume_end - volume_start}s - removed {objects_hit_count} objects')
        volume_idx+=1
    else: break


end = time.time()

printer.print(f'Total time: {end - start}')