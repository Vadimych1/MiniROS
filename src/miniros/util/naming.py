class Node:
    MOTION_CONTROLLER = "motncontrol"
    MOTOR_CONTROLLER = "motrcontrol"
    PATH_PLANNER = "pplanner"
    LIDAR = "lidar"
    SLAM = "slam"
    GOAL_MANAGER = "goalmgr"
    CAMERA = "cam"

class Topic:
    # motion controller
    MC_CMDVEL = "cmdvel"

    # lidar   
    L_SCAN = "scan"
    L_POINT_CLOUD = "pcl"

    # slam
    SLAM_OCCUPANCY_GRID = "occgrid"
    SLAM_POSE = "pose"
    
    # odometry
    O_VELOCITY = "vel"
    O_POSE = "pose"
    
    # goal manager
    GM_GOAL = "goal"

    # path planner
    PP_PATH = "path"
    
    # camera
    CAM_FRAME_RGB = "frgb"
    CAM_FRAME_GRAY = "fgray"
