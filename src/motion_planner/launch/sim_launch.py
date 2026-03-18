import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    # Get the directory of the turtlebot3_gazebo package
    turtlebot3_gazebo_dir = get_package_share_directory('turtlebot3_gazebo')

    # Path to the empty_world.launch.py file
    empty_world_launch_file = os.path.join(
        turtlebot3_gazebo_dir,
        'launch',
        'empty_world.launch.py'
    )

    # Include the Gazebo launch file
    gazebo_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(empty_world_launch_file)
    )

    # Create the RViz2 node
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        # Optional: You can add an 'arguments' list here to pass a specific .rviz config file
        # arguments=['-d', os.path.join(get_package_share_directory('motion_planner'), 'rviz', 'default.rviz')]
    )

    # Return the LaunchDescription
    return LaunchDescription([
        gazebo_cmd,
        rviz_node
    ])
