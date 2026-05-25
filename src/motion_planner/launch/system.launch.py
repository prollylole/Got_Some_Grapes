#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription

from launch.launch_description_sources import PythonLaunchDescriptionSource

from launch_ros.actions import Node


def generate_launch_description():

    # ================= WORLD LAUNCH =================
    world_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('turtlebot3_sim'),
                'launch',
                'turtlebot3_world.launch.py'
            )
        )
    )

    # ================= NAV2 LAUNCH =================
    nav2_launch_file_dir = os.path.join(get_package_share_directory('nav2_bringup'), 'launch')
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_launch_file_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map': os.path.expanduser('~/coloured_map.yaml'),
            'use_sim_time': 'true'
        }.items()
    )

    # ================= CONTROLLER NODE =================
    controller_node = Node(
        package='motion_planner',
        executable='controller',
        output='screen'
    )

    # ================= PERCEPTION NODE =================
    perception_node = Node(
        package='perception',
        executable='colour_service_node',
        output='screen'
    )

    # ================= CUSTOMER GUI =================
    customer_gui = Node(
        package='ui',
        executable='gui_node',
        output='screen'
    )

    # ================= STAFF GUI =================
    staff_gui = Node(
        package='ui',
        executable='staff_gui',
        output='screen'
    )

    return LaunchDescription([
        world_launch,
        # nav2_launch,
        controller_node,
        perception_node,
        customer_gui,
        staff_gui
    ])