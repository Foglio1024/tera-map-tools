import struct
import array
import bpy
from mathutils import Vector
from bpy_extras.object_utils import object_data_add
import math
from operator import attrgetter
import xml.etree.ElementTree as ET

SIZE = 15360

class Zone:
    def __init__(self, squares, position, origin):
        self.squares = squares
        self.origin = origin
        self.position = position
        self.relative_position = Point2D(position.x - origin.x, position.y - origin.y)

    def contains_point(self, point2d):
        return (point2d.x / SIZE in range(self.relative_position.x, self.relative_position.x + 1) 
            and point2d.y / SIZE in range(self.relative_position.y, self.relative_position.y + 1))

class Square:
    def __init__(self, x, y, geoDataCount, volumes_per_cell):
        self.geoDataCount = geoDataCount
        self.volumes_per_cell = volumes_per_cell
        self.x = x
        self.y = y
        self.cells = []

    def add_cell(self, geodata):
        self.cells.append(geodata)
    
    def contains_point(self, point2d):
        return (point2d.x / SIZE in range(self.relative_position.x, self.relative_position.x + 1) 
            and point2d.y / SIZE in range(self.relative_position.y, self.relative_position.y + 1))

class Cell:
    def __init__(self, x, y, z, h, volume_idx):
        self.x = x
        self.y = y
        self.z = z
        self.h = h
        self.volume_idx = volume_idx

class Volume:
    def __init__(self, volume_idx):
        self.points = []
        self.index = volume_idx

class Point3D:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

class Point2D:
    def __init__(self, x, y):
        self.x = x
        self.y = y


# -------------------------------------------------------------- #

AREA_LIST_PATH = "E:\\TERA_DEV\\Server\\Executable\\Bin\\Datasheet\\AreaList.xml"
AREALIST = ET.parse(AREA_LIST_PATH).getroot()
CONTINENTS = AREALIST.findall("Continent")

def get_continent(id):
    ret = None
    for continent in CONTINENTS:
        if int(continent.attrib.get("id")) == id:
            ret = continent
            break

    return ret

def get_continent_origin(continent_id):
    continent = get_continent(continent_id)
    return Point2D(
        int(continent.attrib.get("originZoneX")),
        int(continent.attrib.get("originZoneY")),
    )


# def create_empties():
#     for square in squares[0:240]:
#         squareCollection = bpy.data.collections.new(f'Square_{square.x}_{square.y}')
#         bpy.context.scene.collection.children.link(squareCollection)

#         for cell in square.cells:
#             cellCollection = bpy.data.collections.new(f'Square_{square.x}_{square.y}__Cell_{cell.x}_{cell.y}')
#             squareCollection.children.link(cellCollection)

#             name = f'Cell{cell.volume_idx}_{square.x}_{square.y}_x{cell.x}_y{cell.y}_z{cell.z}_h{cell.h}'

#             empty = bpy.data.objects.new(name , None)
#             empty.empty_display_size = 0.1
#             empty.location.x = cell.x + square.x * 8
#             empty.location.y = cell.y + square.y * 8
#             empty.location.z = cell.z / 10
#             cellCollection.objects.link(empty)

#         # bpy.context.window.view_volume.volume_collection.children[cellCollection.name].exclude = True

#         print(f"Added square{square.x} {square.y}")


def create_volumes(squares, onlyFirst):
    volumes = []

    r = range(0, 20)  # todo: get max from squares
    if onlyFirst:
        r = range(0, 1)
    for volumeIdx in r:
        volume = Volume(volumeIdx)
        volumes.append(volume)
        for square in squares:
            for cell in square.cells:
                if cell.volume_idx == volumeIdx:
                    volume.points.append(
                        Point3D(
                            (16 / 10) * (cell.x + square.x * 8 + 0.5 - 120 * 8),
                            (16 / 10) * (cell.y + square.y * 8 + 0.5),
                            (cell.z) / 10,
                        )
                    )
    return volumes

