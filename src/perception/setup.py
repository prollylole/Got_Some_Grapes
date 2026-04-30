from setuptools import find_packages, setup

package_name = 'perception'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name]
        ),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='claudia',
    maintainer_email='claudiawee08@gmail.com',
    description='Perception nodes for vision and colour detection',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'aruco_node = perception.aruco_node:main',
            'ai_vision_node = perception.ai_vision_node:main',
            'ColourBatch = perception.ColourBatch:main',
            'colour_service_node = perception.colour_service_node:main',
        ],
    }
)