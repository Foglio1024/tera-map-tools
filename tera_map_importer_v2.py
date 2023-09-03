import os
import bpy
import math
from mathutils import Vector
from bpy_extras.object_utils import object_data_add


class Utils:
    def parse_name(line):
        return line[line.find("Name=") + 5 : -1].replace('"', "")

    def parse_class(line):
        class_idx = line.find("Class=")
        class_name = ""
        if class_idx != -1:
            class_name = (
                line[class_idx : line.find("Name=")]
                .replace("Class=/Script/Engine.", "")
                .trim()
            )

        return class_name

    def parse_vector(line, name):
        split = (
            line.replace(f"{name}=", "").replace("(", "").replace(")", "").split(",")
        )

        ret = []  # x, y, z

        for part in split:
            value = float(part.split("=")[1])
            ret.append(value)

        return ret

    def parse_mesh_path(line):
        ret = line[line.find('"') :].replace('"', "").replace("'", "") + ".psk"
        return ret.replace("/Game", "StaticMeshes\\")

    def find_or_create_collection(coll_name):
        found = None
        for c in bpy.data.collections:
            if c.name == coll_name:
                found = c
        if found == None:
            found = bpy.data.collections.new(coll_name)
            bpy.context.scene.collection.children.link(found)

        return found

    def reframe(collection):
        pivot = bpy.data.objects.new("Pivot", None)

        for obj in collection.objects:
            obj.parent = pivot

        collection.objects.link(pivot)

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


class Level:
    def __init__(self, name):
        self.actors = []
        self.name = name

    def read_from(file_path):
        print(f"Loading level from {file_path}")

        h, t = os.path.split(file_path)

        ret = Level(t.replace(".t3d", ""))

        current_actor = None
        current_scene_component = None
        current_static_mesh_component = None

        actor_labels = []

        lines = open(file_path, "r").readlines()
        print(f"Read {len(lines)} lines")

        idx = 0
        for line in lines:
            line = line.strip()
            if line.startswith("Begin Actor"):
                actor_name = Utils.parse_name(line)
                current_actor = StaticMeshActor(f"{actor_name}_{idx}", idx)
                idx = idx + 1
                actor_labels.append(actor_name)
                print(f"Created Actor {actor_name}")
            elif line.startswith("ActorLabel"):
                current_actor.set_label(line)

            elif line.startswith("Begin Object"):
                obj_name = Utils.parse_name(line)
                if obj_name == "RootTransform":
                    current_scene_component = SceneComponent(obj_name)
                elif obj_name.startswith("StaticMeshComponent"):
                    current_static_mesh_component = StaticMeshComponent(obj_name)
            elif line.startswith("End Object"):
                if (
                    current_static_mesh_component != None
                    and current_static_mesh_component.mesh_path != ""
                ):
                    current_actor.smc = current_static_mesh_component
                if current_scene_component != None:
                    current_actor.scene_component = current_scene_component

            elif line.startswith("End Actor"):
                if current_actor.smc == None:
                    continue
                if current_actor.label in actor_labels:
                    continue
                ret.actors.append(current_actor)
                actor_labels.append(current_actor.label)
                current_scene_component = None
                current_static_mesh_component = None
            else:
                if line.find("Layers(") != -1:
                    current_actor.layers.append(line.split("=")[1].replace('"', ""))

                if current_static_mesh_component != None:
                    current_static_mesh_component.read_line(line)

                if current_scene_component != None:
                    current_scene_component.read_line(line)
        return ret


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
            self.location = Utils.parse_vector(line, "RelativeLocation")
        elif line.find("RelativeRotation") != -1:
            self.rotation = Utils.parse_vector(line, "RelativeRotation")
        elif line.find("RelativeScale3D") != -1:
            self.scale = Utils.parse_vector(line, "RelativeScale3D")

    def apply_transform_to(self, obj):
        tmp = bpy.data.objects.new("tmp", None)
        obj.parent = tmp

        tmp.scale.x = self.scale[0]
        tmp.scale.y = self.scale[1] * (-1)
        tmp.scale.z = self.scale[2]

        tmp.rotation_euler.x = math.radians(self.rotation[2] * (-1))
        tmp.rotation_euler.y = math.radians(self.rotation[0])
        tmp.rotation_euler.z = math.radians(self.rotation[1])

        tmp.location.x = self.location[0]
        tmp.location.y = self.location[1]
        tmp.location.z = self.location[2]

        bpy.context.evaluated_depsgraph_get().update()

        pwm = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = pwm

        bpy.data.objects.remove(bpy.data.objects[tmp.name])


class StaticMeshComponent:
    def __init__(self, name):
        self.name = name
        self.mesh_path = ""
        self.location = [0, 0, 0]
        self.rotation = [0, 0, 0]
        self.scale = [1, 1, 1]
        self.disable_collisions = False

    def read_line(self, line):
        if "RelativeLocation" in line:
            self.location = Utils.parse_vector(line, "RelativeLocation")
        elif "RelativeRotation" in line:
            self.rotation = Utils.parse_vector(line, "RelativeRotation")
        elif "RelativeScale3D" in line:
            self.scale = Utils.parse_vector(line, "RelativeScale3D")
        elif "StaticMesh=StaticMesh" in line:
            self.mesh_path = Utils.parse_mesh_path(line)
        elif "CollisionEnabled=NoCollision" in line:
            self.disable_collisions = True

    def apply_transform_to(self, obj):
        obj.scale.x = self.scale[0]
        obj.scale.y = self.scale[1] * (-1)
        obj.scale.z = self.scale[2]

        obj.rotation_euler.x = math.radians(self.rotation[2] * (-1))
        obj.rotation_euler.y = math.radians(self.rotation[0])
        obj.rotation_euler.z = math.radians(self.rotation[1])

        obj.location.x = self.location[0]
        obj.location.y = self.location[1]
        obj.location.z = self.location[2]


