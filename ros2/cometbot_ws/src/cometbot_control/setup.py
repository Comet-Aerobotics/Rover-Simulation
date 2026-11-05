from setuptools import find_packages, setup
package_name = "cometbot_control"
setup(name=package_name, version="0.1.0", packages=find_packages(exclude=["test"]),
      data_files=[
          ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
          ("share/" + package_name, ["package.xml"]),
          ("share/" + package_name + "/launch", ["launch/teleop.launch.py"]),
      ], install_requires=["setuptools"], zip_safe=True,
      maintainer="AIAA Rover Team", maintainer_email="aiaa@utdallas.edu",
      description="Joystick to Twist control for the AIAA rover.", license="Apache-2.0",
      tests_require=["pytest"], entry_points={"console_scripts": [
          "teleop_publisher = cometbot_control.teleop_publisher:main"]})