def create_point_clouds(zone):
    volumes = create_volumes(zone.squares, False)

    for volume in volumes:
        if len(volume.points) == 0:
            continue
        mesh = bpy.data.meshes.new(f"Volume{volume.index}")

        vectors = []
        for point in volume.points:
            vectors.append(Vector([point.x, point.y, point.z]))

        mesh.from_pydata(vectors, [], [])

        obj = bpy.data.objects.new(f"Volume{volume.index}", mesh)
        bpy.context.scene.collection.objects.link(obj)

        scale = 0.1
        obj.scale.x *= scale
        obj.scale.y *= scale
        obj.scale.z *= scale

        obj.location.x = -(zone.position.x - zone.origin.x) * 15360 * 0.01
        obj.location.y = (zone.position.y - zone.origin.y + 1) * 15360 * 0.01

        obj.rotation_euler[2] = math.radians(90)

        # rotate and scale

        pivot = bpy.data.objects.new('Pivot', None)
        bpy.context.scene.collection.objects.link(pivot)
        obj.parent = pivot

        pivot.scale.x *= 4 * (-1)
        pivot.scale.y *= 4 * (-1)
        pivot.scale.z *= 4

        pivot.rotation_euler[2] = math.radians(90)

        bpy.context.evaluated_depsgraph_get().update()
        for child in pivot.children:
            pwm = child.matrix_world.copy()
            child.parent = None
            child.matrix_world = pwm

        bpy.data.objects.remove(bpy.data.objects[pivot.name])

def load_zone(position, origin):
    idx_path = f"E:\\TERA_DEV\\Server\\Topology\\x{position.x}y{position.y}.idx"
    geo_path = f"E:\\TERA_DEV\\Server\\Topology\\x{position.x}y{position.y}.geo"

    squares = []

    with open(idx_path, "rb") as idx:
        for squareY in range(120):
            for squareX in range(120):
                geoDataCount = array.array("I", idx.read(4))[0]
                volumes_per_cell = array.array("H", idx.read(128))
                squares.append(Square(squareX, squareY, geoDataCount, volumes_per_cell))

    with open(geo_path, "rb") as geo:
        for square in squares:
            for cellY in range(8):
                for cellX in range(8):
                    for volume_idx in range(square.volumes_per_cell[cellY * 8 + cellX]):
                        geoPair = array.array("H", geo.read(4))
                        square.add_cell(
                            Cell(cellX, cellY, geoPair[0], geoPair[1], volume_idx)
                        )

    return Zone(squares, position, origin)

def load_topo(continent_id, min_x, max_x, min_y, max_y):
    origin = get_continent_origin(continent_id)
    print(f"origin is {origin.x},{origin.y}")

    areas = get_continent(continent_id).findall("Area")
    zone_list = []

    for area in areas:
        for zones in area.findall("Zones"):
            for xml_zone in zones.findall("Zone"):
                zone_list.append(xml_zone)

    print(f"found {len(zone_list)} zones")

    curr = 0

    zones = []
    for xml_zone in zone_list:
        pos = Point2D(int(xml_zone.attrib.get("x")), int(xml_zone.attrib.get("y")))
        if pos.x < min_x: continue
        if pos.x > max_x: continue
        if pos.y < min_y: continue
        if pos.y > max_y: continue

        zone = load_zone(pos, origin)
        zones.append(zone)

        curr += 1
        print(f"[{curr}/{len(zone_list)}] Loaded zone {pos.x},{pos.y}")

    return zones

def create_topo(continent_id, min_x, max_x, min_y, max_y):
    zones = load_topo(continent_id, min_x, max_x, min_y, max_y)

    for zone in zones:
        create_point_clouds(zone)
    return


# -------------------------------------------------------------- #

CONTINENT = 4

create_topo(CONTINENT, 57, 57, 57, 57)
