import bpy
import math


class SceneUtils:
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
