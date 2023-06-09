#!/usr/bin/env python3

import rospy
from sensor_msgs.msg import Image, CameraInfo
from std_msgs.msg import Int32
import cv2
from cv_bridge import CvBridge, CvBridgeError
import numpy as np
import rospkg
import yaml
import message_filters
import struct
from PIL import Image as PILImage
from geometry_msgs.msg import Point

class Camera():

    def __init__(self):
        rospy.init_node('camera_node', anonymous=True)
        rospy.loginfo("Camera...")
        self._check_camera_ready()
        self.rgb_bridge = CvBridge()
        rgb_sub = rospy.Subscriber("/camera/image_raw", Image, self.rgb_callback)
        self.coor_pub = rospy.Publisher('/camera/contour_coodinates', Point, queue_size=10)
        self.camera_info_subscriber = rospy.Subscriber('/camera/camera_info', CameraInfo, self.camera_info_callback)
        self.rgb = None
        self.cX = 0
        self.cY = 0
        self.skip=False
        self.count=0
        model_sub = rospy.Subscriber('/model/count', Int32, self.model_callback)

    def _register_color_threshold(self):
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

    def _check_camera_ready(self):
        camera_msg = None
        rospy.loginfo("Checking Camera...")
        while camera_msg is None and not rospy.is_shutdown():
            try:
                camera_msg = rospy.wait_for_message("/camera/image_raw", Image, timeout=1.0)
                rospy.logdebug("Current /camera/image_raw READY=>" + str(camera_msg))

            except:
                rospy.logdebug("Current /camera/image_raw not ready yet, retrying for getting camera")
        rospy.loginfo("Checking Camera...DONE")
    
    def rgb_callback(self, image_rgb):
        try:
            rgb = self.rgb_bridge.imgmsg_to_cv2(image_rgb, "bgr8")
        except CvBridgeError as e:
            rospy.logerr(e)
            return
        self.rgb = rgb

    def model_callback(self, msg):
        self.count=msg.data
        self.skip=False

    def nothing(self,x):
        pass

    def camera_info_callback(self,camera_info):
        width = camera_info.width #640
        height = camera_info.height #480
        # Intrinsic camera matrix for the raw (distorted) images.
        #     [fx  0 cx]
        # K = [ 0 fy cy]
        #     [ 0  0  1]
        # Projects 3D points in the camera coordinate frame to 2D pixel
        # coordinates using the focal lengths (fx, fy) and principal point
        # (cx, cy).
        ppx = camera_info.K[2] #cx 320.5
        ppy = camera_info.K[5] #cy 240.5
        fx = camera_info.K[0] #149.2239
        fy = camera_info.K[4] #149.2239
        self.camera_info_subscriber.unregister()

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
    
    def run(self):
        # cv2.namedWindow('Edge', cv2.WINDOW_FREERATIO)
        cv2.namedWindow("Edge", cv2.WINDOW_NORMAL)

        # Resize the window to the desired size
        cv2.resizeWindow("Edge", 800, 600)
        cv2.createTrackbar('Threshold1', 'Edge' , 0, 255, self.nothing)
        while not rospy.is_shutdown():
            im = self.rgb
            threshold_value = cv2.getTrackbarPos('Threshold1', 'Edge')
            src_gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
            img_blur = cv2.GaussianBlur(src_gray,(5,5),0)
            edges = cv2.Canny(img_blur, 135, 135*3)
            contours, hierarchy = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) #cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE
            cv2.drawContours(im, contours, -1, (0, 0, 0), 1)
            if len(contours)>0 and self.skip ==False and self.count>0:
                rospy.loginfo(f'Length of contours: {len(contours)}')
                M0 = cv2.moments(contours[0])
                if M0["m00"] != 0 and M0["m10"] !=0 and M0["m01"] !=0:
                    self.cX = int(M0["m10"] / M0["m00"])
                    self.cY = int(M0["m01"] / M0["m00"])
                    point = Point()
                    point.x = self.cX
                    point.y = self.cY
                    self.coor_pub.publish(point)
                    self.skip=True
                    rospy.loginfo(f'self.cX: {self.cX}, self.cY: {self.cY}')
            im = cv2.circle(im, (self.cX, self.cY), 2, (255, 0, 0), 1)
            cv2.imshow('Edge', im)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                break
        rospy.signal_shutdown('Quit')

if __name__ == '__main__':
    camera = Camera()
    try:
        camera.run()
    except rospy.ROSInterruptException:
        pass