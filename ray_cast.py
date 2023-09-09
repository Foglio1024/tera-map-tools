import math
import time
import bmesh
import bpy
import sys
import os

dir = os.path.dirname(bpy.data.filepath)
if not dir in sys.path:
    sys.path.append(dir)

from bpy import context as C
from bpy import data as D
from bpy_extras.object_utils import object_data_add
from mathutils import bvhtree
from mathutils import Vector
from lib.topology import Point2D
from lib.printer import Printer
from lib.time_tracker import TimeTracker
from lib.utils import Utils

P = Printer()
T = TimeTracker()

SCENE_SCALE = C.scene.unit_settings.scale_length


class ZoneShape:
    def __init__(
        self, pos: Point2D, origin: Point2D, max_height: float, base_size: float
    ):
        self.num_squares: int = 120
        self.num_cells: int = 8

        self.pos = pos
        self.origin = origin
        self.max_height = max_height / SCENE_SCALE
        self.base_size = base_size

        self.rel_pos = Point2D(pos.x - origin.x, pos.y - origin.y)
        self.size = base_size * SCENE_SCALE
        self.square_size = self.size / self.num_squares

        self.__create_bounding_box()

    def __create_bounding_box(self):
        bb_mesh = D.meshes.new("ZoneBB")
        bb_obj = D.objects.new("ZoneBB", bb_mesh)
        bb_obj.location.x = self.base_size * self.rel_pos.y  # swapped
        bb_obj.location.y = self.base_size * self.rel_pos.x  # swapped
        bb_points = [
            [0, 0, 0],
            [self.base_size, 0, 0],
            [self.base_size, self.base_size, 0],
            [0, self.base_size, 0],
            [0, 0, self.max_height],
            [self.base_size, 0, self.max_height],
            [self.base_size, self.base_size, self.max_height],
            [0, self.base_size, self.max_height],
        ]
        bb_faces = [
            [0, 1, 2, 3],
            [0, 1, 5, 4],
            [1, 2, 6, 5],
            [2, 3, 7, 6],
            [3, 0, 4, 7],
            [4, 5, 6, 7],
        ]
        bb_mesh.from_pydata(bb_points, [], bb_faces)
        C.scene.collection.objects.link(bb_obj)
        bb_obj.display_type = "WIRE"

        bb_bmesh = bmesh.new()
        bb_bmesh.from_mesh(bb_mesh)
        bb_bmesh.transform(bb_obj.matrix_basis)
        bb_bvhtree = bvhtree.BVHTree.FromBMesh(bb_bmesh)

        self.bounding_box_object = bb_obj
        self.bounding_box_bvhtree = bb_bvhtree

    def get_square_pos(self, sx: int, sy: int):
        return Point2D(
            (sx * self.square_size + self.rel_pos.y * self.size) / SCENE_SCALE,
            (sy * self.square_size + self.rel_pos.x * self.size) / SCENE_SCALE,
        )

    def get_cell_pos(self, sx: int, sy: int, cx: int, cy: int):
        sq_pos = self.get_square_pos(sx, sy)

        cell_rel_pos = Point2D(
            (cx + 0.5) * ((self.square_size / self.num_cells) / SCENE_SCALE),
            (cy + 0.5) * ((self.square_size / self.num_cells) / SCENE_SCALE),
        )

        return Point2D(
            round(cell_rel_pos.x + sq_pos.x, 3), round(cell_rel_pos.y + sq_pos.y, 3)
        )

    def get_cell_index(self, sx: int, sy: int, cx: int, cy: int):
        return int(
            cx
            + (self.num_cells * cy)
            + (sx + (self.num_squares * sy)) * int(math.pow(self.num_cells, 2))
        )

    def is_object_partially_in_zone(self, object):
        # create bmesh objects
        bm = bmesh.new()

        # fill bmesh data from objects
        bm.from_mesh(object.data)

        bm.transform(object.matrix_world)

        # make BVH tree from BMesh of objects
        object_bvhtree = bvhtree.BVHTree.FromBMesh(bm)

        # get intersecting pairs
        inter = object_bvhtree.overlap(self.bounding_box_bvhtree)

        return inter != []

    def is_object_origin_in_zone(self, object):
        left = self.bounding_box_object.location.x  # - zone_object.dimensions.x / 2
        right = left + self.bounding_box_object.dimensions.x  # / 2
        bottom = self.bounding_box_object.location.y  # - zone_object.dimensions.y / 2
        top = bottom + self.bounding_box_object.dimensions.y  # / 2

        ret = (
            object.location.x >= left
            and object.location.x <= right
            and object.location.y >= bottom
            and object.location.y <= top
        )

        return ret


