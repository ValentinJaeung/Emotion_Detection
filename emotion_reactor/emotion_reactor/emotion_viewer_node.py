#!/usr/bin/env python3
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from hri import HRIListener

BOX_COLOR = (0, 220, 0)
TEXT_COLOR = (0, 220, 0)


class EmotionViewerNode(Node):
    """Shows the full camera feed with each tracked face's bounding box and
    its current expression + confidence drawn above it. Purely a visual
    sanity check for the detection pipeline — no reaction logic.
    """

    def __init__(self):
        super().__init__('emotion_viewer_node')

        self.declare_parameter('image_topic', 'image')
        image_topic = self.get_parameter('image_topic').value

        self.bridge = CvBridge()
        self.hri_listener = HRIListener('emotion_viewer_hri_listener')

        self.sub = self.create_subscription(
            Image, image_topic, self._on_image, 10)

        self.get_logger().info(
            f'emotion_viewer_node ready, showing "{image_topic}" '
            f'(press q or Ctrl+C to quit)')

    def _on_image(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h, w = frame.shape[:2]

        for face_id, face in self.hri_listener.faces.items():
            roi = face.roi
            if roi is None:
                continue
            x, y, rw, rh = roi
            x1, y1 = int(x * w), int(y * h)
            x2, y2 = int((x + rw) * w), int((y + rh) * h)
            cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR, 2)

            if face.expression is not None and face.expression_confidence is not None:
                label = (f'{face.expression.name} '
                         f'{face.expression_confidence * 100:.0f}%')
                text_y = y1 - 10 if y1 - 10 > 10 else y1 + 20
                cv2.putText(frame, label, (x1, text_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, TEXT_COLOR, 2)

        cv2.imshow('emotion_viewer', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            self.get_logger().info('quit requested, shutting down')
            rclpy.shutdown()

    def destroy_node(self):
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = EmotionViewerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    try:
        node.destroy_node()
    except Exception:
        pass


if __name__ == '__main__':
    main()
