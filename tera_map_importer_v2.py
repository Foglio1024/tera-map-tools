import os
import bpy
import math
from mathutils import Vector
from bpy_extras.object_utils import object_data_add


class Printer:
    def __init__(self):
        self.text = ""

    def reprint(self, text):
        empty = ""
        for c in self.text:
            empty += " "
        print(empty, end="\r")
        print(text, end="\r")
        self.text = text

    def print(self, text):
        self.reprint(text + "\n")

printer = Printer()

# -------------------------- set paths -----------------------------

SRC_DIR = 'E:\\TERA_DEV\\test_re_export\\cli'

MAP_NAME = 'RNW_C_P'

LEVEL_DIR = f'{SRC_DIR}\\{MAP_NAME}'
T3D_PATH = f'{LEVEL_DIR}\\{MAP_NAME}.t3d'
TERRAIN_PATH = f'{LEVEL_DIR}\\Terrains.txt'

# -------------------------------------------------------------------

def parse_name(line):
    return line[line.find("Name=") + 5 : -1].replace('\"', '')

def parse_class(line):
    class_idx = line.find('Class=')
    class_name = ''
    if class_idx != -1:
        class_name = line[class_idx:line.find('Name=')].replace('Class=/Script/Engine.', '').trim()

    return class_name

def parse_vector(line, name):
    split = line.replace(f'{name}=(', '').replace(')', '').split(',')

    ret = [] # x, y, z

    for part in split:
        value = float(part.split('=')[1])
        ret.append(value)
    
    return ret

def parse_mesh_path(line):
    ret =  line[line.find('\"'):].replace('\"', '').replace('\'', '') + ".psk"
    return ret.replace('/Game', 'StaticMeshes\\')

class Level:
    def __init__(self, name):
        self.actors = []
        self.name = name

    def read_from(file_path):

        printer.print(f'Loading level from {file_path}')

        h,t = os.path.split(file_path)

        ret = Level(t.replace('.t3d', ''))

        current_actor = None
        smc = None

        actor_labels = []

        lines = open(file_path, "r").readlines()
        printer.print(f'Read {len(lines)} lines')

        idx = 0
        for line in lines:
            line = line.strip()
            if line.startswith("Begin Actor"):
                actor_name = parse_name(line)
                current_actor = Actor(f'{actor_name}_{idx}', idx)
                idx = idx + 1
                actor_labels.append(actor_name)
                printer.reprint(f'Created Actor {actor_name}')
            elif line.startswith('ActorLabel'):
                current_actor.set_label(line)

            elif line.startswith("Begin Object"):
                obj_name = parse_name(line)
                smc = StaticMeshComponent(obj_name)
            elif line.startswith("End Object"):
                if smc.mesh_path == '': continue
                current_actor.smc = smc
            elif line.startswith("End Actor"):
                if current_actor.smc == None: continue
                if current_actor.label in actor_labels: continue
                ret.actors.append(current_actor)
                actor_labels.append(current_actor.label)
            else:
                if smc == None: continue
                smc.read_line(line)
        return ret

class Actor:
    def __init__(self, name, idx):
        self.name = name
        self.smc = None
        self.index = idx
        self.label = ''
    
    def set_label(self, line):
        self.label = line.split('=')[1].replace('\"', '')

class StaticMeshComponent:
    def __init__(self, name):
        self.name = name
        self.mesh_path = ''
        self.location = [0,0,0]
        self.rotation = [0,0,0]
        self.scale = [1,1,1]
    
    def read_line(self, line):
        if line.find('RelativeLocation') != -1:
            self.location = parse_vector(line, 'RelativeLocation')
        elif line.find('RelativeRotation') != -1:
            self.rotation = parse_vector(line, 'RelativeRotation')
        elif line.find('RelativeScale3D') != -1:
            self.scale = parse_vector(line, 'RelativeScale3D')
        elif line.find('StaticMesh=StaticMesh') != -1:
            self.mesh_path = parse_mesh_path(line)
            printer.reprint(f'Set mesh path: {self.mesh_path}')

class Terrain:
    def read_from(file_path):

        ret = []

        if not os.path.exists(file_path): return ret

        printer.print(f'Reading terrains from {file_path}')

        current_terrain = None
        lines = open(file_path, "r").readlines()

        for line in lines:
            if line.startswith('\t'):
                line = line.strip().replace(': ', '=')
                if 'Location' in line:
                    current_terrain.abs_location = parse_vector(line, 'Location')
                elif 'Scale' in line:
                    current_terrain.abs_scale = parse_vector(line, 'Scale')
            else:
                if current_terrain != None:
                    ret.append(current_terrain)

                current_terrain = Terrain(line.strip())

        # add last terrain
        if current_terrain != None:
            ret.append(current_terrain)

        base_path,h = os.path.split(file_path)
        for terrain in ret:
            setup_path = os.path.join(base_path, 'Terrains', terrain.map, terrain.name, 'Setup.txt')
            setup_lines = open(setup_path, "r").readlines()
            for line in setup_lines:
                if line.startswith('Location'):
                        terrain.rel_location = parse_vector(line, 'Location')
                if line.startswith('Scale'):
                        terrain.rel_scale = parse_vector(line, 'Scale')

        return ret
    
    def __init__(self, line):
        idx = line.find('_Terrain')
        self.map = line[:idx]
        self.name = line[idx + 1:]

