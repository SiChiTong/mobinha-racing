import os
import tf
import math

import rospy
from geometry_msgs.msg import Point
from visualization_msgs.msg import Marker, MarkerArray

dir_path = os.path.dirname(os.path.realpath(__file__))

def LocalPathViz(waypoints):
    color =  [241, 76, 152, 1]
    return Path(waypoints, 999, 0.2, 1.5, (color[0]/255,color[1]/255, color[2]/255, 0.75))

def KappaPathViz(waypoints):
    return Path(waypoints, 999, 0.2, 1.5, (150/255,59/255, 255/255, 0.5))

def Path(waypoints, id_, z, scale, color):
    marker = Line('path', int(id_), scale, color, len(waypoints))
    for pt in waypoints:
        marker.points.append(Point(x=pt[0], y=pt[1], z=z))
    return marker
    
def path_viz(paths):
    if paths == None:
        return
    return LocalPathViz(paths)

def kappa_viz(kappas):
    kappa_viz = KappaPathViz(kappas)
    return kappa_viz
    
def Line(ns, id_, scale, color, len):
    marker = Marker()
    marker.type = Marker.SPHERE_LIST
    marker.action = Marker.ADD
    marker.header.frame_id = 'world'
    marker.ns = ns
    marker.id = id_
    marker.lifetime = rospy.Duration(0)
    marker.scale.x = scale
    marker.scale.y = scale
    marker.scale.z = scale
    marker.color.r = color[0]
    marker.color.g = color[1]
    marker.color.b = color[2]
    marker.color.a = color[3]
    marker.pose.orientation.x = 0.0
    marker.pose.orientation.y = 0.0
    marker.pose.orientation.z = 0.0
    marker.pose.orientation.w = 1.0
    return marker

def LaneletMapViz(lanelet, for_viz):
    array = MarkerArray()
    for id_, data in lanelet.items():
        for n, (leftBound, leftType) in enumerate(zip(data['leftBound'], data['leftType'])):
            marker = Bound('leftBound', id_, n, leftBound,
                           leftType, (1.0, 1.0, 1.0, 1.0))
            array.markers.append(marker)

        for n, (rightBound, rightType) in enumerate(zip(data['rightBound'], data['rightType'])):
            marker = Bound('rightBound', id_, n, rightBound,
                           rightType, (1.0, 1.0, 1.0, 1.0))
            array.markers.append(marker)

    for n, (points, type_) in enumerate(for_viz):
        if type_ == 'stop_line':
            marker = Bound('for_viz', n, n, points,
                           'solid', (1.0, 1.0, 1.0, 1.0))
            array.markers.append(marker)
        else:
            marker = Bound('for_viz', n, n, points,
                           type_, (1.0, 1.0, 1.0, 1.0))
            array.markers.append(marker)

    return array

def Bound(ns, id_, n, points, type_, color):
    if type_ == 'solid':
        marker = Line('%s_%s' % (ns, id_), n, 0.15, color, 0)
        for pt in points:
            marker.points.append(Point(x=pt[0], y=pt[1], z=0.0))

    elif type_ == 'dotted':
        marker = Points('%s_%s' % (ns, id_), n, 0.15, color)
        for pt in points:
            marker.points.append(Point(x=pt[0], y=pt[1], z=0.0))

    return marker

def Points(ns, id_, scale, color):
    marker = Marker()
    marker.type = Marker.POINTS
    marker.action = Marker.ADD
    marker.header.frame_id = 'world'
    marker.ns = ns
    marker.id = id_
    marker.lifetime = rospy.Duration(0)
    marker.scale.x = scale
    marker.scale.y = scale
    marker.color.r = color[0]
    marker.color.g = color[1]
    marker.color.b = color[2]
    marker.color.a = color[3]
    return marker

