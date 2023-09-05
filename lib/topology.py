SIZE = 15360

class Point2D:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Point3D:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


class Volume:
    def __init__(self, volume_idx):
        self.points = []
        self.index = volume_idx


class Cell:
    def __init__(self, x, y, z, h, volume_idx):
        self.x = x
        self.y = y
        self.z = z
        self.h = h
        self.volume_idx = volume_idx


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


class Zone:
    def __init__(self, squares, position, origin):
        self.squares = squares
        self.origin = origin
        self.position = position
        self.relative_position = Point2D(position.x - origin.x, position.y - origin.y)

    def contains_point(self, point2d):
        return (point2d.x / SIZE in range(self.relative_position.x, self.relative_position.x + 1)
            and point2d.y / SIZE in range(self.relative_position.y, self.relative_position.y + 1))


class Node:
    def __init__(self, x, y, z, neighbors, distances, idx):
        self.x = x
        self.y = y
        self.z = z
        self.neighbors = neighbors
        self.distances = distances
        self.idx = idx

