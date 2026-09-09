from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('video_device', default_value='/dev/usb_cam'),
        DeclareLaunchArgument('image_width', default_value='1920'),
        DeclareLaunchArgument('image_height', default_value='1080'),
        DeclareLaunchArgument('framerate', default_value='30.0'),
        DeclareLaunchArgument('frame_id', default_value='camera'),

        Node(
            package='usb_cam_cv',
            executable='camera_node',
            name='camera_node',
            output='screen',
            parameters=[{
                'video_device': LaunchConfiguration('video_device'),
                'image_width': LaunchConfiguration('image_width'),
                'image_height': LaunchConfiguration('image_height'),
                'framerate': LaunchConfiguration('framerate'),
                'frame_id': LaunchConfiguration('frame_id'),
            }],
        ),
    ])
