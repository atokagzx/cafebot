import logging
from functools import wraps
from time import sleep
from typing import List, Tuple, Union, Optional
from enum import IntEnum
import json
from xarm.wrapper import XArmAPI
import threading
from modules._utils import Singleton
from modules.config import SharedExtConfig
from modules._dataclasses import (Velocity,
    JointPose, 
    CartesianPose,
    TCPOffset,
    BaseOffset,
)
from modules._exceptions import (RobotException, 
                                 WrongModeException,
                                 ConfigException)
from modules.xarm_ws import XArmWebsocket as WS
import numpy as np

class MotionType(IntEnum):
    linear = 0
    linear_or_joint = 1
    joint = 2


def retry_decorator(func):
    '''
    decorator to retry function call on RobotException up to self._config.retry_attempts times
    '''
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        logger = self._logger.getChild("retry_decorator")
        assert isinstance(self, RobotAdapter), "retry_decorator can only be used with RobotAdapter methods"
        for attempt in range(self._config.retry_attempts):
            try:
                return func(self, *args, **kwargs)
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


class RobotAdapter(metaclass=Singleton):
    def __init__(self):
        self._logger = logging.getLogger("robot_adapter")
        self._config = SharedExtConfig()
        self._asked_mode = 0
        self._enable_lock = threading.Lock()
        self._robot = XArmAPI(self._config.robot_ip,
                              is_radian=False,
                              do_not_open=False)
        self._logger.info(f"Robot connection config:\n\tstream type: {self._robot._arm._stream_type}\n\tenable_report: {self._robot._arm._enable_report}")
        self._set_mode()
        
    
    def park(self):
        self._logger.info("parking robot")
        pose = self._config.poses.park
        self.move_to(pose, self._config.velocities.reduced, linear=True)
        self._logger.info("robot parked successfully")


    def _set_tcp_config(self, name: str):
        available_configs = WS().get_tcp_configs()
        if name not in available_configs:
            available_configs_str = "\n".join(f"- {name}: {value}" for name, value in available_configs.items())
            self._logger.error(f'not found TCP config "{name}" from available:\n{available_configs_str}')
            raise ConfigException(f"TCP config '{name}' not available")
        config = available_configs[name]
        assert isinstance(config, TCPOffset), f"expected TCPOffset, got {type(config)}"
        self._logger.info(f'setting TCP config "{name}": {config}')
        ret_raise(self._robot.set_tcp_offset)(config.as_list(), is_radian=True)
        current_config = self._robot.tcp_offset
        current_config[3:] = list(map(lambda x: round(x / 180 * 3.14159, 4), current_config[3:]))
        if np.linalg.norm(np.array(current_config) - np.array(config.as_list())) > 0.01:
            err_msg = f"failed to set TCP config '{name}': {current_config} vs {config}"
            self._logger.error(err_msg)
            raise RobotException(err_msg)
        self._logger.info(f'TCP config "{name}" set successfully')
        self.enable_robot()


    def _set_base_config(self, name: str):
        available_configs = WS().get_base_configs()
        if name not in available_configs:
            available_configs_str = "\n".join(f"- {name}: {value}" for name, value in available_configs.items())
            self._logger.error(f'not found base config "{name}" from available:\n{available_configs_str}')
            raise ConfigException(f"base config '{name}' not available")
        config = available_configs[name]
        assert isinstance(config, BaseOffset), f"expected BaseOffset, got {type(config)}"
        self._logger.info(f'current base config: {self._robot.world_offset}')
        self._logger.info(f'setting base config "{name}": {config}')
        ret_raise(self._robot.set_world_offset)(config.as_list(), is_radian=True)
        # get and check if config was set
        sleep(0.5)
        current_config = self._robot.world_offset
        current_config[3:] = list(map(lambda x: round(x / 180 * 3.14159, 4), current_config[3:]))
        if np.linalg.norm(np.array(current_config) - np.array(config.as_list())) > 0.01:
            err_msg = f"failed to set base config '{name}': {current_config} vs {config}"
            self._logger.error(err_msg)
            raise RobotException(err_msg)
        self._logger.info(f'base config "{name}" set successfully')
        self.enable_robot()
        

    @retry_decorator
    def move_to(self, pose: Union[JointPose, CartesianPose],
                velocity: Velocity, 
                linear: Optional[bool] = False) -> None:
        '''
        moves robot to specified pose
        @param linear: if True and pose is CartesianPose, robot will move linearly
        '''
        self._set_mode(0)
        if isinstance(pose, JointPose):
            ret_raise(self._robot.set_servo_angle)(angle=pose.values, speed=velocity.joint, wait=True)
        elif isinstance(pose, CartesianPose):
            self._set_tcp_config(pose.tcp)
            self._logger.info(f"moving to pose: {pose}, current mode: {self._robot.mode}, state: {self._robot.state}")
            if linear:
                ret_raise(self._robot.set_position)(*pose.position, *pose.orientation, speed=velocity.linear, wait=True, motion_type=MotionType.linear)
            else:
                ret_raise(self._robot.set_position)(*pose.position, *pose.orientation, speed=velocity.linear, wait=True, motion_type=MotionType.joint)
        else:
            raise ValueError("pose must be JointPose or CartesianPose")
        

    @retry_decorator
    def _set_mode(self, mode: int=None) -> None:
        if mode is None:
            mode = self._asked_mode
        if self._robot.has_err_warn:
            raise RobotException(f"robot has error or warning: {self._robot.error_code}, {self._robot.warn_code}")
        if self._robot.mode == mode:
            return
        if self._robot.state == 5:
            self.enable_robot()
        self._logger.info(f"setting mode {self._robot.mode} -> {mode}")
        self._asked_mode = mode
        ret_raise(self._robot.set_mode)(mode)
        ret_raise(self._robot.set_state)(0)
        sleep(0.1)
        # check if mode was set
        if self._robot.mode != mode:
            raise WrongModeException(f"current mode: {self._robot.mode}, asked mode: {mode}")
        if self._robot.state != 0:
            raise WrongModeException(f"failed to set state 0: {self._robot.state}")


    def enable_robot(self) -> None:
        self._logger.info("enabling robot")
        with self._enable_lock:
            self._robot.clean_error()
            self._robot.clean_warn()
            self._robot.motion_enable(enable=True)
            self._robot.set_mode(self._asked_mode)
            self._robot.set_state(0)
        self._logger.info(f"current mode: {self._robot.mode}, state: {self._robot.state}")
        