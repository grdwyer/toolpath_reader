from typing import Iterable
import ezdxf
import ezdxf.entities
import ezdxf.math
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


def create_points_from_vec(vec: ezdxf.math.Vec3, scale=1.0):
    point = Point32()
    point.x = vec.x * scale
    point.y = vec.y * scale
    point.z = vec.z * scale
    return point


def approx_equal(a: Point32, b: Point32, tol=0.00001):
    dist = math.sqrt(math.pow(a.x-b.x, 2) + math.pow(a.y-b.y, 2) + math.pow(a.z-b.z, 2))
    return dist < tol


def print_entity(e):
    print("start point: %s" % e.dxf.start)
    print("end point: %s\n" % e.dxf.end)


def create_polygon(entities: Iterable[ezdxf.entities.DXFGraphic], scale: float = 1.0):
    # Is the first point in the list the first of the path?
    poly = Polygon()

    for entity in entities:
        # generate points from entity
        if entity.dxftype() == "LINE":
            if len(poly.points) == 0 or not approx_equal(poly.points[-1], create_points_from_vec(get_start(entity),
                                                                                                 scale)):
                poly.points.append(create_points_from_vec(get_start(entity), scale))
            poly.points.append(create_points_from_vec(get_end(entity), scale))

        elif entity.dxftype() == "LWPOLYLINE":
            start_point = entity.ocs().to_wcs(ezdxf.math.Vec3(entity.get_points('x')[0][0],
                                                              entity.get_points('y')[0][0],
                                                              entity.dxf.elevation))
            if len(poly.points) == 0 or not approx_equal(poly.points[-1], create_points_from_vec(start_point, scale)):
                poly.points.append(create_points_from_vec(start_point, scale))

            for point in entity[1:]:
                poly.points.append(create_points_from_vec(entity.ocs().to_wcs(ezdxf.math.Vec3(point[0],
                                                                                              point[1],
                                                                                              entity.dxf.elevation)),
                                                          scale))

        # elif entity.dxftype() == "SPLINE":

    return poly


def get_start(entity):
    if entity.dxftype() == "LINE":
        return entity.dxf.start
    elif entity.dxftype() == "LWPOLYLINE":
        ocs_point = ezdxf.math.Vec3(entity.get_points('x')[0][0], entity.get_points('y')[0][0], entity.dxf.elevation)
        return entity.ocs().to_wcs(ocs_point)
    elif entity.dxftype() == "SPLINE":
        return entity.control_points[0]


def get_end(entity):
    if entity.dxftype() == "LINE":
        return entity.dxf.end
    elif entity.dxftype() == "LWPOLYLINE":
        ocs_point = ezdxf.math.Vec3(entity.get_points('x')[-1][0], entity.get_points('y')[-1][0], entity.dxf.elevation)
        return entity.ocs().to_wcs(ocs_point)
    elif entity.dxftype() == "SPLINE":
        return entity.control_points[-1]


def order_entities(modelspace: ezdxf.layouts.Modelspace):
    # for entity in modelspace:
    #     print('Type: {}, start: {}, end: {}'.format(type(entity), get_start(entity), get_end(entity)))

    ordered_entities = [modelspace[0]]  # TODO: check the first element is first entity along the path

    while len(ordered_entities) < len(modelspace):  # TODO: this will loop forever if it can't match an entity
        for comp in modelspace:
            if get_end(ordered_entities[-1]).isclose(get_start(comp)):
                ordered_entities.append(comp)
                break

    # for entity in ordered_entities:
    #     print('Type: {}, start: {}, end: {}'.format(type(entity), get_start(entity), get_end(entity)))
    return ordered_entities


def create_toolpath_from_dxf(path: str):
    doc = ezdxf.readfile(path)
    if doc.units == 0:
        # unitless assume mm
        scale = 0.001
    elif doc.units == units.MM:
        # unitless assume mm
        scale = 0.001
    elif doc.units == units.M:
        scale = 1.0
    else:
        scale = 1.0
    msp = doc.modelspace()
    ordered = order_entities(msp)
    polygon = create_polygon(ordered, scale)
    return polygon


if __name__ == '__main__':
    # doc = ezdxf.readfile("/home/george/dev_ws/src/toolpath_reader/test/polyline.dxf")
    # doc = ezdxf.readfile("/home/george/dev_ws/src/toolpath_reader/test/spline_poly.dxf")
    doc = ezdxf.readfile("/home/george/dev_ws/src/toolpath_reader/test/spline.dxf")
    print(doc.units)
    msp = doc.modelspace()

    ordered = order_entities(msp)
    polygon = create_polygon(ordered)
    print(polygon)

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


