#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2


class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        self.declare_parameter('video_device', '/dev/usb_cam')
        self.declare_parameter('image_width', 1920)
        self.declare_parameter('image_height', 1080)
        self.declare_parameter('framerate', 30.0)
        self.declare_parameter('frame_id', 'camera')

        dev = self.get_parameter('video_device').value
        w = self.get_parameter('image_width').value
        h = self.get_parameter('image_height').value
        fps = self.get_parameter('framerate').value
        self.frame_id = self.get_parameter('frame_id').value

        self.bridge = CvBridge()
        self.pub = self.create_publisher(Image, 'image_raw', 10)

        self.cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self.cap.isOpened():
            self.get_logger().error(f'failed to open {dev}')
            raise RuntimeError('camera open failed')

        aw = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        ah = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.get_logger().info(f'{dev} open at {aw}x{ah} @ {fps} fps')

        self.timer = self.create_timer(1.0 / fps, self.tick)

    def tick(self):
        ok, frame = self.cap.read()
        if not ok:
            self.get_logger().warn('frame read failed')
            return
        msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        self.pub.publish(msg)

    def destroy_node(self):
        if hasattr(self, 'cap'):
            self.cap.release()
        super().destroy_node()


def main():
    rclpy.init()
    node = CameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

