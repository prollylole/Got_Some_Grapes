import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'motion_planner'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.py')),
        (os.path.join('share', package_name, 'map'),
            glob('map/*.yaml')),
        (os.path.join('share', package_name, 'param', 'humble'),
            glob('param/humble/*.yaml')),
        (os.path.join('share', package_name, 'rviz'),
            glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='claudia',
    maintainer_email='claudiawee08@gmail.com',
    description='TODO: Package description',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'route_optimizer_node = motion_planner.route_optimizer_node:main',
            'basic_test = motion_planner.basic_test:main',
            'controller = motion_planner.controller:main',
        ],
    },
)
