#!/usr/bin/env python3

import math
import cv2
import rclpy
import threading
import time

from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup

from sensor_msgs.msg import LaserScan, Image
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseArray, PoseStamped, Pose, Twist
from visualization_msgs.msg import MarkerArray, Marker
from std_msgs.msg import Float64
from builtin_interfaces.msg import Duration
from action_msgs.msg import GoalStatus
from std_msgs.msg import Bool, String
from nav2_msgs.action import NavigateToPose, ComputePathToPose
from perception_interfaces.srv import DetectColour
from tf2_ros import Buffer, TransformListener

import cv_bridge

class GoalStats:
    """Helper class to store position and orientation"""
    def __init__(self, position=None, orientation=None):
        self.position = position
        self.orientation = orientation

class Controller(Node):
    def __init__(self):
        super().__init__('turtlebot3_controller_node')

        self.current_goal_idx = 0
        self.total_mission_distance = 0.0
        self.completed_mission_distance = 0.0
        self.goal_set = False
        self.laser_received = False

        self.last_scan = None
        self.current_pose = Pose()
        # Initialise with NaN to mimic uninitialised state 
        self.current_pose.position.x = float('nan')
        self.current_pose.position.y = float('nan')

        self.goals = []
        self.segment_distances = []

        # Parameters
        self.declare_parameter('goal_action_name', 'navigate_to_pose')
        self.goal_action_name = self.get_parameter('goal_action_name').value
        self.declare_parameter('navigate_to_pose_action_name', '/navigate_to_pose')
        self.navigate_to_pose_action_name = self.get_parameter('navigate_to_pose_action_name').value

        # tf2 listener
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # Subcriptions
        self.laser_sub = self.create_subscription(
            LaserScan,
            '/scan',
            self.laser_callback,
            10
        )

        # self.single_goal_sub = self.create_subscription(
        #     PoseStamped,
        #     '/goal_pose',
        #     self.single_goal_pose_callback,
        #     10
        # )

        self.array_goal_sub = self.create_subscription(
            PoseArray,
            '/waypoints',
            self.array_goal_pose_callback,
            10
        )

        self.odom_sub = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10
        )

        self.continue_sub = self.create_subscription(
            Bool, 
            '/continue', 
            self.continue_callback, 
            10)

        self.robot_run_sub = self.create_subscription(
            Bool,
            '/robot_run',
            self.robot_run_callback,
            10)
            
        self.robot_run_pub = self.create_publisher(
            Bool,
            '/robot_run',
            10)
            
        self.selected_objects_sub = self.create_subscription(
            String,
            '/selected_objects',
            self.selected_objects_callback,
            10)

        self.mode_sub = self.create_subscription(
            String,
            '/mode',
            self.mode_callback,
            10)

        self.is_running = False
        self.mode = "normal"
        self.pending_items = []
        self.checking_item = False

        self.object_to_colour = {
            'apple' : 'red',
            'bottle': 'blue',
            'book': 'yellow',
            'cup': 'green',
            'banana': 'red',
            'raspberry': 'yellow'
        }

        def create_pose(x, y, yaw=0.0):
            p = Pose()
            p.position.x = x
            p.position.y = y
            p.position.z = 0.0
            
            cy = math.cos(yaw * 0.5)
            sy = math.sin(yaw * 0.5)
            p.orientation.x = 0.0
            p.orientation.y = 0.0
            p.orientation.z = sy
            p.orientation.w = cy
            return p

        # another_mock_supermarket
        # self.item_waypoints = {
        #     'banana': create_pose(1.38, -11.6, 1.57),
        #     'bottle': create_pose(-1.98, -11.2, 0.0),
        #     'book': create_pose(-4.12, -8.81, -3.14159),
        #     'cup': create_pose(-7.1, -11.3, 0.0),
        #     'apple': create_pose(-9.28, -8.6, -3.14159),
        #     'raspberry': create_pose(-10.7, -10.5, -1.57)
        # }
        # fix 90 degree turns 
        self.item_waypoints = {
            'banana': create_pose(1.38, -11.6, 0.0),
            'bottle': create_pose(-1.98, -11.2, -1.57),
            'book': create_pose(-4.12, -8.81, 1.57),
            'cup': create_pose(-7.1, -11.3, -1.57),
            'apple': create_pose(-9.28, -8.6, 1.57),
            'raspberry': create_pose(-10.7, -10.5, 3.14159)
        }

        # 3rd supermarket
        # self.item_waypoints = {
        #     'banana': create_pose(6.23, -1.17, 1.57),
        #     'bottle': create_pose(4.53, -0.182, 0.0),
        #     'book': create_pose(3.24, 1.18, -3.14159),
        #     'cup': create_pose(1.62, 0.197, 0.0),
        #     'apple': create_pose(0.592, 1.57, -3.14159),
        #     'raspberry': create_pose(-0.428, 0.611, -1.57)
        # }

        self.status_pub = self.create_publisher(
            String, 
            '/robot_status', 
            10)

        self.continue_pub = self.create_publisher(
            Bool, 
            '/continue', 
            10)

        self.active_route_pub = self.create_publisher(
            String,
            '/active_route',
            10
        ) 

        # Publishers
        self.marker_pub = self.create_publisher(MarkerArray, '/visualization_marker', 10)
        self.mission_progress_pub = self.create_publisher(Float64, '/mission_progress', 10)
        self.mission_distance_pub = self.create_publisher(String, '/mission_distance', 10)
        self.status_pub = self.create_publisher(String, 'robot_status', 10)
        self.item_availability_pub = self.create_publisher(Bool, '/item_availability', 10)
        self.out_of_stock_pub = self.create_publisher(String, '/out_of_stock', 10)
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # continue/pause button 
        self.waiting_for_continue = False

        self.action_cb_group = ReentrantCallbackGroup()

        # Action Client for Nav2
        # callback group allows us to have multiple callback functions (timer and action server responses)
        # to be processed at the same time
        self.navigate_to_pose_client = ActionClient(
            self,
            NavigateToPose,
            self.navigate_to_pose_action_name,
            callback_group=self.action_cb_group
        )

        if not self.navigate_to_pose_client.wait_for_server(timeout_sec=3.0):
            self.get_logger().warn(f"NavigateToPose action server '{self.navigate_to_pose_action_name}' not available yet.")
        else:
            self.get_logger().info(f"NavigateToPose action client connected to '{self.navigate_to_pose_action_name}'.")

        # compute path to pose action client works concurrently with navigate to pose
        # computing the path for best item formulation while driving to previous waypoint
        self.compute_path_client = ActionClient(
            self,
            ComputePathToPose,
            '/compute_path_to_pose',
            callback_group=self.action_cb_group
        )

        self.detect_client = self.create_client(
            DetectColour,
            '/detect_colour',
            callback_group=self.action_cb_group
        )
        
        self.is_calculating = False
        
        self.waypoints = []

        self.cv_bridge = cv_bridge.CvBridge()

        # Periodic timer (200ms) for telemetry and markers
        self.timer = self.create_timer(0.2, self.timer_callback)

        self.get_logger().info("Turtlebot3 controller node started")

    def timer_callback(self):
        self.publish_goal_markers()
        self.publish_telemetry()
        self.check_goal_reached_manually()

    def check_goal_reached_manually(self):
        if not self.goal_set or not self.waypoints or self.current_goal_idx >= len(self.waypoints):
            return

        # if stop button is pressed, don't send next waypoint
        if not getattr(self, 'is_running', True):
            return

        # Check distance to current goal
        cur_pos = self.current_pose.position

        # guard against uninitialised odometry
        if math.isnan(cur_pos.x) or math.isnan(cur_pos.y):
            return
            
        goal_pos = self.goals[self.current_goal_idx].position
        dist = self.compute_distance(cur_pos, goal_pos)

        # stuck detection to prevent robot from stalling:
        # if robot moves less than 0.2m in 5s, consider it stalling
        now = self.get_clock().now()
        is_stuck = False

        # if robot is moving and if stuck anchor is zero, always update stuck anchor to current position
        if not self.waiting_for_continue:
            if not hasattr(self, 'stuck_anchor_pos') or self.stuck_anchor_pos is None:
                self.stuck_anchor_pos = Pose().position
                self.stuck_anchor_pos.x = cur_pos.x
                self.stuck_anchor_pos.y = cur_pos.y
                self.stuck_anchor_time = now
            else:
                # calculate the distance between current position and stuck anchor position
                movement = self.compute_distance(cur_pos, self.stuck_anchor_pos)
                # if movement is greater than 0.2m, update stuck anchor position
                if movement > 0.2:
                    self.stuck_anchor_pos.x = cur_pos.x
                    self.stuck_anchor_pos.y = cur_pos.y
                    self.stuck_anchor_time = now

                # if movement is less than 0.2m, check time difference of now and stuck anchor time
                # if time difference is greater than 5s, robot is stuck
                else:
                    dt = (now - self.stuck_anchor_time).nanoseconds / 1e9
                    if dt > 5.0:
                        is_stuck = True
        
        # if within 0.3m or stuck for > 15s 
        if (dist < 0.3 or is_stuck) and not self.waiting_for_continue and not self.checking_item:
            if is_stuck:
                self.get_logger().info(f"Robot stuck near goal for >15s (dist: {dist:.2f}m). Starting automated item check.")
            else:
                self.get_logger().info(f"Waypoint {self.current_goal_idx + 1} reached! Starting automated item check.")

            self.stuck_anchor_pos = None # Reset for the next run
            
            # Cancel the active Nav2 driving goal so the robot actually stops moving!
            if hasattr(self, 'active_goal_handle') and self.active_goal_handle is not None:
                self.active_goal_handle.cancel_goal_async()

            # Formally register this segment's distance as completed
            if self.current_goal_idx < len(self.segment_distances):
                self.completed_mission_distance += self.segment_distances[self.current_goal_idx]
                
            # flag checking item availability
            self.checking_item = True
            item_name = self.pending_items[self.current_goal_idx]['name']

            # start new thread async to call perception service and avoid blocking navigation
            threading.Thread(target=self.check_item_availability_async, args=(item_name,), daemon=True).start()

    def get_yaw(self, orientation):
        siny_cosp = 2 * (orientation.w * orientation.z + orientation.x * orientation.y)
        cosy_cosp = 1 - 2 * (orientation.y * orientation.y + orientation.z * orientation.z)
        return math.atan2(siny_cosp, cosy_cosp)

    def rotate_to_yaw(self, target_yaw):
        self.get_logger().info(f"Rotating to face wall at yaw: {target_yaw:.2f}")
        twist = Twist()
        
        while rclpy.ok() and getattr(self, 'is_running', False):
            if math.isnan(self.current_pose.position.x):
                time.sleep(0.1)
                continue
                
            current_yaw = self.get_yaw(self.current_pose.orientation)
            diff = target_yaw - current_yaw
            diff = (diff + math.pi) % (2 * math.pi) - math.pi
            
            if abs(diff) < 0.1:
                break
                
            angular_speed = 1.0 * diff
            if angular_speed > 0.5:
                angular_speed = 0.5
            elif angular_speed < -0.5:
                angular_speed = -0.5
            elif angular_speed > 0 and angular_speed < 0.1:
                angular_speed = 0.1
            elif angular_speed < 0 and angular_speed > -0.1:
                angular_speed = -0.1
                
            twist.angular.z = angular_speed
            self.cmd_vel_pub.publish(twist)
            time.sleep(0.05)
            
        stop_twist = Twist()
        self.cmd_vel_pub.publish(stop_twist)
        self.get_logger().info("Sent /cmd_vel 0 to stop completely.")
        time.sleep(1.0)

    def check_item_availability_async(self, item_name):
        self.waiting_for_continue = True
        try:
            time.sleep(0.5)
            
            target_yaw = 0.0
            for item in self.pending_items:
                if item['name'] == item_name:
                    target_yaw = self.get_yaw(item['pose'].orientation)
                    break
            
            self.rotate_to_yaw(target_yaw)
            
            self.get_logger().info(f"Scanning for item: {item_name}")

            expected_colour = self.object_to_colour.get(item_name)
            if not expected_colour:
                self.get_logger().warn(f"No colour mapping for '{item_name}'. Marking out of stock.")
                self.publish_item_out_of_stock(item_name)
                return
            
            if not self.detect_client.wait_for_service(timeout_sec=5.0):
                self.get_logger().error("Perception service /detect_colour not available!")
                self.publish_item_out_of_stock(item_name)
                return

            # request perception data from item_name
            req = DetectColour.Request()
            req.expected_colour = expected_colour

            # broadcast service request to colour service node to detect colour 
            # colour_service_node will run openCV processing HSV and send response to res
            future = self.detect_client.call_async(req)

            # start timer after when request is sent
            start_time = time.time()
            # looping until request is done within 15s otherwise send timeout
            while rclpy.ok() and not future.done():
                if time.time() - start_time > 15.0:
                    self.get_logger().error(f"Timeout waiting for /detect_colour for {item_name}")
                    self.publish_item_out_of_stock(item_name)
                    return
                time.sleep(0.1)
            
            # if camera failed or timeout then mark as out of stock
            if not future.done() or future.result() is None:
                self.get_logger().error(f"Failed to get result for {item_name}")
                self.publish_item_out_of_(item_name)
                return
            
            res = future.result()
            item_missing = (not res.success or res.missing_flag or not res.colour_present)

            if item_missing:
                self.get_logger().info(f"{item_name} is OUT OF STOCK.")
                self.publish_item_out_of_stock(item_name)
            else:
                self.get_logger().info(f"{item_name} is AVAILABLE.")
                msg = Bool()
                msg.data = True
                self.item_availability_pub.publish(msg)
            
        finally:
            # reset checking item flag 
            self.checking_item = False
            self.waiting_for_continue = True

            msg = Bool()
            msg.data = False
            self.continue_pub.publish(msg)
            
    def publish_item_out_of_stock(self, item_name):
        msg = Bool()
        msg.data = False
        self.item_availability_pub.publish(msg)

        msg_str = String()
        msg_str.data = item_name
        self.out_of_stock_pub.publish(msg_str)
                
    def laser_callback(self, msg):
        self.last_scan = msg
        self.laser_received = True 

    # reads up transform from odom to map to match the current and ideal pose and orientation
    # try linking the map frame to base_footprint otherwise try base_link frame
    def odom_callback(self, msg):
        try:
            t = self.tf_buffer.lookup_transform('map', 'base_footprint', rclpy.time.Time())
            self.current_pose.position.x = t.transform.translation.x
            self.current_pose.position.y = t.transform.translation.y
            self.current_pose.position.z = t.transform.translation.z
            self.current_pose.orientation = t.transform.rotation
        except Exception:
            try:
                t = self.tf_buffer.lookup_transform('map', 'base_link', rclpy.time.Time())
                self.current_pose.position.x = t.transform.translation.x
                self.current_pose.position.y = t.transform.translation.y
                self.current_pose.position.z = t.transform.translation.z
                self.current_pose.orientation = t.transform.rotation
            except Exception:
                self.current_pose = msg.pose.pose

    def continue_callback(self, msg):
        if msg.data == True and self.waiting_for_continue:
            # The user clicked Continue on the GUI
            self.get_logger().info("Continue button pressed by user! Moving to the next waypoint.")
            self.waiting_for_continue = False

            self.current_goal_idx += 1
            self.send_next_waypoint()

    def robot_run_callback(self, msg):
        run_cmd = msg.data
        if run_cmd == True and not self.is_running:
            self.get_logger().info("UI Start button pressed! Resuming navigation.")
            self.is_running = True

            # if we have goals loaded and we aren't waiting at a shelf, start driving
            if self.goal_set and not getattr(self, 'waiting_for_continue', False):
                self.send_next_waypoint()

        elif run_cmd == False and self.is_running:
            self.get_logger().info("UI Stop button pressed! Halting robot.")
            self.is_running = False

            # Force stop Nav2
            if getattr(self, 'active_goal_handle', None) is not None:
                self.manual_advance = True
                self.active_goal_handle.cancel_goal_async()
    
    def mode_callback(self, msg):
        self.mode = msg.data
        self.get_logger().info(f"Controller Mode switched to: {self.mode}")

    def selected_objects_callback(self, msg):
        # cannot add items to cart while mission started
        if self.is_running:
            self.get_logger().warn("Cannot update cart while robot is running! Please stop the robot first.")
            return

        # clear existing pending items and populate with newly clicked items
        # then passes control to process_waypoints
        self.pending_items.clear()
        items_str = msg.data.split(',') if msg.data else []

        # splitting demand and upsell string from selected object string
        # name : demand level : upsell level
        for item_str in items_str:
            if not item_str: continue
            parts = item_str.split(':')
            if len(parts) == 3:
                name = parts[0].strip().lower()

                # demand mapping
                d_level = parts[1]
                demand_val = 0
                if d_level == '1' : demand_val = 15
                elif d_level == '2' : demand_val = 10
                elif d_level == '3' : demand_val = 5

                # upsel mapping
                u_level = parts[2]
                upsell_val = 0
                if u_level == '1' : upsell_val = 12
                elif u_level == '2' : upsell_val = 8
                elif u_level == '3' : upsell_val = 4

                if name in self.item_waypoints:
                    self.pending_items.append({
                        'name': name,
                        'pose': self.item_waypoints[name],
                        'demand': demand_val,
                        'upsell': upsell_val
                    })

                else:
                    self.get_logger().warn(f"Unknown item selected: {name}")

        # Update the active mission array
        self.process_waypoints([], "map")

    def image_callback(self, msg):
        try:
            image = self.cv_bridge.imgmsg_to_cv2(msg, "bgr8")
        except cv_bridge.CvBridgeError as e:
            self.get_logger().warn(f"cv_bridge exception: {str(e)}")
    
    def compute_distance(self, a, b):
        dx = a.x - b.x
        dy = a.y - b.y
        return math.sqrt(dx*dx + dy*dy)

    # receives array of waypoints and passes to process_waypoints
    def array_goal_pose_callback(self, msg):
        frame = msg.header.frame_id if msg.header.frame_id else "map"
        self.process_waypoints(msg.poses, frame)
    
    # using Nav2 compute path service to get the length of path between 2 points
    # async and wait are used for non blocking calls, this means the program runs in the background
    # while waiting for the server response, the controller can do other things like receiving callbacks
    async def get_nav2_path_length(self, start_pos, goal_pos):
        if not self.compute_path_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().warn("ComputePathToPose server not available, using Euclidean distannce.")
            return self.compute_distance(start_pos, goal_pos)
        
        goal_msg = ComputePathToPose.Goal()
        goal_msg.use_start = True
        
        start_ps = PoseStamped()
        start_ps.header.frame_id = "map"
        start_ps.pose.position = start_pos
        start_ps.pose.orientation.w = 1.0
        goal_msg.start = start_ps

        goal_ps = PoseStamped()
        goal_ps.header.frame_id = "map"
        goal_ps.pose.position = goal_pos
        goal_ps.pose.orientation.w = 1.0
        goal_msg.goal = goal_ps

        goal_msg.planner_id = "GridBased"

        # Nav2 takes time to calculate path, using future allows non blocking functionality while it is calculating for path
        future = self.compute_path_client.send_goal_async(goal_msg)
        goal_handle = await future

        if not goal_handle.accepted:
            self.get_logger().warn("Path request rejected by Nav2 server, using Euclidean distance.")
            return self.compute_distance(start_pos, goal_pos)

        result_future = goal_handle.get_result_async()
        result = await result_future

        # received path from Nav2 server 
        path = result.result.path

        # if Nav2 fails to generate a path, we use the Euclidean distance between the two points
        if not path.poses:
            self.get_logger().warn("Empty path returned by Nav2 server, using Euclidean distance.")
            return self.compute_distance(start_pos, goal_pos)
        
        total_dist = 0.0
        prev = path.poses[0].pose.position

        # looping individual segments of path to calculate the total length of path
        for i in range(1, len(path.poses)):
            curr = path.poses[i].pose.position
            total_dist += self.compute_distance(prev, curr)
            prev = curr

        return total_dist

    async def calculate_best_next_item(self, current_pos, pending_items, mode, from_name="Robot Start"):
        if not pending_items:
            return None, -1, 0.0
            
        # normal mode 
        a = 1.5 # demand factor
        b = 0.0 # upsell factor
        c = 1.0 # distance factor
        
        if mode == "upsell":
            a = 1.0
            b = 0.8
            c = 1.0
            
        results = []
        for i, item in enumerate(pending_items):
            dist = await self.get_nav2_path_length(current_pos, item['pose'].position)
            score = (a * item['demand']) + (b * item['upsell']) - (c * dist)
            results.append({
                'item': item,
                'idx': i,
                'score': score,
                'dist': dist,
                'name': item['name']
            })
            
        # Sort results by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        
        for rank, res in enumerate(results):
            self.get_logger().info(f"From: {from_name} -> To: {res['name']} | Nav2 Dist: {res['dist']:.2f}m | Score: {res['score']:.2f} | Rank: {rank+1}")
                
        best = results[0]
        return best['item'], best['idx'], best['score']

    # loops through all pending items and query Nav2 for the actual path length for every item in the loop
    # calculate the score for each item using the score formula then store the best item in remaining route
    async def recalculate_remaining_route(self):
        if self.current_goal_idx >= len(self.pending_items):
            return
            
        # remaining updates pending item
        remaining = list(self.pending_items[self.current_goal_idx : ])
        old_route_names = [item['name'] for item in remaining]
        sorted_remaining = []
        
        # get current position
        sim_pos = self.current_pose.position
        if math.isnan(sim_pos.x) or math.isnan(sim_pos.y):
            sim_pos = Pose().position
            sim_pos.x = 0.0
            sim_pos.y = 0.0
            
        if self.current_goal_idx == 0:
            current_from_name = "Robot Start"
        else:
            current_from_name = self.pending_items[self.current_goal_idx - 1]['name']
            
        # use current position and pending items to update remaining route using the score formula
        # add best item to sorted_remaining then remove from remaining, repeat until remaining is empty
        # update self.pending_items to be the sorted_remaining
        while remaining:
            best_item, best_idx, score = await self.calculate_best_next_item(sim_pos, remaining, self.mode, current_from_name)
            sorted_remaining.append(best_item)
            sim_pos = best_item['pose'].position
            current_from_name = best_item['name']
            remaining.pop(best_idx)
            
        new_route_names = [item['name'] for item in sorted_remaining]

        # publish the active route to gui
        route_msg = String()
        route_msg.data = " -> ".join(new_route_names) if new_route_names else "None"
        self.active_route_pub.publish(route_msg)
        
        if old_route_names != new_route_names and len(old_route_names) > 1:
            old_str = " -> ".join(old_route_names)
            new_str = " -> ".join(new_route_names)
            self.get_logger().info(f"*** DYNAMIC ROUTE CHANGE DETECTED ***")
            self.get_logger().info(f"Old Route: {old_str}")
            self.get_logger().info(f"New Route: {new_str}")

        self.pending_items[self.current_goal_idx : ] = sorted_remaining
        
        # store new ordered goals from sorted_remaining in self.goals for controller
        for i, item in enumerate(sorted_remaining):
            idx = self.current_goal_idx + i
            p = item['pose']
            ps = PoseStamped()
            ps.header.frame_id = "map"
            ps.header.stamp = self.get_clock().now().to_msg()
            ps.pose = p
            
            self.waypoints[idx] = ps
            gs = GoalStats(position=p.position, orientation=p.orientation)
            self.goals[idx] = gs
            
        # if we are at the beginning, use current position, otherwise get previous goal position
        prev_pos = self.current_pose.position if self.current_goal_idx == 0 else self.goals[self.current_goal_idx - 1].position
        if math.isnan(prev_pos.x) and self.current_goal_idx == 0 and len(self.goals) > 0:
            prev_pos = self.goals[0].position
            
        # get total distance of remaining segments and subtract from total distance because we recaculated the route
        old_remaining_dist = sum(self.segment_distances[self.current_goal_idx : ])
        self.total_mission_distance -= old_remaining_dist
        
        # calculate new distances and add to total distance for distance travelled using sorted remaining 
        # calculated from the best item 
        new_segments = []
        for i, item in enumerate(sorted_remaining):
            idx = self.current_goal_idx + i
            seg = self.compute_distance(prev_pos, item['pose'].position)
            new_segments.append(seg)
            
            self.total_mission_distance += seg
            prev_pos = item['pose'].position
            
        self.segment_distances[self.current_goal_idx : ] = new_segments
        self.publish_goal_markers()

    # runs asynchronous timer to trigger recalculation in the background
    def trigger_recalculation(self):
        if getattr(self, 'is_calculating', False):
            self.get_logger().warn("Already calculating a route, ignoring trigger.")
            return

        # call recalculate and send async immediately
        self.recalc_timer = self.create_timer(0.0, self.async_recalculate_and_send, callback_group=self.action_cb_group)

    async def recalculate_and_trigger(self):
        if getattr(self, 'is_calculating', False):
            self.get_logger().warn("Already calculating a route, ignoring trigger.")
            return
        
        self.is_calculating = True

    # if calculating flag is true, run recalculate remaining route function and send goals to Nav2 using dispatch_goal
    async def async_recalculate_and_send(self):
        if hasattr(self, 'recalc_timer') and self.recalc_timer:
            self.recalc_timer.cancel()
            self.recalc_timer = None

        self.is_calculating = True
        self.get_logger().info("Asking Nav2 for path distances... this may take a moment.")

        # calculates the path distances using compute_path_to_pose action client and updates the segment_distance list
        await self.recalculate_remaining_route()

        self.is_calculating = False
        self.goal_set = len(self.goals) > 0

        if self.goal_set:
            if self.is_running:
                self.dispatch_goal()
            else:
                self.get_logger().info(f"Waypoints loaded (Mode: {self.mode}). Waiting for UI Start button to begin")

    def process_waypoints(self, poses, frame="map"):
        if not self.pending_items:
            self.get_logger().warn("Empty pending items list received")
            self.goals.clear()
            self.waypoints.clear()
            self.segment_distances.clear()
            self.goal_set = False
            return
        
        # reset goal related variables once pending items are loaded
        self.goals = [None] * len(self.pending_items)
        self.segment_distances = [0.0] * len(self.pending_items)
        self.total_mission_distance = 0.0
        self.completed_mission_distance = 0.0
        self.current_goal_idx = 0
        self.waypoints = [None] * len(self.pending_items)

        # Trigger async route recalculation
        self.trigger_recalculation()

    def send_next_waypoint(self):
        if not self.is_running:
            return
            
        if self.current_goal_idx >= len(self.waypoints):
            self.get_logger().info("All waypoints completed successfully!")
            self.goal_set = False
            self.is_running = False
            
            run_msg = Bool()
            run_msg.data = False
            self.robot_run_pub.publish(run_msg)
            
            status_msg = String()
            status_msg.data = "Mission Complete."
            self.status_pub.publish(status_msg)
            return
        
        # trigger async route recalculation
        self.trigger_recalculation()

    # send goal with current target from pending items and current goal index to Nav2 to execute 
    def dispatch_goal(self):
        if not self.is_running:
            return
        
        if self.current_goal_idx >= len(self.waypoints):
            return

        current_target = self.pending_items[self.current_goal_idx]
        self.get_logger().info(f"Dynamic Route: Selected '{current_target['name']}' as next target.")

        goal_msg = NavigateToPose.Goal()
        fresh_pose = self.waypoints[self.current_goal_idx]
        fresh_pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose = fresh_pose

        self.get_logger().info(f"Sending NavigateToPose goal for waypoint {self.current_goal_idx + 1}/{len(self.waypoints)}")

        # Async send goal execution
        send_goal_future = self.navigate_to_pose_client.send_goal_async(
            goal_msg,
            feedback_callback=self.handle_feedback
        )

        send_goal_future.add_done_callback(self.handle_goal_response)

    def handle_goal_response(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error("Goal was rejected by server")
            self.goal_set = False
            return

        self.active_goal_handle = goal_handle
        self.get_logger().info("NavigateToPose goal accepted by server, waiting for result")

        # Wait for the action to complete()
        self.get_result_future = goal_handle.get_result_async()
        self.get_result_future.add_done_callback(self.handle_result)

    def handle_feedback(self, feedback_msg):
        # The feedback message contains feedback form action server
        self.publish_telemetry()

    def handle_result(self, future):
        result = future.result()
        
        if result.status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f"Waypoint {self.current_goal_idx + 1} succeeded organically by Nav2.")
            if self.current_goal_idx < len(self.segment_distances):
                self.completed_mission_distance += self.segment_distances[self.current_goal_idx]
            self.current_goal_idx += 1
            self.send_next_waypoint()
        elif result.status == GoalStatus.STATUS_ABORTED:
            if getattr(self, 'manual_advance', False):
                self.manual_advance = False
                self.get_logger().info("Nav2 aborted old goal safely because loop forced the next point.")
            else:
                self.get_logger().error(f"CRITICAL: Waypoint {self.current_goal_idx + 1} was completely rejected by Nav2 global planner! It is likely inside a wall or obstacle. Halting mission.")
                self.goal_set = False
        elif result.status == GoalStatus.STATUS_CANCELED:
            if getattr(self, 'manual_advance', False):
                self.manual_advance = False
                self.get_logger().info("Nav2 cancelled old goal safely because loop forced the next point.")
            else:
                self.get_logger().warn("NavigateToPose action cancelled.")
    
    def publish_goal_markers(self):
        arr = MarkerArray()
        now = self.get_clock().now().to_msg()

        marker_id = 0
        for i, g in enumerate(self.goals):
            if g is None:
                continue
            m = Marker()
            m.header.frame_id = "map"
            m.header.stamp = now
            m.ns = "goals"
            m.id = marker_id
            marker_id += 1
            m.type = Marker.SPHERE
            m.action = Marker.ADD
            m.pose.position = g.position
            m.pose.orientation = g.orientation
            m.scale.x = 0.3
            m.scale.y = 0.3
            m.scale.z = 0.3

            if i == self.current_goal_idx:
                m.color.r = 0.0
                m.color.g = 1.0
                m.color.b = 0.0
            else:
                m.color.r = 0.0
                m.color.g = 0.5
                m.color.b = 0.2
            m.color.a = 1.0

            # Using builtin_interfaces.msg.Duration object to ensure valid time layout
            m.lifetime = Duration(sec=1, nanosec=0)

            arr.markers.append(m)

            if i == self.current_goal_idx:
                arrow = Marker()
                arrow.header.frame_id = "map"
                arrow.header.stamp = now
                arrow.ns = "current_goal_arrow"
                arrow.id = marker_id
                marker_id += 1
                arrow.type = Marker.ARROW
                arrow.action = Marker.ADD
                
                arrow.points.append(self.current_pose.position)
                arrow.points.append(g.position)
                
                arrow.scale.x = 0.05
                arrow.scale.y = 0.1
                arrow.scale.z = 0.2
                
                arrow.color.r = 1.0
                arrow.color.g = 0.0
                arrow.color.b = 0.0
                arrow.color.a = 1.0
                
                arrow.lifetime = Duration(sec=0, nanosec=200_000_000) # 200ms
                
                arr.markers.append(arrow)

        if arr.markers:
            self.marker_pub.publish(arr)

    def publish_telemetry(self):
        dist_msg = String()
        prog_msg = Float64()

        progress = 0.0
        completed = 0.0

        if not self.goal_set or not self.goals or self.total_mission_distance <= 1e-6:
            progress = 0.0
        else:
            cur = self.current_pose
            current_segment_completed = 0.0
            
            if self.current_goal_idx < len(self.goals):
                seg_len = self.segment_distances[self.current_goal_idx]
                
                # Dynamic Odom Fix: If first segment was tracked as 0 because of missing boot-up Odometry, fix it here and now!
                if seg_len <= 1e-6 and self.current_goal_idx == 0 and not math.isnan(cur.position.x):
                    seg_len = self.compute_distance(cur.position, self.goals[0].position)
                    self.segment_distances[0] = seg_len
                    self.total_mission_distance += seg_len
                    self.get_logger().info(f"Boot-up tracking fixed. First segment mapped manually as {seg_len:.2f}m")

                to_goal = self.compute_distance(cur.position, self.goals[self.current_goal_idx].position)

                if seg_len > 1e-6:
                    current_segment_completed = max(0.0, seg_len - to_goal)

            completed = self.completed_mission_distance + current_segment_completed
            # self.get_logger().info(f"Goal {self.current_goal_idx} distance travelled: {completed}")
            
            progress = (completed / self.total_mission_distance) * 100.0 if self.total_mission_distance > 1e-6 else 0.0
            # self.get_logger().info(f"Progress of mission: {progress}")

            progress = max(0.0, min(100.0, progress))
        
        dist_msg.data = f"{completed:.2f}m / {self.total_mission_distance:.2f}m"
        prog_msg.data = progress

        self.mission_distance_pub.publish(dist_msg)
        self.mission_progress_pub.publish(prog_msg)

def main(args=None):
    rclpy.init(args=args)
    node = Controller()
    executor = MultiThreadedExecutor()
    try:
        # spinning multithreaded executor allows for concurrent execution of callbacks
        rclpy.spin(node, executor=executor)
    except KeyboardInterrupt:
        node.get_logger().info("Turtlebot controller node shutting down")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()