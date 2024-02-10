import logging
from functools import wraps
from time import sleep
from typing import List, Tuple, Union, Optional
from enum import IntEnum
from xarm.wrapper import XArmAPI
import threading
from modules._utils import Singleton
from modules.config import SharedExtConfig
from modules._dataclasses import (Velocity,
    JointPose, 
    CartesianPose
)

class MotionType(IntEnum):
    linear = 0
    linear_or_joint = 1
    joint = 2


def retry_decorator(func):
    '''
    decorator to retry function call on RobotException up to self._config.retry_attempts times
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        logger = self._logger.getChild("retry_decorator")
        assert isinstance(self, RobotAdapter), "retry_decorator can only be used with RobotAdapter methods"
        for attempt in range(self._config.retry_attempts):
            try:
                return func(*args, **kwargs)
            except RobotException as e:
                exc = e
                logger.error(f"attempt {attempt + 1} failed: {e}")
                self.enable_robot()
                sleep(1)
                logger.info("retrying...")
        else:
            raise exc
    return wrapper


def ret_raise(func):
    '''
    decorator to raise RobotException if function returns non-zero code
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        ret = func(*args, **kwargs)
        if ret != 0:
            raise RobotException(f"{func.__name__} failed: {ret}")
    return wrapper


class RobotException(Exception):
    pass


class WrongModeException(RobotException):
    pass


class RobotAdapter(metaclass=Singleton):
    def __init__(self):
        self._logger = logging.getLogger("robot_adapter")
        self._config = SharedExtConfig()
        self._asked_mode = 0
        self._enable_lock = threading.Lock()
        self._robot = XArmAPI(self._config.robot_ip,
                              is_radian=False,
                              do_not_open=False)
        print("RobotAdapter init")
        self._set_mode()
        
    
    def park(self):
        pose = self._config.poses.park
        self.move_to(pose, self._config.velocities.reduced, linear=True)


    @retry_decorator
    def move_to(self, pose: Union[JointPose, CartesianPose],
                velocity: Velocity, 
                linear: Optional[bool] = False):
        '''
        moves robot to specified pose
        @param linear: if True and pose is CartesianPose, robot will move linearly
        '''
        self._set_mode(0)
        if isinstance(pose, JointPose):
            ret_raise(self._robot.set_servo_angle)(angle=pose.values, speed=velocity.joint, wait=True)
        elif isinstance(pose, CartesianPose):
            if linear:
                ret_raise(self._robot.set_position)(*pose.position, *pose.orientation, speed=velocity.linear, wait=True, motion_type=MotionType.linear)
            else:
                ret_raise(self._robot.set_position)(*pose.position, *pose.orientation, speed=velocity.linear, wait=True, motion_type=MotionType.joint)
        else:
            raise ValueError("pose must be JointPose or CartesianPose")
        

    @retry_decorator
    def _set_mode(self, mode: int=None):
        if mode is None:
            mode = self._asked_mode
        if self._robot.has_err_warn:
            raise RobotException(f"robot has error or warning: {self._robot.error_code}, {self._robot.warn_code}")
        if self._robot.mode == mode:
            return
        self._logger.info(f"setting mode {self._robot.mode} -> {mode}")
        self._asked_mode = mode
        ret_raise(self._robot.set_mode)(mode)
        ret_raise(self._robot.set_state)(0)
        sleep(0.1)
        # check if mode was set
        if self._robot.mode != mode:
            raise WrongModeException(f"current mode: {self._robot.mode}, asked mode: {mode}")


    def enable_robot(self):
        logger = self._logger.getChild("enable_method")
        with self._enable_lock:
            self._robot.clean_error()
            self._robot.clean_warn()
            self._robot.motion_enable(enable=True)
            self._robot.set_mode(self._asked_mode)
            self._robot.set_state(0)
            