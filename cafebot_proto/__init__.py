import os
import sys
_current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(_current_dir)
import cafebot_pb2_grpc as pb2_grpc
import cafebot_pb2 as pb2
sys.path.remove(_current_dir)
del _current_dir
del os
del sys