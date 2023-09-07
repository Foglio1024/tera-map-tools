import os
import bpy
import math
from lib.printer import Printer
from lib.map import Level
from lib.map import Terrain
from lib.scene_utils import SceneUtils
from lib.utils import Utils
from mathutils import Vector

P = Printer()

class MapImporter:
    def __init__(self, source_dir, map_name):
        self.source_dir = source_dir
        self.map_name = map_name
        self.level_dir = f"{source_dir}\\{map_name}"
        self.t3d_path = f"{self.level_dir}\\{map_name}.t3d"
        self.terrains_path = f"{self.level_dir}\\Terrains.txt"

    def __import_blocking_volumes(self, level):
        idx = 0
        for vol in level.blocking_volumes:
            idx += 1
            vol_mesh = bpy.data.meshes.new(f"BlockingVolume_{str(idx)}")
            vol_mesh.from_pydata(
                vol.brush_component.vertices,
                [],
                list(Utils.divide_chunks(vol.brush_component.indices, 3)),
            )
            vol_obj = bpy.data.objects.new(f"BlockingVolume_{str(idx)}", vol_mesh)
            vol.brush_component.apply_transform_to(vol_obj)
            self.map_coll.objects.link(vol_obj)

    def __build_actor(self, sma, idx, loaded_meshes, level):
        mesh_path = os.path.join(self.source_dir, level.name, sma.smc.mesh_path)

        if not os.path.exists(mesh_path):
            P.print(f"Cannot find mesh file in {mesh_path}")
        else:
            imported = None
            for loaded_name, loaded_path in loaded_meshes:
                if loaded_path == mesh_path:
                    # P.print(f'Copying {sma.label} <- {loaded_name}')
                    src = bpy.data.objects[loaded_name]
                    cp = src.copy()
                    cp.data = src.data
                    imported = cp
                    break

            if imported == None:
                # P.print(f'Importing {mesh_path}')
                bpy.ops.import_scene.psk(filepath=mesh_path)
                imported = bpy.context.scene.collection.objects[0]
                loaded_meshes.append((f"{sma.label}_{sma.index}", mesh_path))

            mesh_name = imported.data.name
            imported.name = f"{sma.label}_{sma.index}"
            imported.data.name = mesh_name

            sma.smc.apply_transform_to(imported)

            self.map_coll.objects.link(imported)

            # test_coll = SceneUtils.find_or_create_collection('test')
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

    def __generate_agg_geom(self, sma):
        idx = 0

        objects = []

        for convex_elem in sma.smc.agg_geoms:
            name = f"AG_{sma.label}_{str(idx)}"
            mesh = bpy.data.meshes.new(name)
            mesh.from_pydata(
                convex_elem.vertices,
                [],
                list(Utils.divide_chunks(convex_elem.indices, 3)),
            )
            obj = bpy.data.objects.new(name, mesh)

            sma.smc.agg_apply_transform_to(obj)
            self.map_coll.objects.link(obj)
            if obj.name in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.unlink(obj)

            objects.append(obj)

            # P.print(f"Created ConvexElem from {len(convex_elem.vertices)} vertices")

            idx += 1
        if len(objects) > 1:
            bpy.ops.object.select_all(action="DESELECT")
            for o in objects:
                o.select_set(True)
                bpy.context.view_layer.objects.active = o
            bpy.ops.object.join()

    def __import_actors(self, level, import_meshes = False, import_agg_geoms = True):
        loaded_meshes = []
        idx = 0

        for sma in level.actors:
            if "LM_MLOD" in sma.layers:
                continue

            if sma.smc.disable_collisions == True:
                continue
            
            if import_meshes:
                self.__build_actor(sma, idx, loaded_meshes, level)

            if import_agg_geoms:
                self.__generate_agg_geom(sma)

            P.reprint(f"Imported actor {idx + 1} of {len(level.actors)}")
            idx += 1

    def __import_terrains(self, terrains):
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

            solidify = obj.modifiers.new('Solidify', 'SOLIDIFY')
            solidify.thickness = 2000

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

    def import_map(self, import_actors = True, import_terrains = True, import_blocking_volumes = False):
        level = Level.read_from(self.t3d_path)
        terrains = Terrain.read_from(self.terrains_path)

        self.map_coll = SceneUtils.find_or_create_collection(level.name)

        if import_actors:
            self.__import_actors(level)
        
        if import_blocking_volumes:
            self.__import_blocking_volumes(level)
        
        if import_terrains:
            self.__import_terrains(terrains)

        SceneUtils.reframe(self.map_coll)

        for coll in self.map_coll.children:
            SceneUtils.reframe(coll)
