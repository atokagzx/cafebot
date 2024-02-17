import json
import time
import threading
import websocket
import logging
from functools import wraps
from dataclasses import dataclass
from modules._utils import Singleton
from modules.config import SharedExtConfig
from modules._exceptions import WebsocketException
from modules._dataclasses import (TCPOffset,
                                  BaseOffset)


def connection_handler_wrapper(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger("connection_handler")
        SP = WSSessionProvider
        for i in range(5):
            if SP().connection is None:
                SP().establish_connection()
            if SP().connection is not None:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    SP().close_connection()
            logger.warning(f"connection failed, retrying {i+1}/5")
            time.sleep(1)
        else:
            logger.warning(f"connection failed")
            return None
    return wrapper


def ws_retry_decorator(func):
    '''
    decorator to retry function call on RobotException up to self._config.retry_attempts times
    '''
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        logger = self._logger.getChild("ws_retry_decorator")
        assert isinstance(self, XArmWebsocket), "ws_retry_decorator can only be used with XArmWebsocket methods"
        for attempt in range(SharedExtConfig().retry_attempts):
            try:
                return func(self, *args, **kwargs)
            except WebsocketException as e:
                exc = e
                logger.error(f"attempt {attempt + 1} failed")
                time.sleep(1)
                logger.info("retrying...")
        else:
            raise exc
    return wrapper


class WSSessionProvider(metaclass=Singleton):
    def __init__(self):
        self._logger = logging.getLogger("ws_session")
        self._connection = None
        self._receive_thread = None
        self._cmd_id = 100
        self._pending_cmds = {}
        self.establish_connection()


    @property
    def connection(self):
        return self._connection
    

    @property
    def cmd_id(self):
        cmd_id_temp = self._cmd_id
        self._cmd_id += 1
        self._pending_cmds[cmd_id_temp] = None
        return cmd_id_temp
    

    @property
    def pending_cmds(self):
        return self._pending_cmds
    

    def close_connection(self):
        self._logger.info("closing connection")
        try:
            self._connection and self._connection.close() 
        except Exception as e:
            self._logger.exception(f"failed to close connection: {e}")
        self._connection = None
    

    def update_connection(self):
        self._logger.info("updating connection")
        self.close_connection()
        self.establish_connection()


    def establish_connection(self):
        if self._connection is not None:
            self._logger.info("connection already established")
            return
        self._connection = websocket.WebSocket()
        uri = f"ws://{SharedExtConfig().robot_ip}:18333/ws?channel=prod&lang=en&v=1"
        try:
            self._connection.connect(uri, timeout=None)
        except ConnectionRefusedError as e:
            self._logger.warning(f"connection refused by: {uri}")
            self._connection = None
        else:
            self._logger.info(f"connection established with: {uri}")
            self._pending_cmds = {}
            self._receive_thread = threading.Thread(target=self._receive, daemon=True)
            self._receive_thread.start()


    def _receive(self):
        while True:
            try:
                response = self._connection.recv()
                response = json.loads(response)
                # self._logger.info(f"received response: {response}")
                cmd_id = response.get("id")
                if cmd_id is not None and int(cmd_id) in self._pending_cmds.keys():
                    self._logger.info(f"received response for command: {cmd_id}")
                    self._pending_cmds[int(cmd_id)] = response
            except Exception:
                self._logger.exception(f"failed to receive response")
                break
        self._logger.info("receive thread stopped")


deg2rad = lambda x: x * 3.141592653589793 / 180


class XArmWebsocket(metaclass=Singleton):
    def __init__(self):
        self._logger = logging.getLogger("xarm_ws")

    
    @connection_handler_wrapper
    def _send_command(self, cmd:str, data:dict):
        cmd_id = WSSessionProvider().cmd_id
        command = {
            "data": data,
            "cmd": cmd,
            "id": str(cmd_id)
        }
        self._logger.info(f"sending command: {cmd}")
        self._logger.debug(f"command data: {data}")
        WSSessionProvider().connection.send(json.dumps(command))
        return cmd_id
    

    def _run_blocking_command(self, cmd:str, data:dict, timeout:int=2) -> None:
        cmd_id = self._send_command(cmd, data)
        start_time = time.time()
        while True:
            if cmd_id not in WSSessionProvider().pending_cmds.keys():
                err_msg = f"cmd_id {cmd_id} not found in pending commands, connection might be lost during command execution"
                self._logger.warning(err_msg)
                raise WebsocketException(err_msg)
            response = WSSessionProvider().pending_cmds[cmd_id]
            if response is not None:
                response = WSSessionProvider().pending_cmds.pop(cmd_id)
                self._logger.info(f"cmd_id {cmd_id} executed successfully")
                return response['data']
            if time.time() - start_time > timeout:
                try:
                    WSSessionProvider().pending_cmds.pop(cmd_id)
                except KeyError:
                    pass
                self._logger.warning(f"cmd_id {cmd_id} timed out")
                raise WebsocketException(f"cmd_id {cmd_id} timed out")
            time.sleep(0.1)
            

    @ws_retry_decorator
    def get_tcp_configs(self):
        cmd = "get_tcp_offset_load_config"
        data = {"userId": "test", "version": "xarm6"}
        response = self._run_blocking_command(cmd, data)
        items = response['tcp_load_offset'].values()
        items = list(filter(lambda x: 'tcp_offset' in x, items))
        items_dict = {}
        for item in items:
            name = item['tcp_offset']['name']
            if isinstance(name, dict):
                name = name['en']
            values = item['tcp_offset']['values']
            values[3:] = list(map(deg2rad, values[3:]))
            values = list(map(lambda x: round(x, 4), values))
            items_dict[name] = TCPOffset(*values)
        return items_dict
    

    @ws_retry_decorator
    def get_base_configs(self):
        cmd = "get_world_offset_config"
        data = {"userId": "test", "version": "xarm6"}
        response = self._run_blocking_command(cmd, data)
        _current_config = BaseOffset(*response['currentConfig'])
        self._logger.info(f"current base config: {_current_config}")
        items = response['configs']
        items_dict = {}
        for item in items:
            name = item['name']
            if isinstance(name, dict):
                name = name['en']
            values = item['values']
            values[3:] = list(map(deg2rad, values[3:]))
            values = list(map(lambda x: round(x, 4), values))
            items_dict[name] = BaseOffset(*values)
        return items_dict
    