from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='motion_planner', # The name of your package
            executable='slam_node',   # The executable defined in setup.py
            name='slam_node',         # The name you want to give the running node
            output='screen',          # Print logs to the terminal
            parameters=[{'use_sim_time': True}] # Enable this if using Gazebo
        ),
    ])
