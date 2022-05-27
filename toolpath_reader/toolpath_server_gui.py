import os
import subprocess
from ament_index_python.packages import get_package_share_directory
import rclpy
from rclpy.node import Node
import yaml
import threading
from toolpath_reader.dxf_reader import create_toolpath_from_dxf
from visualization_msgs.msg import Marker
from geometry_msgs.msg import Pose, Vector3, Point, Polygon, Point32
from ram_interfaces.srv import GetToolpath
from ram_interfaces.msg import Toolpath
from qt_gui.plugin import Plugin
from python_qt_binding import loadUi
from python_qt_binding.QtCore import QAbstractListModel, QFile, QIODevice, Qt, Signal
from python_qt_binding.QtGui import QIcon, QImage, QPainter
from python_qt_binding.QtWidgets import QCompleter, QFileDialog, QGraphicsScene, QWidget, QLabel


def make_point(x, y=None, z=None, msg_type=Point):
    point = msg_type()

    if isinstance(x, list) and y is None and z is None:
        point.x = float(x[0])
        point.y = float(x[1])
        point.z = float(x[2])

    else:
        point.x = float(x)
        point.y = float(y)
        point.z = float(z)
    return point


class ToolpathServer(Plugin):
    def __init__(self, context):
        super(ToolpathServer, self).__init__(context)
        self._widget = QWidget()
        self._node = context.node

        ui_file = os.path.join(get_package_share_directory('toolpath_reader'), 'resource', 'toolpath_server.ui')
        loadUi(ui_file, self._widget)
        self._widget.setObjectName('Toolpath Interface')
        self.setObjectName('Toolpath Interface')
        self._widget.setWindowTitle('Toolpath Interface')
        if context.serial_number() > 1:
            self._widget.setWindowTitle(self._widget.windowTitle() + ('(%d)' % context.serial_number()))
            # Add widget to the user interface
        context.add_widget(self._widget)

        self._widget.button_refresh_list.clicked.connect(self.cb_refresh_list)
        self._widget.button_set_directory.clicked.connect(self.cb_set_directory)
        self._widget.button_load.clicked.connect(self.cb_load_toolpath)

        self.pub_marker = self._node.create_publisher(Marker, "/toolpath_server/marker_toolpath".format(self._node.get_name()), 10)
        self.timer_rviz_display = self._node.create_timer(0.2, self.callback_timer_marker_publish)
        self.timer_rviz_display.cancel()

        self.server_get_toolpath = self._node.create_service(GetToolpath, "/toolpath_server/get_toolpath".format(self._node.get_name()),
                                                             self.cb_get_toolpath)

        self._node.declare_parameter("toolpath_frame", "implant")

        self.files = []
        self.loaded_toolpath = None
        self.toolpath_directory = None

    def set_status(self, message):
        self._widget.label_status.setText(message)
        self._node.get_logger().info(message)

    def cb_refresh_list(self):
        # get param for source directory
        # get a list of each yaml file in there
        # add as option in the list combobox
        self.set_status("Refreshing list of toolpaths")
        if self.toolpath_directory is not None:
            self.files = [toolpath for toolpath in os.listdir(self.toolpath_directory) if
                          'dxf' in toolpath or 'toolpath' in toolpath]
            self._widget.list_toolpaths.clear()
            self._widget.list_toolpaths.addItems(self.files)
        else:
            self.set_status("Select a directory first")

    def cb_set_directory(self):
        # Open popup directory to select the folder
        self.toolpath_directory = QFileDialog.getExistingDirectory(self._widget, "Open Toolpath Directory",
                                                                   "/home/george/dev_ws/src",
                                                                   # TODO start in package directory?
                                                                   QFileDialog.ShowDirsOnly
                                                                   | QFileDialog.DontResolveSymlinks)
        self.set_status("Refreshing list of toolpaths")
        if self.toolpath_directory is not None:
            self.files = [toolpath for toolpath in os.listdir(self.toolpath_directory) if
                          'dxf' in toolpath or 'toolpath' in toolpath]
            self._widget.list_toolpaths.clear()
            self._widget.list_toolpaths.addItems(self.files)

    def cb_load_toolpath(self):
        # get path to selected toolpath
        # set the param for the toolpath handler
        # trigger load to the toolpath handler
        selected_toolpath = self.files[self._widget.list_toolpaths.currentRow()]
        self.set_status("Loading tool path from {}".format(selected_toolpath))
        path = self.toolpath_directory + '/' + selected_toolpath

        if 'yaml' in path:
            with open(path) as file:
                toolpath_config = yaml.load(file, Loader=yaml.FullLoader)
                self.loaded_toolpath = self.create_toolpath_message(toolpath_config)

        elif 'dxf' in path:
            self.loaded_toolpath = Toolpath()
            self.loaded_toolpath.path = create_toolpath_from_dxf(path)
            self.loaded_toolpath.header.frame_id = self._node.get_parameter("toolpath_frame").get_parameter_value().string_value
            self.loaded_toolpath.header.stamp = self._node.get_clock().now().to_msg()

        self.set_status("Loaded toolpath from {}, containing {} points".format(path,
                                                                               len(self.loaded_toolpath.path.points)))

        self.send_marker_delete_msg()
        if self.timer_rviz_display.is_canceled():  # Make sure it is already stopped
            self.timer_rviz_display.reset()

    def cb_get_toolpath(self, request: GetToolpath.Request, response: GetToolpath.Response):
        if self.loaded_toolpath is not None:
            response.toolpath = self.loaded_toolpath
            response.success = True
        else:
            response.success = False
            response.message = "No toolpath has been loaded"
        return response

    def callback_timer_marker_publish(self):
        self._node.get_logger().debug("subcriber_count: {}".format(self.pub_marker.get_subscription_count()))
        msg = self.create_rviz_marker()
        self.pub_marker.publish(msg)

    def create_rviz_marker(self):
        msg = Marker()
        msg.header.frame_id = self._node.get_parameter("toolpath_frame").get_parameter_value().string_value
        msg.header.stamp = self._node.get_clock().now().to_msg()

        msg.id = 0

        msg.type = Marker.LINE_STRIP
        msg.action = Marker.ADD
        msg.pose.orientation.w = 1.0

        # TODO: make these params
        msg.scale.x = 0.003

        msg.color.a = 1.0
        msg.color.r = 1.0

        # msg.lifetime.sec = 0
        # msg.frame_locked = True

        if self.loaded_toolpath is not None:  # if initialised, there's a better way to check
            for path_point in self.loaded_toolpath.path.points:
                point = Point()
                point.x = path_point.x
                point.y = path_point.y
                point.z = path_point.z
                msg.points.append(point)
        return msg

    def send_marker_delete_msg(self):
        msg = Marker()
        msg.header.frame_id = self._node.get_parameter("toolpath_frame").get_parameter_value().string_value
        msg.header.stamp = self._node.get_clock().now().to_msg()
        msg.id = 0
        msg.action = Marker.DELETE
        self.pub_marker.publish(msg)

    def create_toolpath_message(self, toolpath_config):
        msg = Toolpath()
        if toolpath_config is not None:  # if initialised, there's a better way to check
            msg.header.frame_id = self._node.get_parameter("toolpath_frame").get_parameter_value().string_value
            msg.header.stamp = self._node.get_clock().now().to_msg()

            points = toolpath_config["cut"]["points"]
            for path_point in points:
                point = make_point(path_point, msg_type=Point32)
                msg.path.points.append(point)
        else:
            self.set_status("Toolpath has not been loaded. Empty toolpath will be returned")
        return msg

    def __del__(self):
        self._node.get_logger().warn("Destroying toolpath loader plugin")
        self.timer_rviz_display.cancel()
        self.timer_rviz_display.destroy()
        self.server_get_toolpath.destroy()
        self.pub_marker.destroy()
