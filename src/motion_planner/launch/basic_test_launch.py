from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='motion_planner',
            executable='basic_test',
            name='obstacle_stop',
            output='screen',
        ),
    ])
