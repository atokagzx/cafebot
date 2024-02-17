from typing import List, Tuple, Union
from dataclasses import dataclass


@dataclass
class ExtConfig:
    robot_ip: str
    retry_attempts: int


@dataclass
class JointPose:
    values: Tuple[float, float, float, float, float, float]

    def __post_init__(self):
        assert len(self.values) == 6, "joint pose must have 6 values"
        self.values = tuple(map(lambda x: x, self.values))


@dataclass
class CartesianPose:
    position: Tuple[float, float, float]
    orientation: Tuple[float, float, float]
    frame: str
    tcp: str

    def __post_init__(self):
        assert len(self.position) == 3, "position must have 3 values"
        assert len(self.orientation) == 3, "orientation must have 3 values"
        self.position = tuple(self.position)
        self.orientation = tuple(self.orientation)


@dataclass
class Poses:
    park: Union[JointPose, CartesianPose]
    stand: Union[JointPose, CartesianPose]
    
    def __post_init__(self):
        type_to_dataclass = {"joint": JointPose, 
                             "cartesian": CartesianPose}
        for attr_name in self.__annotations__:
            pose = getattr(self, attr_name)
            pose_type = pose.pop("type")
            dataclass = type_to_dataclass[pose_type]
            setattr(self, attr_name, dataclass(**getattr(self, attr_name)))


@dataclass
class Velocity:
    joint: float
    linear: float


@dataclass
class Velocities:
    reduced: Velocity
    normal: Velocity
    
    def __post_init__(self):
        for attr_name in self.__annotations__:
            setattr(self, attr_name, Velocity(**getattr(self, attr_name)))
            

@dataclass
class TCPOffset:
    x: float
    y: float
    z: float
    roll: float
    pitch: float
    yaw: float


    def as_list(self) -> List[float]:
        return [self.x, self.y, self.z, self.roll, self.pitch, self.yaw]


@dataclass
class BaseOffset:
    x: float
    y: float
    z: float
    roll: float
    pitch: float
    yaw: float

    def as_list(self) -> List[float]:
        return [self.x, self.y, self.z, self.roll, self.pitch, self.yaw]
    
