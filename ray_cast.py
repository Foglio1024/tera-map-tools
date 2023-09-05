import time
import bmesh
import bpy
from mathutils import bvhtree
from mathutils import Vector
from bpy_extras.object_utils import object_data_add
from lib.printer import Printer
from lib.time_tracker import TimeTracker
from lib.utils import Utils

printer = Printer()
time_tracker = TimeTracker()

SCENE_SCALE = bpy.context.scene.unit_settings.scale_length

ZONE_MAX_HEIGHT = 32800 / SCENE_SCALE
RAYCAST_LENGTH = 40000


def raycast(x, y):
    result, location, normal, index, object, matrix = bpy.context.scene.ray_cast(
        bpy.context.view_layer.depsgraph,
        Vector((x, y, ZONE_MAX_HEIGHT)),
        Vector((0, 0, -1)),
        distance=RAYCAST_LENGTH,
    )
    return result, location.z, object

def is_object_partially_in_zone(zone_BVHtree, object):
    #create bmesh objects
    bm2 = bmesh.new()

    #fill bmesh data from objects
    bm2.from_mesh(object.data)

    bm2.transform(object.matrix_world) 

    #make BVH tree from BMesh of objects
    object_BVHtree = bvhtree.BVHTree.FromBMesh(bm2)

    #get intersecting pairs
    inter = object_BVHtree.overlap(zone_BVHtree)

    return inter != []

def is_object_origin_in_zone(zone_object, object):
    left = zone_object.location.x #- zone_object.dimensions.x / 2
    right  = left + zone_object.dimensions.x #/ 2
    bottom  = zone_object.location.y #- zone_object.dimensions.y / 2
    top  = bottom + zone_object.dimensions.y #/ 2

    ret =  (object.location.x >= left and object.location.x <= right
        and object.location.y >= bottom and object.location.y <= top)
    
    return ret

ZONE_POSITION = [57,57] # game ref sys, inverted later
ZONE_ORIGIN = [56,57]   # game ref sys, inverted later

ZONE_BASE_SIZE = 614.4
NUM_SQUARES = 120
NUM_CELLS = 8
ZONE_SIZE = ZONE_BASE_SIZE * SCENE_SCALE
SQUARE_SIZE = ZONE_SIZE / NUM_SQUARES
SRC_COLLECTION = 'RNW_C_P'

done_coll = bpy.data.collections.new(SRC_COLLECTION + '_hit')
excl_coll = bpy.data.collections.new(SRC_COLLECTION + '_excl')
geo_coll = bpy.data.collections.new(SRC_COLLECTION + '_geo')
bpy.context.scene.collection.children.link(done_coll)
bpy.context.scene.collection.children.link(geo_coll)
bpy.context.scene.collection.children.link(excl_coll)
bpy.context.window.view_layer.layer_collection.children[geo_coll.name].exclude = True
bpy.context.window.view_layer.layer_collection.children[done_coll.name].exclude = True
bpy.context.window.view_layer.layer_collection.children[excl_coll.name].exclude = True

src_objects = bpy.data.collections[SRC_COLLECTION].objects

# set origin of all objects in src collection to geometry center
bpy.ops.object.select_all(action='DESELECT')
for o in src_objects:
    o.select_set(True)
    bpy.context.view_layer.objects.active = o

bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
bpy.ops.object.transform_apply(scale=True, location=False, rotation=False)
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

