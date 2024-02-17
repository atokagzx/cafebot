class RobotException(Exception):
    pass


class WrongModeException(RobotException):
    pass


class WebsocketException(RobotException):
    pass


class ConfigException(RobotException):
    pass