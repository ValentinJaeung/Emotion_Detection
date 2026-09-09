import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'usb_cam_cv'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='val',
    maintainer_email='tlswodnd123456@gmail.com',
    description='OpenCV-based V4L2 MJPEG camera driver for ROS 2',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'camera_node = usb_cam_cv.camera_node:main',
        ],
    },
)