# define area coordinates
zone_bb_mesh = bpy.data.meshes.new('ZoneBB')
zone_bb_obj = bpy.data.objects.new('ZoneBB', zone_bb_mesh)
zone_bb_obj.location.x = (ZONE_SIZE * (ZONE_POSITION[1] - ZONE_ORIGIN[1])) / SCENE_SCALE # swapped
zone_bb_obj.location.y = (ZONE_SIZE * (ZONE_POSITION[0] - ZONE_ORIGIN[0])) / SCENE_SCALE # swapped
zone_bb_points = [
    [0,0,0],[ZONE_BASE_SIZE,0,0],[ZONE_BASE_SIZE,ZONE_BASE_SIZE,0],[0,ZONE_BASE_SIZE,0],
    [0,0,ZONE_MAX_HEIGHT],[ZONE_BASE_SIZE,0,ZONE_MAX_HEIGHT],[ZONE_BASE_SIZE,ZONE_BASE_SIZE,ZONE_MAX_HEIGHT],[0,ZONE_BASE_SIZE,ZONE_MAX_HEIGHT]
]
zone_bb_faces = [
    [0,1,2,3],
    [0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7],
    [4,5,6,7]
]
zone_bb_mesh.from_pydata(zone_bb_points, [], zone_bb_faces)
bpy.context.scene.collection.objects.link(zone_bb_obj)
zone_bb_obj.display_type = 'WIRE'
bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

zone_bb_bmesh = bmesh.new()
zone_bb_bmesh.from_mesh(zone_bb_mesh)
zone_bb_bmesh.transform(zone_bb_obj.matrix_basis)
zone_BVHtree = bvhtree.BVHTree.FromBMesh(zone_bb_bmesh)

# check if objects are contained inside the area
for o in src_objects:
    if is_object_partially_in_zone(zone_BVHtree, o) or is_object_origin_in_zone(zone_bb_obj, o): continue
    src_objects.unlink(o)
    excl_coll.objects.link(o)

bpy.context.scene.collection.objects.unlink(zone_bb_obj)

objects_hit = []

volume_idx = 0

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

    time_tracker.start()

    for sx in range(NUM_SQUARES):
        for sy in range(NUM_SQUARES):
            square_location_x = (
                sx * (ZONE_SIZE / NUM_SQUARES) + (ZONE_POSITION[1] - ZONE_ORIGIN[1]) * ZONE_SIZE
            ) / SCENE_SCALE
            square_location_y = (
                sy * (ZONE_SIZE / NUM_SQUARES) + (ZONE_POSITION[0] - ZONE_ORIGIN[0]) * ZONE_SIZE
            ) / SCENE_SCALE

            cell_times = []

            for cx in range(NUM_CELLS):
                for cy in range(NUM_CELLS):
                    cell_x = (cx + 0.5) * ((SQUARE_SIZE/NUM_CELLS) / SCENE_SCALE)
                    cell_y = (cy + 0.5) * ((SQUARE_SIZE/NUM_CELLS) / SCENE_SCALE)

                    abs_x = cell_x + square_location_x
                    abs_y = cell_y + square_location_y

                    cell_idx = cx + (NUM_CELLS * cy) + (sx + (NUM_SQUARES * sy)) * NUM_CELLS * NUM_CELLS

                    if cell_idx in missed_points: continue
                    cell_start = time.time()
                    result, z, obj = raycast(abs_x, abs_y)
                    if result:
                        volume_points.append([abs_x, abs_y, z])
                        if obj.name not in objects_hit:
                            objects_hit.append(obj.name)
                    else:
                        missed_points[cell_idx] = True
                    cell_end = time.time()
                    cell_times.append(cell_end - cell_start)

            avg = 0
            if len(cell_times) != 0:
                avg = sum(cell_times)/len(cell_times)

            squares_per_sec = time_tracker.get_iterations_per_sec()
            squares_done = sy + (sx *NUM_SQUARES)
            squares_left = NUM_SQUARES * NUM_SQUARES - squares_done
            time_left = squares_left / squares_per_sec
            printer.reprint(f'Zone ({ZONE_POSITION[0]}:{ZONE_POSITION[1]}) | Volume {volume_idx} | Square ({str(int(sx)).rjust(3, " ")}:{str(int(sy)).rjust(3, " ")}) | Speed: {squares_per_sec:.1f} sq/s\t| ETA: {Utils.time_convert(time_left)}')

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
        printer.print(f'Volume {volume_idx} done in {Utils.time_convert(volume_end - volume_start)} - removed {objects_hit_count} objects')
        volume_idx+=1

    else: break


end = time.time()

printer.print(f'Total time: {Utils.time_convert(end - start)}')