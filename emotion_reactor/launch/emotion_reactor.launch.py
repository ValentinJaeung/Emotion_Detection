from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('confidence_threshold', default_value='0.5'),
        DeclareLaunchArgument('smoothing_window', default_value='5'),
        DeclareLaunchArgument('poll_period', default_value='0.2'),

        Node(
            package='emotion_reactor',
            executable='emotion_reactor_node',
            name='emotion_reactor_node',
            output='screen',
            parameters=[{
                'confidence_threshold': LaunchConfiguration('confidence_threshold'),
                'smoothing_window': LaunchConfiguration('smoothing_window'),
                'poll_period': LaunchConfiguration('poll_period'),
            }],
        ),
    ])
