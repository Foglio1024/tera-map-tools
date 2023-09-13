import math
import struct
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
from lib.topology import Node
from lib.printer import Printer
from lib.time_tracker import TimeTracker
from lib.utils import Utils
from lib.scene_utils import SceneUtils
import lib.globals

P = Printer()
T = TimeTracker()

MAX_Z = 65535 / 25

SCENE_SCALE = C.scene.unit_settings.scale_length


class GeoGenerator:
    def __init__(self, src_collection_name: str, pos: Point2D, origin: Point2D):
        self.num_squares: int = 120
        self.num_cells: int = 8

        self.pos = pos
        self.origin = origin
        self.max_height = (65535 / 2) / SCENE_SCALE
        self.base_size = lib.globals.BASE_ZONE_SIZE

        self.rel_pos = Point2D(pos.x - origin.x, pos.y - origin.y)
        self.size = self.base_size * SCENE_SCALE
        self.square_size = self.size / self.num_squares

        self.src_coll_name = src_collection_name

    def setup(self):
        self.__create_bounding_box()

        self.__excl_coll = SceneUtils.find_or_create_collection(
            f"{self.src_coll_name}_hidden"
        )
        SceneUtils.set_exclude_collection(self.__excl_coll.name, True)

        self.__geo_coll = SceneUtils.find_or_create_collection(
            f"{self.src_coll_name}_geo"
        )
        SceneUtils.set_exclude_collection(self.__geo_coll.name, True)

        self.__src_coll = D.collections[self.src_coll_name]

        SceneUtils.set_origin_to_geometry(self.__src_coll.objects)

        # check if objects are contained inside the area
        for o in self.__src_coll.objects:
            if self.__is_object_partially_in_zone(o) or self.__is_object_origin_in_zone(
                o
            ):
                continue
            self.__src_coll.objects.unlink(o)
            self.__excl_coll.objects.link(o)

        C.scene.collection.objects.unlink(self.bounding_box_object)

    def __create_bounding_box(self):
        bb_mesh = D.meshes.new(f"{self.src_coll_name}_bb")
        bb_obj = D.objects.new(f"{self.src_coll_name}_bb", bb_mesh)
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

    def __get_square_pos(self, sx: int, sy: int):
        return Point2D(
            (sx * self.square_size + self.rel_pos.y * self.size) / SCENE_SCALE,
            (sy * self.square_size + self.rel_pos.x * self.size) / SCENE_SCALE,
        )

    def __get_cell_pos(self, sx: int, sy: int, cx: int, cy: int):
        sq_pos = self.__get_square_pos(sx, sy)
        cell_rel_pos = Point2D(
            (cx + 0.5) * ((self.square_size / self.num_cells) / SCENE_SCALE),
            (cy + 0.5) * ((self.square_size / self.num_cells) / SCENE_SCALE),
        )

        return Point2D(
            round(cell_rel_pos.x + sq_pos.x, 3), round(cell_rel_pos.y + sq_pos.y, 3)
        )

    def __get_cell_index(self, sx: int, sy: int, cx: int, cy: int):
        return int(
            (self.num_cells * cx)
            + cy
            + (sx * self.num_squares + sy) * int(math.pow(self.num_cells, 2))
        )

    def __is_object_partially_in_zone(self, object):
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

    def __is_object_origin_in_zone(self, object):
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

    def __raycast(self, x: float, y: float, z: float, z_dir: float = -1):
        result, location, normal, index, object, matrix = C.scene.ray_cast(
            C.view_layer.depsgraph, (x, y, z), (0, 0, z_dir)
        )
        return result, location.z, object

    def generate_cells(self):
        T.start()

        self.volumes = {}  # cell_idx : z_values
        self.wrapped = {}  # cell_idx : neg_z_value

        # raycast
        for sx in range(self.num_squares):
            for sy in range(self.num_squares):
                for cx in range(self.num_cells):
                    for cy in range(self.num_cells):
                        cell_abs_pos = self.__get_cell_pos(sx, sy, cx, cy)
                        cell_idx = self.__get_cell_index(sx, sy, cx, cy)

                        hidden_objects = []
                        z_cast = self.max_height
                        while True:
                            result, z, obj = self.__raycast(
                                cell_abs_pos.x, cell_abs_pos.y, z_cast
                            )
                            wrap = 0
                            if result:
                                if z < 0:
                                    wrap = z
                                    z = MAX_Z + z

                                if cell_idx in self.volumes:
                                    if (
                                        self.volumes[cell_idx][
                                            len(self.volumes[cell_idx]) - 1
                                        ]
                                        - z
                                        > 1
                                    ):
                                        self.volumes[cell_idx].append(z)
                                        self.wrapped[cell_idx].append(wrap)
                                else:
                                    self.volumes[cell_idx] = [z]
                                    self.wrapped[cell_idx] = [wrap]

                                # z_cast = z - 0.001
                                obj.hide_set(True)
                                hidden_objects.append(obj)

                            else:
                                if cell_idx not in self.volumes:
                                    P.print(
                                        f"Missed ({sx},{sy})->({cx},{cy}) | ({cell_abs_pos.x} : {cell_abs_pos.y})"
                                    )
                                # todo: add point if missed? for dungeons with no terrain
                                for hidden in hidden_objects:
                                    hidden.hide_set(False)

                                break

                squares_per_sec = T.get_iterations_per_sec()
                squares_done = sy + (sx * self.num_squares)
                squares_left = math.pow(self.num_squares, 2) - squares_done
                time_left = squares_left / squares_per_sec
                P.reprint(
                    f'RAYCAST Z > Zone ({self.pos.x}:{self.pos.y}) | Square ({str(int(sx)).rjust(3, " ")}:{str(int(sy)).rjust(3, " ")}) | {squares_per_sec:.1f} sq/s | ETA: {Utils.time_convert(time_left)}'
                )

        # sort
        T.start()
        for sx in range(self.num_squares):
            for sy in range(self.num_squares):
                for cx in range(self.num_cells):
                    for cy in range(self.num_cells):
                        cell_idx = self.__get_cell_index(sx, sy, cx, cy)
                        if cell_idx in self.volumes:
                            self.volumes[cell_idx].sort()
                            self.wrapped[cell_idx].sort()

                squares_per_sec = T.get_iterations_per_sec()
                squares_done = sy + (sx * self.num_squares)
                squares_left = math.pow(self.num_squares, 2) - squares_done
                time_left = squares_left / squares_per_sec
                P.reprint(
                    f'SORT > Zone ({self.pos.x}:{self.pos.y}) | Square ({str(int(sx)).rjust(3, " ")}:{str(int(sy)).rjust(3, " ")}) | {squares_per_sec:.1f} sq/s | ETA: {Utils.time_convert(time_left)}'
                )

    def generate_heights(self):
        T.start()
        self.heights = {}
        for sx in range(self.num_squares):
            for sy in range(self.num_squares):
                for cx in range(self.num_cells):
                    for cy in range(self.num_cells):
                        cell_idx = self.__get_cell_index(sx, sy, cx, cy)
                        if cell_idx not in self.volumes:
                            continue

                        z_values = self.volumes[cell_idx]

                        cell_pos = self.__get_cell_pos(sx, sy, cx, cy)

                        for i in range(len(z_values)):
                            z = z_values[i]
                            w = self.wrapped[cell_idx][i]

                            if w != 0:
                                z -= MAX_Z

                            result, found_z, obj = self.__raycast(
                                cell_pos.x, cell_pos.y, z + 0.001, 1
                            )

                            if result:
                                h = found_z - abs(z)
                            else:
                                h = MAX_Z / 2

                            if h < 0:
                                h += MAX_Z / 2

                            if h > MAX_Z / 2:
                                h = MAX_Z / 2

                            if cell_idx in self.heights:
                                self.heights[cell_idx].append(h)
                            else:
                                self.heights[cell_idx] = [h]

                squares_per_sec = T.get_iterations_per_sec()
                squares_done = sy + (sx * self.num_squares)
                squares_left = math.pow(self.num_squares, 2) - squares_done
                time_left = squares_left / squares_per_sec
                P.reprint(
                    f'RAYCAST H > Zone ({self.pos.x}:{self.pos.y}) | Square ({str(int(sx)).rjust(3, " ")}:{str(int(sy)).rjust(3, " ")}) | {squares_per_sec:.1f} sq/s | ETA: {Utils.time_convert(time_left)}'
                )

    def draw(self, display: str):
        if len(self.volumes) != 0:
            T.start()

            source = self.volumes
            if display == "h":
                source = self.heights

            volume_idx = 0
            while True:
                volume_name = f"x{self.pos.x}y{self.pos.y}_{volume_idx}"
                volume_mesh = D.meshes.new(volume_name)
                volume_obj = D.objects.new(volume_name, volume_mesh)

                volume_points = []
                for sx in range(self.num_squares):
                    for sy in range(self.num_squares):
                        for cx in range(self.num_cells):
                            for cy in range(self.num_cells):
                                cell_abs_pos = self.__get_cell_pos(sx, sy, cx, cy)
                                cell_idx = self.__get_cell_index(sx, sy, cx, cy)

                                if cell_idx in source:
                                    volumes_in_cell = source[cell_idx]
                                    if len(volumes_in_cell) >= volume_idx + 1:
                                        z = volumes_in_cell[volume_idx]
                                        w = self.wrapped[cell_idx][volume_idx]
                                        if w != 0:
                                            z -= MAX_Z
                                        volume_points.append(
                                            Vector(
                                                (
                                                    cell_abs_pos.x,
                                                    cell_abs_pos.y,
                                                    z,
                                                )
                                            )
                                        )

                        squares_per_sec = T.get_iterations_per_sec()
                        squares_done = sy + (sx * self.num_squares)
                        squares_left = math.pow(self.num_squares, 2) - squares_done
                        time_left = squares_left / squares_per_sec
                        P.reprint(
                            f'DRAW > Zone ({self.pos.x}:{self.pos.y}) | Volume {volume_idx} | Square ({str(int(sx)).rjust(3, " ")}:{str(int(sy)).rjust(3, " ")}) | {squares_per_sec:.1f} sq/s | ETA: {Utils.time_convert(time_left)}'
                        )

                if len(volume_points) == 0:
                    break
                volume_mesh.from_pydata(volume_points, [], [])
                self.__geo_coll.objects.link(volume_obj)
                volume_idx += 1

    def cleanup(self):
        for obj in self.__excl_coll.objects:
            self.__excl_coll.objects.unlink(obj)
            self.__src_coll.objects.link(obj)

        D.collections.remove(self.__excl_coll)
        C.window.view_layer.layer_collection.children[
            self.__geo_coll.name
        ].exclude = False

    def export(self, output_path: str):
        # todo : max vol idx
        T.start()
        idx_file = open(f"{output_path}/x{self.pos.x}y{self.pos.y}.idx", "wb")
        geo_file = open(f"{output_path}/x{self.pos.x}y{self.pos.y}.geo", "wb")
        for sy in range(self.num_squares):
            for sx in range(self.num_squares):
                volumes_amount = 0
                volumes_per_cell = []

                for cy in range(self.num_cells):
                    for cx in range(self.num_cells):
                        cell_idx = self.__get_cell_index(sx, sy, cx, cy)
                        z_values = self.volumes[cell_idx]
                        volumes_amount += len(z_values)
                        volumes_per_cell.append(len(z_values))
                        for i in range(len(z_values)):
                            z = z_values[i]
                            h = self.heights[cell_idx][i]

                            try:
                                geo_file.write(struct.pack("H", int(z) * 25))
                            except:
                                P.print(f"{cell_idx} ERROR on Z:{z}")
                            try:
                                geo_file.write(struct.pack("H", int(h) * 25))
                            except:
                                P.print(f"{cell_idx} ERROR on H:{h}")

                idx_file.write(struct.pack("I", volumes_amount))
                for vpc in volumes_per_cell:
                    idx_file.write(struct.pack("H", vpc))

                squares_per_sec = T.get_iterations_per_sec()
                squares_done = sy + (sx * self.num_squares)
                squares_left = math.pow(self.num_squares, 2) - squares_done
                time_left = squares_left / squares_per_sec
                P.reprint(
                    f'EXPORT > Zone ({self.pos.x}:{self.pos.y}) | Square ({str(int(sx)).rjust(3, " ")}:{str(int(sy)).rjust(3, " ")}) | {squares_per_sec:.1f} sq/s | ETA: {Utils.time_convert(time_left)}'
                )

        idx_file.close()
        geo_file.close()





def generate_geo(
    map_name: str,
    map_pos: Point2D,
    map_origin: Point2D,
    export_path: str,
    draw_z: bool = True,
    draw_h: bool = False,
):
    start = time.time()
    generator = GeoGenerator(map_name, map_pos, map_origin)
    generator.setup()
    try:
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
    except:
        pass
    generator.generate_cells()
    generator.generate_heights()
    if draw_z:
        generator.draw("z")
    if draw_h:
        generator.draw("h")
    generator.cleanup()
    generator.export(export_path)

    end = time.time()

    P.print(
        f"{generator.src_coll_name} @ x{generator.pos.x}y{generator.pos.y} done in: {Utils.time_convert(end - start)} | using {generator.num_cells}x{generator.num_cells} cells, {generator.num_squares}x{generator.num_squares} squares"
    )
