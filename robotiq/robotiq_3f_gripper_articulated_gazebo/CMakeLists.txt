cmake_minimum_required(VERSION 3.0.2)
project(robotiq_3f_gripper_articulated_gazebo)

find_package(catkin REQUIRED)

catkin_package(
)

install(DIRECTORY launch DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})