class Terrain:
    def read_from(file_path):
        ret = []

        if not os.path.exists(file_path):
            return ret

        print(f"Reading terrains from {file_path}")

        current_terrain = None
        lines = open(file_path, "r").readlines()

        for line in lines:
            if line.startswith("\t"):
                line = line.strip().replace(": ", "=")
                if "Location" in line:
                    current_terrain.abs_location = Utils.parse_vector(line, "Location")
                elif "Scale" in line:
                    current_terrain.abs_scale = Utils.parse_vector(line, "Scale")
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
                    terrain.rel_location = Utils.parse_vector(line, "Location")
                if line.startswith("Scale"):
                    terrain.rel_scale = Utils.parse_vector(line, "Scale")

        return ret

    def __init__(self, line):
        idx = line.find("_Terrain")
        self.map = line[:idx]
        self.name = line[idx + 1 :]


class MapImporter:
    def __init__(self, source_dir, map_name):
        self.source_dir = source_dir
        self.map_name = map_name
        self.level_dir = f"{source_dir}\\{map_name}"
        self.t3d_path = f"{self.level_dir}\\{map_name}.t3d"
        self.terrains_path = f"{self.level_dir}\\Terrains.txt"

    def import_actors(self, level):
        loaded_meshes = []
        idx = 0

        for sma in level.actors:
            if "LM_MLOD" in sma.layers:
                continue

            if sma.smc.disable_collisions == True: 
                continue

            idx += 1
            mesh_path = os.path.join(self.source_dir, level.name, sma.smc.mesh_path)

            if not os.path.exists(mesh_path):
                print(f"Cannot find mesh file in {mesh_path}")
            else:
                imported = None
                for loaded_name, loaded_path in loaded_meshes:
                    if loaded_path == mesh_path:
                        # print(f'Copying {sma.label} <- {loaded_name}')
                        src = bpy.data.objects[loaded_name]
                        cp = src.copy()
                        cp.data = src.data
                        imported = cp
                        break

                if imported == None:
                    # print(f'Importing {mesh_path}')
                    bpy.ops.import_scene.psk(filepath=mesh_path)
                    imported = bpy.context.scene.collection.objects[0]
                    loaded_meshes.append((f"{sma.label}_{sma.index}", mesh_path))

                mesh_name = imported.data.name
                imported.name = f"{sma.label}_{sma.index}"
                imported.data.name = mesh_name

                sma.smc.apply_transform_to(imported)

                # test_coll = Utils.find_or_create_collection('test')
                # if test_coll.name not in self.map_coll.children:
                #     self.map_coll.children.link(test_coll)
                #     bpy.context.scene.collection.children.unlink(test_coll)

                if sma.scene_component != None:
                    sma.scene_component.apply_transform_to(imported)
                
                # if sma.smc.disable_collisions == True: 
                #     test_coll.objects.link(imported)
                # else:
                #     self.map_coll.objects.link(imported)

                # unlink object from main collection
                if imported.name in bpy.context.scene.collection.objects:
                    bpy.context.scene.collection.objects.unlink(imported)

    def import_terrains(self, terrains):
        for ter in terrains:
            # create square
            terrain_mesh = bpy.data.meshes.new(f"{ter.map}_{ter.name}")
            points = []
            points.append(Vector([0, 0, 0]))
            points.append(Vector([-15360, 0, 0]))
            points.append(Vector([-15360, 15360, 0]))
            points.append(Vector([0, 15360, 0]))

            terrain_mesh.from_pydata(
                points, [[0, 1], [1, 2], [2, 3], [3, 0]], [[1, 2, 3, 0]]
            )
            terrain_mesh.uv_layers.new(name="HeightUV")
            obj = bpy.data.objects.new(terrain_mesh.name, terrain_mesh)

            # add subsurf mod
            subsurf = obj.modifiers.new("Subdivision", "SUBSURF")
            subsurf.levels = 9  # todo: check
            subsurf.subdivision_type = "SIMPLE"
            # add displacement mod
            displace = obj.modifiers.new("Displace", "DISPLACE")
            # configure displacement mod
            displace.strength = 1310.5  # todo: why?
            displace.mid_level = 0.5

            # create texture for displacement
            tex = bpy.data.textures.new("HeightMap", "IMAGE")
            displace.texture = tex
            displace.texture_coords = "UV"

            # load image from height map file
            img = bpy.data.images.load(
                os.path.join(
                    self.level_dir, "Terrains", ter.map, ter.name, "HeightMap.png"
                )
            )
            img.colorspace_settings.name = "Non-Color"
            tex.image = img
            tex.extension = "EXTEND"
            tex.use_interpolation = False

            # move square to raw position
            obj.location.x = ter.rel_location[0]
            obj.location.y = ter.rel_location[1]
            obj.location.z = ter.rel_location[2]

            obj.scale.x = 4
            obj.scale.y = 4
            obj.scale.z = -100

            obj.rotation_euler.z = math.radians(-90)

            # link to collection
            self.map_coll.objects.link(obj)

            # unlink object from main collection
            if obj.name in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.unlink(obj)

    def import_level(self):
        level = Level.read_from(self.t3d_path)
        terrains = Terrain.read_from(self.terrains_path)

        self.map_coll = Utils.find_or_create_collection(level.name)

        self.import_actors(level)
        self.import_terrains(terrains)

        Utils.reframe(self.map_coll)

        for coll in self.map_coll.children:
            Utils.reframe(coll)


# -------------------------------------------------------------------

importer = MapImporter(
    source_dir="E:\\TERA_DEV\\test_re_export\\cli", map_name="RNW_C_P"
)
importer.import_level()
