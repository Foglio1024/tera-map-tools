import bpy
import math
from lib.t3d_utils import T3DUtils
from lib.printer import Printer

import os

from mathutils import Vector

P = Printer()


class StaticMeshActor:
    def __init__(self, name, idx):
        self.name = name
        self.smc = None
        self.scene_component = None
        self.index = idx
        self.label = ""
        self.layers = []

    def set_label(self, line):
        self.label = line.split("=")[1].replace('"', "")


class SceneComponent:
    def __init__(self, name):
        self.name = name

    def read_line(self, line):
        if line.find("RelativeLocation") != -1:
            self.location = T3DUtils.parse_vector(line, "RelativeLocation")
        elif line.find("RelativeRotation") != -1:
            self.rotation = T3DUtils.parse_vector(line, "RelativeRotation")
        elif line.find("RelativeScale3D") != -1:
            self.scale = T3DUtils.parse_vector(line, "RelativeScale3D")

    def apply_transform_to(self, obj):
        tmp = bpy.data.objects.new("tmp", None)
        obj.parent = tmp

        tmp.scale.x = self.scale.x
        tmp.scale.y = self.scale.y * (-1)
        tmp.scale.z = self.scale.z

        tmp.rotation_euler.x = math.radians(self.rotation.z * (-1))
        tmp.rotation_euler.y = math.radians(self.rotation.x)
        tmp.rotation_euler.z = math.radians(self.rotation.y)

        tmp.location = self.location

        bpy.context.evaluated_depsgraph_get().update()

        pwm = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = pwm

        bpy.data.objects.remove(bpy.data.objects[tmp.name])


class StaticMeshComponent:
    def __init__(self, name):
        self.name = name
        self.mesh_path = ""
        self.location = Vector([0, 0, 0])
        self.rotation = Vector([0, 0, 0])
        self.scale = Vector([1, 1, 1])
        self.disable_collisions = False
        self.agg_geoms = []

    def read_line(self, line):
        if "RelativeLocation" in line:
            self.location = T3DUtils.parse_vector(line, "RelativeLocation")
        elif "RelativeRotation" in line:
            self.rotation = T3DUtils.parse_vector(line, "RelativeRotation")
        elif "RelativeScale3D" in line:
            self.scale = T3DUtils.parse_vector(line, "RelativeScale3D")
        elif "StaticMesh=StaticMesh" in line:
            self.mesh_path = T3DUtils.parse_mesh_path(line)
        elif "CollisionEnabled=NoCollision" in line:
            self.disable_collisions = True
        elif "AggGeom" in line:
            self.parse_agg_geom(line)

    def parse_agg_geom(self, line):
        line = line.replace("AggGeom=(", "")[:-1]
        count = line.count("VertexData")

        for _ in range(count):
            convex_elem = ConvexElem()

            vertex_data_start = line.find("VertexData")
            idx_data_start = line.find("IndexData")

            vertex_data = line[
                vertex_data_start + len("VertexData=(") : idx_data_start - len("),")
            ]
            vertex_data = vertex_data.replace("),", ")|")

            str_vertices = vertex_data.split("|")

            for str_vert in str_vertices:
                # P.print(str_vert)
                convex_elem.vertices.append(T3DUtils.parse_vector(str_vert, ""))

            idx_elem_box = line.find("ElemBox=")
            idx_data = line[
                idx_data_start + len("IndexData=(") : idx_elem_box - len("),")
            ].split(",")
            idx_data.reverse()
            for str_idx in idx_data:
                # P.print(str_idx)
                convex_elem.indices.append(int(str_idx))

            self.agg_geoms.append(convex_elem)

            line = line[idx_elem_box + len("ElemBox=") :]

    def apply_transform_to(self, obj):
        obj.scale.x = self.scale.x
        obj.scale.y = self.scale.y * (-1)
        obj.scale.z = self.scale.z

        obj.rotation_euler.x = math.radians(self.rotation.z * (-1))
        obj.rotation_euler.y = math.radians(self.rotation.x)
        obj.rotation_euler.z = math.radians(self.rotation.y)

        obj.location = self.location

    def agg_apply_transform_to(self, obj):
        obj.scale = self.scale

        obj.rotation_euler.x = math.radians(self.rotation.z * (-1))
        obj.rotation_euler.y = math.radians(self.rotation.x * (-1))
        obj.rotation_euler.z = math.radians(self.rotation.y)

        obj.location = self.location


