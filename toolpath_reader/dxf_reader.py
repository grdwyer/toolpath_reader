from typing import Iterable
import ezdxf
import ezdxf.entities
from ezdxf import units
from geometry_msgs.msg import Polygon, Point32
import math


def create_points_from_line(line: ezdxf.entities.Line):
    start = Point32()
    start.x = line.dxf.start[0]
    start.y = line.dxf.start[1]
    start.z = line.dxf.start[2]
    end = Point32()
    end.x = line.dxf.end[0]
    end.y = line.dxf.end[1]
    end.z = line.dxf.end[2]
    return [start, end]


def approx_equal(a: Point32, b: Point32, tol=0.00001):
    dist = math.sqrt(math.pow(a.x-b.x, 2) + math.pow(a.y-b.y, 2) + math.pow(a.z-b.z, 2))
    return dist < tol


def print_entity(e):
    print("start point: %s" % e.dxf.start)
    print("end point: %s\n" % e.dxf.end)


def create_polygon(lines: Iterable[ezdxf.entities.Line]):
    # Is the first point in the list the first of the path?
    poly = Polygon()
    points = []
    for line in lines:
        points.append(create_points_from_line(line))

    ordered_points = [points[0]]

    while len(ordered_points) < len(points):
        for comp in points:
            if approx_equal(ordered_points[-1][1], comp[0]):
                ordered_points.append(comp)

    poly.points.append(ordered_points[0][0])
    for point in ordered_points:
        poly.points.append(point[1])

    return poly


def get_start(entity):
    if entity.dxftype() == "LINE":
        return entity.dxf.start
    elif entity.dxftype() == "LWPOLYLINE":
        return entity.vertices_in_wcs()[0]
    elif entity.dxftype() == "SPLINE":
        return entity.control_points[0]


def get_end(entity):
    if entity.dxftype() == "LINE":
        return entity.dxf.end
    elif entity.dxftype() == "LWPOLYLINE":
        return entity.vertices_in_wcs()[-1]
    elif entity.dxftype() == "SPLINE":
        return entity.control_points[-1]


def order_entities(modelspace: ezdxf.layouts.Modelspace):
    for entity in modelspace:
        print('Type: {}, start: {}, end: {}'.format(type(entity), get_start(entity), get_end(entity)))


if __name__ == '__main__':
    # doc = ezdxf.readfile("/home/george/dev_ws/src/toolpath_reader/test/polyline.dxf")
    doc = ezdxf.readfile("/home/george/dev_ws/src/toolpath_reader/test/spline_poly.dxf")
    # doc = ezdxf.readfile("/home/george/dev_ws/src/toolpath_reader/test/spline.dxf")
    print(doc.units)
    msp = doc.modelspace()

    order_entities(msp)

    # lines = []
    # for e in msp:
    #     # print(type(e))
    #     # print(e.dxftype())
    #     if e.dxftype() == "LINE":
    #         print(type(get_start(e)))
    #         # print_entity(e)
    #         # print(e.dxf.start[0])
    #         lines.append(e)
    #
    # polygon = create_polygon(lines)
    # print(polygon)

