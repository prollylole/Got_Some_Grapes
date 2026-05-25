import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    # 1. Gazebo Simulation World
    turtlebot3_sim_dir = get_package_share_directory('turtlebot3_sim')
    turtlebot3_world_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(turtlebot3_sim_dir, 'launch', 'turtlebot3_world.launch.py')
        ),
        launch_arguments={'use_sim_time': 'true'}.items()
    )

    # 2. Navigation2 Stack
    motion_planner_dir = get_package_share_directory('motion_planner')
    map_yaml_file = os.path.join(motion_planner_dir, 'map', 'map.yaml')
    params_yaml_file = os.path.join(motion_planner_dir, 'param', 'humble', 'waffle.yaml')
    navigation2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(motion_planner_dir, 'launch', 'navigation2.launch.py')
        ),
        launch_arguments={
            'map': map_yaml_file,
            'use_sim_time': 'true',
            'params_file': params_yaml_file
        }.items()
    )

    # 3. Customer GUI Node
    gui_node = Node(
        package='ui',
        executable='gui_node',
        name='gui_node',
        output='screen'
    )

    # 4. Staff GUI Node
    staff_gui_node = Node(
        package='ui',
        executable='staff_gui',
        name='staff_gui',
        output='screen'
    )

    # 5. Grocery Mission Controller
    controller_node = Node(
        package='motion_planner',
        executable='controller',
        name='controller_node',
        output='screen'
    )

    # 6. Perception / Colour Service
    colour_service_node = Node(
        package='perception',
        executable='colour_service_node',
        name='colour_service_node',
        output='screen'
    )

    return LaunchDescription([
        turtlebot3_world_launch,
        navigation2_launch,
        colour_service_node,
        controller_node,
        gui_node,
        staff_gui_node
    ])