class Level:
    def __init__(self, name):
        self.actors = []
        self.blocking_volumes = []
        self.name = name

    def read_from(file_path):
        P.print(f"Loading level from {file_path}")

        h, t = os.path.split(file_path)

        ret = Level(t.replace(".t3d", ""))

        current_staticmeshactor = None
        current_scene_component = None
        current_static_mesh_component = None
        # current_blockingvolumeactor = None
        # current_brush_component = None

        actor_labels = []

        lines = open(file_path, "r").readlines()
        P.print(f"Read {len(lines)} lines")

        idx = 0
        for line in lines:
            line = line.strip()
            if line.startswith("Begin Actor"):
                actor_name = T3DUtils.parse_name(line)
                actor_class = T3DUtils.parse_class(line)

                if actor_class == "StaticMeshActor":
                    current_staticmeshactor = StaticMeshActor(
                        f"{actor_name}_{idx}", idx
                    )
                # elif actor_class == 'BlockingVolume':
                #     current_blockingvolumeactor = BlockingVolumeActor(f"{actor_name}_{idx}")
                idx = idx + 1
                actor_labels.append(actor_name)
                P.reprint(f"Created Actor {actor_name}")

            elif line.startswith("ActorLabel") and current_staticmeshactor is not None:
                current_staticmeshactor.set_label(line)

            elif line.startswith("Begin Object"):
                obj_name = T3DUtils.parse_name(line)
                if obj_name == "RootTransform":
                    current_scene_component = SceneComponent(obj_name)
                elif obj_name.startswith("StaticMeshComponent"):
                    current_static_mesh_component = StaticMeshComponent(obj_name)
                # elif obj_name.startswith('BrushComponent'):
                #     current_brush_component = BrushComponent(obj_name)

            elif line.startswith("End Object"):
                if (
                    current_static_mesh_component != None
                    and current_staticmeshactor is not None
                    and current_static_mesh_component.mesh_path != ""
                ):
                    current_staticmeshactor.smc = current_static_mesh_component
                if (
                    current_staticmeshactor is not None
                    and current_scene_component != None
                ):
                    current_staticmeshactor.scene_component = current_scene_component
                # if current_brush_component != None and current_blockingvolumeactor != None:
                #     current_blockingvolumeactor.brush_component = current_brush_component

            elif line.startswith("End Actor"):
                if (
                    current_staticmeshactor is not None
                    and current_staticmeshactor.smc != None
                    and current_staticmeshactor.label not in actor_labels
                ):
                    ret.actors.append(current_staticmeshactor)
                    actor_labels.append(current_staticmeshactor.label)
                    current_scene_component = None
                    current_static_mesh_component = None
                    current_staticmeshactor = None
                # if current_blockingvolumeactor != None:
                #     ret.blocking_volumes.append(current_blockingvolumeactor)
                #     current_blockingvolumeactor = None

            else:
                if "Layers(" in line and current_staticmeshactor is not None:
                    current_staticmeshactor.layers.append(
                        line.split("=")[1].replace('"', "")
                    )

                if current_static_mesh_component != None:
                    current_static_mesh_component.read_line(line)

                if current_scene_component != None:
                    current_scene_component.read_line(line)

                # if current_brush_component != None:
                #     current_brush_component.read_line(line)
        return ret


class BrushComponent:
    def __init__(self, name):
        self.name = name
        self.vertices = []
        self.indices = []
        self.location = Vector([0, 0, 0])

    def read_line(self, line):
        if "AggGeom" in line:
            self.parse_agg_geom(line)
        if "RelativeLocation" in line:
            self.location = T3DUtils.parse_vector(line, "RelativeLocation")

    def apply_transform_to(self, obj: bpy.types.Object):
        obj.scale.y = obj.scale.y * (-1)

        obj.location = self.location

    def parse_agg_geom(self, line):
        line = line.replace("AggGeom=(", "")[:-1]
        count = line.count("VertexData")

        if count > 1:
            raise Exception("More than one ConvexElem found!")

        vertex_data_start = line.find("VertexData")
        idx_data_start = line.find("IndexData")

        vertex_data = line[
            vertex_data_start + len("VertexData=(") : idx_data_start - len("),")
        ]
        vertex_data = vertex_data.replace("),", ")|")

        str_vertices = vertex_data.split("|")

        for str_vert in str_vertices:
            # P.print(str_vert)
            self.vertices.append(T3DUtils.parse_vector(str_vert, ""))

        idx_data = line[
            idx_data_start + len("IndexData=(") : line.find("ElemBox") - len("),")
        ].split(",")

        for str_idx in idx_data:
            # P.print(str_idx)
            self.indices.append(int(str_idx))


class BlockingVolumeActor:
    def __init__(self, name):
        self.name = name
        self.brush_component = None


class ConvexElem:
    def __init__(self):
        self.vertices = []
        self.indices = []


class Terrain:
    def read_from(file_path):
        ret = []

        if not os.path.exists(file_path):
            return ret

        P.print(f"Reading terrains from {file_path}")

        current_terrain = None
        lines = open(file_path, "r").readlines()

        for line in lines:
            if line.startswith("\t"):
                line = line.strip().replace(": ", "=")
                if "Location" in line:
                    current_terrain.abs_location = T3DUtils.parse_vector(
                        line, "Location"
                    )
                elif "Scale" in line:
                    current_terrain.abs_scale = T3DUtils.parse_vector(line, "Scale")
            else:
                if current_terrain != None:
                    ret.append(current_terrain)

                current_terrain = Terrain(line.strip())

        # add last terrain
        if current_terrain != None:
            ret.append(current_terrain)

        base_path, h = os.path.split(file_path)
        for terrain in ret:
            setup_path = os.path.join(
                base_path, "Terrains", terrain.map, terrain.name, "Setup.txt"
            )
            setup_lines = open(setup_path, "r").readlines()
            for line in setup_lines:
                if line.startswith("Location"):
                    terrain.rel_location = T3DUtils.parse_vector(line, "Location")
                if line.startswith("Scale"):
                    terrain.rel_scale = T3DUtils.parse_vector(line, "Scale")

        return ret

    def __init__(self, line: str):
        idx = line.find("_Terrain")
        self.map = line[:idx]
        self.name = line[idx + 1 :]
