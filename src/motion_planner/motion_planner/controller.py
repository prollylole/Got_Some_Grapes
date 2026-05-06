#!/usr/bin/env python3

import math
import cv2
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from sensor_msgs.msg import LaserScan, Image
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseArray, PoseStamped, Pose
from visualization_msgs.msg import MarkerArray, Marker
from std_msgs.msg import Float64
from builtin_interfaces.msg import Duration
from action_msgs.msg import GoalStatus
from std_msgs.msg import Bool, String

from nav2_msgs.action import NavigateToPose
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

        # self.image_sub = self.create_subscription(
        #     Image,
        #     '/camera/image',
        #     self.image_callback,
        #     5
        # )

        # Publishers
        self.marker_pub = self.create_publisher(MarkerArray, '/visualization_marker', 10)
        self.mission_progress_pub = self.create_publisher(Float64, '/mission_progress', 10)
        self.mission_distance_pub = self.create_publisher(Float64, '/mission_distance', 10)
        self.status_pub = self.create_publisher(String, 'robot_status', 10)
        self.trigger_scan_pub = self.create_publisher(Bool, '/trigger_scan', 10)

        # continue/pause button 
        self.waiting_for_continue = False
        
        # UI Start/Stop button
        self.is_running = False
        self.run_sub = self.create_subscription(
            Bool, 
            '/robot_run', 
            self.robot_run_callback, 
            10)

        # Action Client for Nav2
        self.navigate_to_pose_client = ActionClient(
            self,
            NavigateToPose,
            self.navigate_to_pose_action_name
        )

        if not self.navigate_to_pose_client.wait_for_server(timeout_sec=3.0):
            self.get_logger().warn(f"NavigateToPose action server '{self.navigate_to_pose_action_name}' not available yet.")
        else:
            self.get_logger().info(f"NavigateToPose action client connected to '{self.navigate_to_pose_action_name}'.")
            
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

        # Check distance to current goal
        cur_pos = self.current_pose.position
        goal_pos = self.goals[self.current_goal_idx].position

        dist = self.compute_distance(cur_pos, goal_pos)

        if dist < 1.0 and not self.waiting_for_continue:
            self.get_logger().info(f"Waypoint {self.current_goal_idx + 1} reached! Pausing robot for Continue button...")
            
            # Cancel the active Nav2 driving goal so the robot actually stops moving!
            if hasattr(self, 'active_goal_handle') and self.active_goal_handle is not None:
                self.active_goal_handle.cancel_goal_async()
            
            # Formally register this segment's distance as completed
            if self.current_goal_idx < len(self.segment_distances):
                self.completed_mission_distance += self.segment_distances[self.current_goal_idx]

            self.manual_advance = True 
            self.waiting_for_continue = True 
            
            scan_msg = Bool()
            scan_msg.data = True
            self.trigger_scan_pub.publish(scan_msg)
            
            status_msg = String()
            status_msg.data = f"Arrived at Waypoint {self.current_goal_idx + 1}. Auto-scanning..."
            self.status_pub.publish(status_msg)
            
    def laser_callback(self, msg):
        self.last_scan = msg
        self.laser_received = True 

    def odom_callback(self, msg):
        self.current_pose = msg.pose.pose

    def robot_run_callback(self, msg):
        run_cmd = msg.data
        if run_cmd == True and not self.is_running:
            self.get_logger().info("UI Start button pressed! Resuming navigation.")
            self.is_running = True
            
            # If we have goals loaded and we aren't waiting at a shelf, start driving!
            if self.goal_set and not self.waiting_for_continue:
                self.send_next_waypoint()
                
        elif run_cmd == False and self.is_running:
            self.get_logger().info("UI Stop button pressed! Halting robot.")
            self.is_running = False
            
            # Force stop Nav2
            if hasattr(self, 'active_goal_handle') and self.active_goal_handle is not None:
                self.active_goal_handle.cancel_goal_async()

    def continue_callback(self, msg):
        if msg.data == True and self.waiting_for_continue:
            # The user clicked Continue on the GUI
            self.get_logger().info("Continue button pressed by user! Moving to the next waypoint.")
            self.waiting_for_continue = False

            self.current_goal_idx += 1
            self.send_next_waypoint()

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

    def process_waypoints(self, poses, frame="map"):
        if not poses:
            self.get_logger().warn("Empty goal pose list received")
            return

        waypoints = []

        # Reset mission tracking variables
        # erase waypoints from previous missions
        self.goals.clear()
        self.segment_distances.clear()
        self.total_mission_distance = 0.0
        self.completed_mission_distance = 0.0
        self.current_goal_idx = 0

        prev_pose = self.current_pose

        # Uninitiliased pose check
        have_prev = True
        if math.isnan(prev_pose.position.x) and math.isnan(prev_pose.position.y):
            have_prev = False
        
        for p in poses:
            ps = PoseStamped()
            ps.header.frame_id = frame
            ps.header.stamp = self.get_clock().now().to_msg()
            ps.pose = p
            waypoints.append(ps)

            gs = GoalStats(position=p.position, orientation=p.orientation)
            self.goals.append(gs)
            self.get_logger().info(f"Goal {self.current_goal_idx + 1}: x={p.position.x}, y={p.position.y}, theta={p.orientation.z}")

            seg = 0.0
            if have_prev:
                seg = self.compute_distance(prev_pose.position, p.position)

            self.segment_distances.append(seg)
            self.total_mission_distance += seg
            self.get_logger().info("total mission distance: " + str(self.total_mission_distance))

            prev_pose = p 
            have_prev = True 
        
        self.waypoints = waypoints
        self.goal_set = len(self.goals) > 0
        
        if self.goal_set:
            if self.is_running:
                self.send_next_waypoint()
            else:
                self.get_logger().info("Waypoints loaded. Waiting for UI Start button to begin.")

    def send_next_waypoint(self):
        if not self.is_running:
            return

        if self.current_goal_idx >= len(self.waypoints)+1:
            self.get_logger().info("All waypoints completed successfully!")
            self.goal_set = False
            return
            
        # if not self.navigate_to_pose_client.wait_for_server(timeout_sec=2.0):
        #     self.get_logger().warn("NavigateToPose action server not available. Will retry later.")
        #     return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = self.waypoints[self.current_goal_idx]

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

        self.get_logger().info("NavigateToPose goal accepted by server, waiting for result")
        
        self.active_goal_handle = goal_handle

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
                
                arrow.scale.x = 5.0
                arrow.scale.y = 5.0
                arrow.scale.z = 5.0
                
                arrow.color.r = 1.0
                arrow.color.g = 0.2
                arrow.color.b = 0.2
                arrow.color.a = 1.0
                
                arrow.lifetime = Duration(sec=0, nanosec=200_000_000) # 200ms
                
                arr.markers.append(arrow)

        if arr.markers:
            self.marker_pub.publish(arr)

    def publish_telemetry(self):
        dist_msg = Float64()
        prog_msg = Float64()

        progress = 0.0

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
            self.get_logger().info(f"Goal {self.current_goal_idx} distance travelled: {completed}")
            
            progress = (completed / self.total_mission_distance) * 100.0 if self.total_mission_distance > 1e-6 else 0.0
            self.get_logger().info(f"Progress of mission: {progress}")

            progress = max(0.0, min(100.0, progress))
        
        dist_msg.data = self.total_mission_distance
        prog_msg.data = progress

        self.mission_distance_pub.publish(dist_msg)
        self.mission_progress_pub.publish(prog_msg)

def main(args=None):
    rclpy.init(args=args)
    node = Controller()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Turtlebot controller node shutting down")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
