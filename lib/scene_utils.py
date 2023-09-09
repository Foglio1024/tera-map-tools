import bpy
import math
from bpy import context as C
from bpy import data as D


class SceneUtils:
    def find_or_create_collection(coll_name, link: bool = True):
        found = None
        for c in D.collections:
            if c.name == coll_name:
                found = c
        if found == None:
            found = D.collections.new(coll_name)
            if link:
                C.scene.collection.children.link(found)

        return found

    def reframe(collection, scale=0.01):
        pivot = D.objects.new("Pivot", None)

        for obj in collection.objects:
            obj.parent = pivot

        collection.objects.link(pivot)

        pivot.scale.x *= scale * (-1)
        pivot.scale.y *= scale
        pivot.scale.z *= scale

        pivot.rotation_euler[2] = math.radians(-90)

        C.evaluated_depsgraph_get().update()
        for child in pivot.children:
            pwm = child.matrix_world.copy()
            child.parent = None
            child.matrix_world = pwm

        D.objects.remove(D.objects[pivot.name])

    def set_origin_to_geometry(objects):
        bpy.ops.object.select_all(action="DESELECT")
        for o in objects:
            o.select_set(True)
            C.view_layer.objects.active = o

        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY")
        bpy.ops.object.select_all(action="DESELECT")

    def set_exclude_collection(coll_name: str, value: bool):
        C.window.view_layer.layer_collection.children[coll_name].exclude = value
