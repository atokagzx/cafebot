import os, sys
import json
import logging
from modules._utils import Singleton
from modules._dataclasses import *


class SharedExtConfig(metaclass=Singleton):
    def __init__(self):
        self._logger = logging.getLogger("shared_ext_config")
        self._load_config()


    def _load_config(self):
        try:
            self._stand_name = os.environ["STAND_NAME"]
        except KeyError:
            _default_stand_name = "default_stand"
            self._logger.warning(f'"STAND_NAME" environment variable not set, using: {_default_stand_name}')
            self._stand_name = _default_stand_name
        self._logger.info(f"stand name: {self._stand_name}")
        config_file_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                    os.pardir, os.pardir, "config", "ext_config.json"))
        self._logger.info(f'loading config from: {config_file_path}')
        with open(config_file_path, "r") as f:
            config_dict = json.load(f)[self._stand_name]
        self._ext_config = ExtConfig(**config_dict['general'])
        self._logger.info(f"ext config: {self._ext_config}")
        self._poses = Poses(**config_dict['poses'])
        self._logger.info(f"poses: {self._poses}")
        self._velocities = Velocities(**config_dict['velocities'])
        self._logger.info(f"velocities: {self._velocities}")
        
    
    @property
    def stand_name(self):
        return self._stand_name
    

    @property
    def robot_ip(self):
        return self._ext_config.robot_ip
    

    @property
    def retry_attempts(self):
        return self._ext_config.retry_attempts
    

    @property
    def velocities(self):
        return self._velocities
    

    @property
    def poses(self):
        return self._poses
    