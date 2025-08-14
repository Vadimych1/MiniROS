import pybullet as p
import numpy as np
import time
from typing import Any
from miniros import decorators, datatypes, AsyncROSClient
import pybullet_data

_JointsDictType = dict[str, int]
physicsClient = p.connect(p.GUI, options="--opengl2")

p.setAdditionalSearchPath(pybullet_data.getDataPath())

p.setGravity(0, 0, -9.8)

def load_joints(robot_id: int):
    joints = {}
    
    for i in range(p.getNumJoints(robot_id)):
        joint_info = p.getJointInfo(robot_id, i)
        
        name = joint_info[1].decode()
        joints[name] = i
    
    return joints

        
def set_joint_speed(name: str, speed: float, joints: _JointsDictType, robot_id: int = 0):
    assert name in joints, f"joint {name} is not loaded"
    p.setJointMotorControl2(robot_id, joints[name], p.VELOCITY_CONTROL, targetVelocity=speed)


def load_urdf(path: str, xyz: list[float] = [0, 0, 0], rpy: list[float] = [0, 0, 0]) -> int:
    id = p.loadURDF(path, 
        basePosition = xyz,
        baseOrientation = p.getQuaternionFromEuler(rpy),
    )
    
    return id


class Sensor:
    def __init__(self, name: str, root: "Robot", topic_name: str | None, xyz: list[float] = [0, 0, 0], rpy: list[float] = [0, 0, 0]):
        self.topic_name = topic_name
        self.name = name
        self.root = root
        self.topic = None
        
        self.xyz = xyz
        self.rpy = rpy
    
        self.attributes = {}
    
    async def initialize(self):
        if self.topic_name is not None:
            self.topic = await self.root.topic(self.name, datatypes.Bytes)
    
    def set_attribute(self, name: str, value: Any):
        self.attributes[name] = value
    
    def measure(self) -> datatypes.Datatype:
        raise NotImplementedError
        
    async def measure_and_post(self):
        assert self.topic_name is not None, "topic_name is not specified"
        assert self.topic is not None, "Sensor.initialize needs to be called before posting"
        
        m = self.measure()
        await self.topic.post(type(m).encode(m))
        
class LidarSensor(Sensor):
    def __init__(self, root: "Robot", name: str = "lidar", topic_name: str | None = None, xyz: list[float] = [0, 0, 0], rpy: list[float] = [0, 0, 0]):
        super().__init__(name, root, topic_name, xyz, rpy)
        
        self.attributes = {
            "measures_per_scan": 360,
            "scan_angle": 360, # degrees
            "scan_distance": 12, # meters
        }
    
    def measure(self) -> datatypes.LidarDatatype:
        """
        Returns real-like LiDAR scan
        
        Distance in mm, angles in degrees 
        """
        position, orientation = p.getBasePositionAndOrientation(self.root.id)        
        pos = np.asarray(position) + np.asarray(self.xyz)
        
        orientation = p.getEulerFromQuaternion(orientation)
        
        start_positions = [pos] * self.attributes["measures_per_scan"]
        end_positions = []
        
        dist = self.attributes["scan_distance"] * 10
        angle_per_scan = self.attributes["scan_angle"] / self.attributes["measures_per_scan"]

        angles = []
        offset = np.random.random() / 10 # for more realistic values
        
        for r in range(self.attributes["measures_per_scan"]):
            r = np.deg2rad(r * angle_per_scan) + offset
            rq = r + orientation[2] + np.pi / 2
            angles.append(np.rad2deg(r))
            end_positions.append(pos + np.asarray([np.cos(rq) * dist, np.sin(rq) * dist, 0]))
        
        raycasts = p.rayTestBatch(
            start_positions,
            end_positions,
        )
        
        distances = [np.linalg.norm(pos - np.array(rc[3])) * 100 for rc in raycasts]
    
        a_d_pairs = [(angle, distance) for angle, distance, rc in zip(angles, distances, raycasts) if distance > 0 and rc[0] > -1]
        if len(a_d_pairs) > 0:
            angles, distances = zip(*a_d_pairs)
        else:
            angles, distances = [], []
    
        return datatypes.LidarDatatype(distances, angles)
        
class JointGroup:
    def __init__(self, root: "Robot", joints: list[str]):
        self.root = root
        self.joints = joints
        
    def set_speed(self, speed: float):
        for j in self.joints:
            self.root.set_joint_speed(j, speed)

class Robot(AsyncROSClient):
    def __init__(self, urdf: "str", startPos: list[float] = [0, 0, 1], startOrientation: list[float] = [0, 0, 0], miniros_name: str | None = None, ip: str = "localhost", port: int = 3000):
        """
        MiniROS client for simulation
        
        Supports all methods of AsyncROSClient
        """
        if miniros_name is not None:
            super().__init__(miniros_name, ip, port)
        
        self.id = load_urdf(urdf, startPos, startOrientation)
        
        self.sensors = {}
        self.joint_groups = []
        
        self.joints = load_joints(self.id)
        
    def set_joint_speed(self, name: str, speed: float) -> None:
        set_joint_speed(name, speed, self.joints, self.id)
        
    def create_joint_group(self, joints: list[str]) -> "JointGroup":
        g = JointGroup(self, joints)
        self.joint_groups.append(g)
        return g
    
    def create_sensor(self, name: str, topic_name: str | None, base_class: type[Sensor] = Sensor, xyz: list[float] = [0, 0, 0], rpy: list[float] = [0, 0, 0]):
        assert name not in self.sensors, "sensor names must be unique"
        
        s = base_class(self, name, topic_name, xyz, rpy)
        self.sensors[name] = s
        return s

@decorators.threaded()
def mainloop(fps: int = 120):
    """
    Start simulation mainloop
    
    Will not block current thread
    """

    try:
        while True:
            p.stepSimulation()
            time.sleep(1 / fps)
    finally:
        p.disconnect()