def CarInfoViz(frame_id, name_space, info, position):
    marker = Marker()
    marker.header.frame_id = frame_id
    marker.ns = name_space
    marker.type = Marker.TEXT_VIEW_FACING
    marker.lifetime = rospy.Duration(0.1)
    marker.scale.z = 2.0
    marker.color.r = 1
    marker.color.g = 1
    marker.color.b = 1
    marker.color.a = 1.0
    marker.pose.position.x = position[0]
    marker.pose.position.y = position[1]
    marker.pose.position.z = position[2]
    marker.text = info
    return marker


def CarViz(frame_id, name_space, position, color):
    marker = Marker()
    marker.header.frame_id = frame_id
    marker.ns = name_space
    marker.id = 0
    marker.type = Marker.MESH_RESOURCE
    marker.mesh_resource = 'file://{}/car.dae'.format(dir_path)
    marker.action = Marker.ADD
    marker.lifetime = rospy.Duration(0.1)
    marker.scale.x = 2.0
    marker.scale.y = 2.0
    marker.scale.z = 2.0
    marker.color.r = color[0]/255
    marker.color.g = color[1]/255
    marker.color.b = color[2]/255
    marker.color.a = color[3]
    marker.pose.position.x = position[0]
    marker.pose.position.y = position[1]
    marker.pose.position.z = position[2]
    quaternion = tf.transformations.quaternion_from_euler(0, 0, math.radians(90))
    marker.pose.orientation.x = quaternion[0]
    marker.pose.orientation.y = quaternion[1]
    marker.pose.orientation.z = quaternion[2]
    marker.pose.orientation.w = quaternion[3]
    return marker

def ObjectsViz(objects):
    marker_array = MarkerArray()
    marker = Marker()
    color1 = [48,255,255,1] #cyan: simulator
    color2 = [69,255,48,1] #green: matched
    color3 = [255, 114, 48, 1] #orage: non-matched
    colors = [color1, color2, color3]
    for n, obj in enumerate(objects):
        color = colors[obj[0]]
        marker = ObjectViz(n, (round(obj[1],1), round(obj[2],1)), obj[3], color)
        marker_array.markers.append(marker)
        dist = f"{round(obj[5])}m, {round(obj[4]*3.6)}km/h"
        marker = CarInfoViz('world',str(n+1), dist,(round(obj[1],1), round(obj[2],1), 3.0) )
        marker_array.markers.append(marker)
    return marker_array


def TargetObjectsViz(objects):
    marker_array = MarkerArray()
    marker = Marker()
    color = [252, 227, 3, 1] #yellow: using at planning
    for n, obj in enumerate(objects):
        marker = ObjectViz(n, (round(obj[0],1), round(obj[1],1)), obj[2], color)
        marker_array.markers.append(marker)
        dist = f"s: {round(obj[3])}, d: {round(obj[4])}"
        marker = CarInfoViz('world',str(n+1), dist,(round(obj[0],1), round(obj[1],1), 4.5) )
        marker_array.markers.append(marker)
    return marker_array

def ObjectViz(_id, position, heading, color):
    marker = Marker()
    marker.header.frame_id = 'world'
    marker.ns = 'object'
    marker.id = _id
    marker.type = Marker.CUBE
    #marker.mesh_resource = 'file://{}/car.dae'.format(dir_path)
    marker.action = Marker.ADD
    marker.lifetime = rospy.Duration(0.1)
    marker.scale.x = 3
    marker.scale.y = 1.2
    marker.scale.z = 1.2
    marker.color.r = color[0]/255
    marker.color.g = color[1]/255
    marker.color.b = color[2]/255
    marker.color.a = color[3]
    marker.pose.position.x = position[0]
    marker.pose.position.y = position[1]
    marker.pose.position.z = 0.5
    quaternion = tf.transformations.quaternion_from_euler(0, 0, math.radians(heading))
    marker.pose.orientation.x = quaternion[0]
    marker.pose.orientation.y = quaternion[1]
    marker.pose.orientation.z = quaternion[2]
    marker.pose.orientation.w = quaternion[3]
    return marker