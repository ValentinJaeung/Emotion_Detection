#!/usr/bin/env python3
from collections import Counter, deque

import rclpy
from rclpy.node import Node
from hri import HRIListener


class EmotionReactorNode(Node):
    """Consumes /humans/faces/<id>/expression (via HRIListener) and reacts to
    stable, confident emotions. Face IDs are ephemeral (a face can be lost and
    a new one tracked with a different id at any time), so all state is keyed
    by id and cleaned up on HRIListener's on_face_lost callback.
    """

    def __init__(self):
        super().__init__('emotion_reactor_node')

        self.declare_parameter('confidence_threshold', 0.5)
        self.declare_parameter('smoothing_window', 5)
        self.declare_parameter('poll_period', 0.2)

        self.confidence_threshold = self.get_parameter(
            'confidence_threshold').value
        self.smoothing_window = self.get_parameter('smoothing_window').value
        poll_period = self.get_parameter('poll_period').value

        # face_id -> deque of recent expressions that passed the confidence
        # threshold, most recent last.
        self._recent_expressions = {}
        # face_id -> last expression actually reacted to (debounces repeats).
        self._last_reacted = {}

        self.hri_listener = HRIListener('emotion_reactor_hri_listener')
        self.hri_listener.on_face_lost(self._on_face_lost)

        self.timer = self.create_timer(poll_period, self._tick)

        self.get_logger().info(
            f'emotion_reactor_node ready (confidence_threshold='
            f'{self.confidence_threshold}, smoothing_window='
            f'{self.smoothing_window})')

    def _on_face_lost(self, face_id):
        self._recent_expressions.pop(face_id, None)
        self._last_reacted.pop(face_id, None)

    def _tick(self):
        for face_id, face in self.hri_listener.faces.items():
            expression = face.expression
            confidence = face.expression_confidence

            if expression is None or confidence is None:
                continue
            if confidence < self.confidence_threshold:
                continue

            window = self._recent_expressions.setdefault(
                face_id, deque(maxlen=self.smoothing_window))
            window.append(expression)

            if len(window) < self.smoothing_window:
                continue

            smoothed, _ = Counter(window).most_common(1)[0]
            if self._last_reacted.get(face_id) == smoothed:
                continue

            self._last_reacted[face_id] = smoothed
            self.react(face_id, smoothed, confidence)

    def react(self, face_id, expression, confidence):
        """Extension point: map a stable, confident expression to robot
        behaviour. Placeholder logs the transition until that mapping is
        decided.
        """
        self.get_logger().info(
            f'face {face_id}: stable expression -> '
            f'{expression.name} (confidence={confidence:.3f})')


def main(args=None):
    rclpy.init(args=args)
    node = EmotionReactorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
