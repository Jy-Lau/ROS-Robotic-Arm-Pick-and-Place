cmake_minimum_required(VERSION 3.0.2)
project(robotiq_3f_gripper_articulated_msgs)

find_package(catkin REQUIRED COMPONENTS std_msgs message_generation )

add_message_files(
    FILES
    Robotiq3FGripperRobotInput.msg
    Robotiq3FGripperRobotOutput.msg
)

generate_messages(
    DEPENDENCIES
    std_msgs
)

catkin_package(
    CATKIN_DEPENDS std_msgs message_runtime
)