# -------------------------------------------------------------------

def find_or_create_collection(coll_name):
    found = None
    for c in bpy.data.collections:
        if c.name == coll_name:
            found = c
    if found == None:
        found = bpy.data.collections.new(coll_name)
        bpy.context.scene.collection.children.link(found)

    return found

def set_transform(smc, obj):
    obj.scale.x = smc.scale[0]
    obj.scale.y = smc.scale[1] * (-1)
    obj.scale.z = smc.scale[2]

    obj.rotation_euler.x = math.radians(smc.rotation[2] * (-1))
    obj.rotation_euler.y = math.radians(smc.rotation[0])
    obj.rotation_euler.z = math.radians(smc.rotation[1])

    obj.location.x = smc.location[0]
    obj.location.y = smc.location[1]
    obj.location.z = smc.location[2]

def import_actors(level, map_coll, pivot):
    loaded_meshes = []
    idx = 0

    for sma in level.actors:
        idx += 1
        mesh_path = SRC_DIR + '\\' +level.name + '\\' + sma.smc.mesh_path #os.path.join(SRC_DIR, level.name, sma.smc.mesh_path)

        if not os.path.exists(mesh_path):
            printer.print(
                f"Cannot find mesh file in {mesh_path}"
            )
        else:
            imported = None
            for loaded_name, loaded_path in loaded_meshes:
                if loaded_path == mesh_path:
                    printer.reprint(f"Copying {sma.label} <- {loaded_name}")
                    src = bpy.data.objects[loaded_name]
                    cp = src.copy()
                    cp.data = src.data
                    imported = cp
                    break

            if imported == None:
                printer.reprint(f"Importing {mesh_path}")
                bpy.ops.import_scene.psk(filepath=mesh_path)
                imported = bpy.context.scene.collection.objects[0]
                loaded_meshes.append(
                    (f"{sma.label}_{sma.index}", mesh_path)
                )

            mesh_name = imported.data.name
            imported.name = f"{sma.label}_{sma.index}"
            imported.data.name = mesh_name
            set_transform(sma.smc, imported)

            imported.parent = pivot

            map_coll.objects.link(imported)
            # unlink object from main collection
            if imported.name in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.unlink(imported)

def import_terrains(terrains, map_coll, pivot):
    for ter in terrains:
        # create square
        terrain_mesh = bpy.data.meshes.new(f'{ter.map}_{ter.name}')
        points = []
        points.append(Vector([ 0    , 0    , 0 ]))
        points.append(Vector([-15360, 0    , 0 ]))
        points.append(Vector([-15360, 15360, 0 ]))
        points.append(Vector([ 0    , 15360, 0 ]))

        terrain_mesh.from_pydata(points, [[0, 1], [1, 2], [2, 3], [3, 0]], [[1,2,3,0]])
        terrain_mesh.uv_layers.new(name='HeightUV')
        obj = bpy.data.objects.new(terrain_mesh.name, terrain_mesh)

        # add subsurf mod
        subsurf = obj.modifiers.new("Subdivision", 'SUBSURF')
        subsurf.levels = 9 # todo: check
        subsurf.subdivision_type = 'SIMPLE'
        # add displacement mod
        displace = obj.modifiers.new("Displace", 'DISPLACE')
        # configure displacement mod
        displace.strength = 1310.5 # todo: why?
        displace.mid_level = 0.5

        # create texture for displacement
        tex = bpy.data.textures.new('HeightMap', 'IMAGE')
        displace.texture = tex
        displace.texture_coords = 'UV'

        # load image from height map file
        img = bpy.data.images.load(os.path.join(LEVEL_DIR, 'Terrains', ter.map, ter.name, 'HeightMap.png'))
        img.colorspace_settings.name = 'Non-Color'
        tex.image = img
        tex.extension = 'EXTEND'
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
        map_coll.objects.link(obj)

        # unlink object from main collection
        if obj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(obj)

        # parent to pivot
        obj.parent = pivot

def reframe(pivot):
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

def import_level(level, terrains):

    map_coll = find_or_create_collection(level.name)

    pivot = bpy.data.objects.new("Pivot", None)
    map_coll.objects.link(pivot)

    import_actors(level, map_coll, pivot)

    import_terrains(terrains, map_coll, pivot)

    reframe(pivot)


# -------------------------------------------------------------------

level = Level.read_from(T3D_PATH)
terrains = Terrain.read_from(TERRAIN_PATH)

import_level(level, terrains)