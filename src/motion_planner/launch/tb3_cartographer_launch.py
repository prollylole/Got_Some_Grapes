import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    # Use the official turtlebot3 cartographer launch file
    cartographer_launch_dir = os.path.join(
        get_package_share_directory('turtlebot3_cartographer'), 'launch'
    )
    
    carto_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(cartographer_launch_dir, 'cartographer.launch.py')
        ),
        launch_arguments={'use_sim_time': 'true'}.items()
    )

    return LaunchDescription([
        carto_launch
    ])