ZONE = ZoneShape(Point2D(57, 57), Point2D(56, 57), 65535 / 2, 614.4)


def raycast(x: float, y: float, z: float):
    result, location, normal, index, object, matrix = C.scene.ray_cast(
        C.view_layer.depsgraph, (x, y, z), (0, 0, -1), distance=ZONE.max_height
    )
    return result, location.z, object


def set_origin_to_geometry(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
        C.view_layer.objects.active = o

    # bpy.ops.object.transform_apply(scale=True, location=False, rotation=False)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY")
    bpy.ops.object.select_all(action="DESELECT")


# ZONE_SIZE = ZONE.base_size * SCENE_SCALE
SRC_COLLECTION = "RNW_C_P"

excl_coll = D.collections.new(SRC_COLLECTION + "_excl")
C.scene.collection.children.link(excl_coll)
C.window.view_layer.layer_collection.children[excl_coll.name].exclude = True

geo_coll = D.collections.new(SRC_COLLECTION + "_geo")
C.scene.collection.children.link(geo_coll)
C.window.view_layer.layer_collection.children[geo_coll.name].exclude = True

src_coll = D.collections[SRC_COLLECTION]

# set origin of all objects in src collection to geometry center
set_origin_to_geometry(src_coll.objects)

# check if objects are contained inside the area
for o in src_coll.objects:
    if ZONE.is_object_partially_in_zone(o) or ZONE.is_object_origin_in_zone(o):
        continue
    src_coll.objects.unlink(o)
    excl_coll.objects.link(o)

C.scene.collection.objects.unlink(ZONE.bounding_box_object)

objects_hit = []

volume_idx = 0

volumes = {}

start = time.time()

volume_start = time.time()

T.start()

# while True:

# RAYCAST Z

needs_more_layers = False
for sx in range(ZONE.num_squares):
    for sy in range(ZONE.num_squares):
        for cx in range(ZONE.num_cells):
            for cy in range(ZONE.num_cells):
                cell_abs_pos = ZONE.get_cell_pos(sx, sy, cx, cy)
                cell_idx = ZONE.get_cell_index(sx, sy, cx, cy)

                hidden_objects = []
                z_cast = ZONE.max_height
                # if cell_idx in volumes:
                #     cells = volumes[cell_idx]
                #     z_cast = cells[len(cells) - 1]
                while True:
                    result, z, obj = raycast(cell_abs_pos.x, cell_abs_pos.y, z_cast)

                    if result:
                        if cell_idx in volumes:
                            volumes[cell_idx].append(z)
                        else:
                            volumes[cell_idx] = [z]

                        # needs_more_layers = True
                        # z_cast = z - 0.001
                        obj.hide_set(True)
                        hidden_objects.append(obj)

                    else:
                        if cell_idx not in volumes:
                            P.print(
                                f"Missed ({sx},{sy})->({cx},{cy}) | ({cell_abs_pos.x} : {cell_abs_pos.y})"
                            )

                        for hidden in hidden_objects:
                            hidden.hide_set(False)

                        break

        squares_per_sec = T.get_iterations_per_sec()
        squares_done = sy + (sx * ZONE.num_squares)
        squares_left = math.pow(ZONE.num_squares, 2) - squares_done
        time_left = squares_left / squares_per_sec
        P.reprint(
            f'[RAYCAST] Zone ({ZONE.pos.x}:{ZONE.pos.y}) | Square ({str(int(sx)).rjust(3, " ")}:{str(int(sy)).rjust(3, " ")}) | Speed: {squares_per_sec:.1f} sq/s\t| ETA: {Utils.time_convert(time_left)}'
        )
# if not needs_more_layers: break
# volume_idx += 1

# SORT
for sx in range(ZONE.num_squares):
    for sy in range(ZONE.num_squares):
        for cx in range(ZONE.num_cells):
            for cy in range(ZONE.num_cells):
                cell_idx = ZONE.get_cell_index(sx, sy, cx, cy)
                if cell_idx in volumes:
                    volumes[cell_idx].sort()
                    P.reprint(
                        f"Sorted cell {100*cell_idx/(math.pow(ZONE.num_squares,2)*math.pow(ZONE.num_cells,2)):.1f}"
                    )


# RAYCAST H
for sx in range(ZONE.num_squares):
    for sy in range(ZONE.num_squares):
        for cx in range(ZONE.num_cells):
            for cy in range(ZONE.num_cells):
                cell_idx = ZONE.get_cell_index(sx, sy, cx, cy)
                if cell_idx not in volumes:
                    continue

                z_values = volumes[cell_idx]

                cell_pos = ZONE.get_cell_pos(sx, sy, cx, cy)

                for i in range(len(z_values)):
                    z = z_values[i]
                    w = wrapped[cell_idx][i]

                    if w: z -= MAX_Z

                    result, found_z, obj = raycast(cell_pos.x, cell_pos.y, z + 0.001, 1)

                    # h = MAX_Z/2 - abs(z) if z != MAX_Z else MAX_Z/2

                    if result:
                        h = (found_z - abs(z))
                    else: h = MAX_Z/2
                    if h < 0: h += MAX_Z/2
                    if h > MAX_Z/2: h = MAX_Z/2

                    if cell_idx in heights:
                        heights[cell_idx].append(h)
                    else:
                        heights[cell_idx] = [h]

display = heights

# GENERATE
if len(volumes) != 0:
    T.start()

    volume_idx = 0
    while True:
        volume_name = f"Volume_{volume_idx}"
        volume_mesh = D.meshes.new(volume_name)
        volume_obj = D.objects.new(volume_name, volume_mesh)

        volume_points = []
        for sx in range(ZONE.num_squares):
            for sy in range(ZONE.num_squares):
                for cx in range(ZONE.num_cells):
                    for cy in range(ZONE.num_cells):
                        cell_abs_pos = ZONE.get_cell_pos(sx, sy, cx, cy)
                        cell_idx = ZONE.get_cell_index(sx, sy, cx, cy)

                        if cell_idx in volumes:
                            volumes_in_cell = volumes[cell_idx]
                            if len(volumes_in_cell) >= volume_idx + 1:
                                volume_points.append(
                                    Vector(
                                        (
                                            cell_abs_pos.x,
                                            cell_abs_pos.y,
                                            volumes_in_cell[volume_idx],
                                        )
                                    )
                                )

                squares_per_sec = T.get_iterations_per_sec()
                squares_done = sy + (sx * ZONE.num_squares)
                squares_left = math.pow(ZONE.num_squares, 2) - squares_done
                time_left = squares_left / squares_per_sec
                P.reprint(
                    f'[GENERATE] Zone ({ZONE.pos.x}:{ZONE.pos.y}) | Volume {volume_idx} | Square ({str(int(sx)).rjust(3, " ")}:{str(int(sy)).rjust(3, " ")}) | Speed: {squares_per_sec:.1f} sq/s\t| ETA: {Utils.time_convert(time_left)}'
                )

        if len(volume_points) == 0:
            break
        volume_mesh.from_pydata(volume_points, [], [])
        geo_coll.objects.link(volume_obj)
        volume_idx += 1

for obj in excl_coll.objects:
    excl_coll.objects.unlink(obj)
    src_coll.objects.link(obj)
end = time.time()

P.print(f"Total time: {Utils.time_convert(end - start)}")
