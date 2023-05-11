#!/usr/bin/env python3

import rospy
from sensor_msgs.msg import Image
from std_msgs.msg import String
import cv2
from cv_bridge import CvBridge, CvBridgeError
import numpy as np
import rospkg
import yaml
import message_filters
import time

class Camera():

    def __init__(self):
        rospy.init_node('camera_node', anonymous=True)
        rospy.loginfo("Camera...")
        self._check_camera_ready()
        self.depth_bridge = CvBridge()
        self.rgb_bridge = CvBridge()
        with open(rospkg.RosPack().get_path('robot_pnp') + f"/config/hsv_threshold.yaml", 'r') as f:
            hsv_yaml = yaml.safe_load(f)
        self.hsv_threshold = {}
        self.hsv_threshold['red'] = np.array(hsv_yaml['red'])
        self.hsv_threshold['green'] = np.array(hsv_yaml['green'])
        self.hsv_threshold['blue'] = np.array(hsv_yaml['blue'])
        self.map_color={}
        self.map_color[0] = 'Red'
        self.map_color[1] = 'Green'
        self.map_color[2] = 'Blue'
        rgb = message_filters.Subscriber("/camera/image_raw", Image)
        depth = message_filters.Subscriber("/camera/depth/image_raw", Image)

        #images synchronization
        syncro = message_filters.TimeSynchronizer([rgb, depth], 10, reset=True)
        syncro.registerCallback(self._process_CB)

    def _check_camera_ready(self):
        camera_msg = None
        rospy.loginfo("Checking Laser...")
        while camera_msg is None and not rospy.is_shutdown():
            try:
                camera_msg = rospy.wait_for_message("/camera/depth/image_raw", Image, timeout=1.0)
                rospy.logdebug("Current /camera/image_raw READY=>" + str(camera_msg))

            except:
                rospy.logdebug("Current /camera/depth/image_raw not ready yet, retrying for getting camera")
        rospy.loginfo("Checking Camera...DONE")
    
    def _process_CB(self, image_rgb, image_depth):
        print("hi")
        t_start = time.time()
        #from standard message image to opencv image
        try:
            rgb = self.rgb_bridge.imgmsg_to_cv2(image_rgb, "bgr8")                                              
            depth = self.depth_bridge.imgmsg_to_cv2(image_depth, "32FC1")

            cv2.imshow("Depth Camera Feed", depth)
            cv2.imshow("RGB Camera Feed", rgb)
            cv2.waitKey(0)
        except CvBridgeError as e:
            rospy.logerr(e)
            return
        rospy.loginfo("Time:", time.time() - t_start)
            

    def _find_color(self, img):
        kernel = np.ones((5, 5), np.float32)/25
        blur = cv2.filter2D(img, -1, kernel)
        hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
        
        mask_red = cv2.inRange(hsv, self.hsv_threshold['red'][0], self.hsv_threshold['red'][1])
        mask_green = cv2.inRange(hsv, self.hsv_threshold['green'][0], self.hsv_threshold['green'][1])
        mask_blue = cv2.inRange(hsv, self.hsv_threshold['blue'][0], self.hsv_threshold['blue'][1])
        
        rgb_mask_count = [cv2.countNonZero(mask_red),cv2.countNonZero(mask_green),cv2.countNonZero(mask_blue)]
        index = rgb_mask_count.index(max(rgb_mask_count)) #0 is red, 1 is green, 2 is blue
        return index

if __name__ == '__main__':
    camera = Camera()
    rospy.spin()