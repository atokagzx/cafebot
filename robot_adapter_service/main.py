#! /usr/bin/env python3
import sys, os
import logging
import argparse
import grpc
from concurrent import futures
from cafebot_proto import pb2_grpc, pb2
from modules.robot_adapter import RobotAdapter, RobotException


class MovementsServicer(pb2_grpc.MovementsServicer):
    def __init__(self):
        self._logger = logging.getLogger("movements_servicer")


    def park(self, request, context):
        self._logger.info("parking robot")
        try:
            RobotAdapter().park()
        except RobotException as e:
            self._logger.error(f"failed to park: {e}")
            return pb2.SimpleResponse(success=False, message=str(e))
        else:
            return pb2.SimpleResponse(success=True, message="ok")
    

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--address", type=str, default="[::]:50051")
    args = parser.parse_args()
    movements_servicer = MovementsServicer()
    RobotAdapter()
    grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    pb2_grpc.add_MovementsServicer_to_server(movements_servicer, grpc_server)
    logging.info(f"starting gRPC server on {args.address}")
    grpc_server.add_insecure_port(args.address)
    grpc_server.start()
    try:
        grpc_server.wait_for_termination()
    except KeyboardInterrupt:
        logging.info("stopping gRPC server")
        grpc_server.stop(0)
        sys.exit(0)
