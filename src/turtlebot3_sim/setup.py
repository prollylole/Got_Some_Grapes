from setuptools import find_packages, setup

package_name = 'turtlebot3_sim'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
    ('share/ament_index/resource_index/packages', ['resource/turtlebot3_sim']),
    ('share/turtlebot3_sim', ['package.xml']),
    ('share/turtlebot3_sim/launch', ['launch/turtlebot3_world.launch.py']),
    ('share/turtlebot3_sim/worlds', ['worlds/supermarket_sim.world']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='harrshawarthan',
    maintainer_email='harrshawarthan@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
        ],
    },
)
