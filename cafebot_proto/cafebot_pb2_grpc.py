# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import cafebot_pb2 as cafebot__pb2


class MovementsStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.park = channel.unary_unary(
                '/robot.Movements/park',
                request_serializer=cafebot__pb2.Empty.SerializeToString,
                response_deserializer=cafebot__pb2.SimpleResponse.FromString,
                )


class MovementsServicer(object):
    """Missing associated documentation comment in .proto file."""

    def park(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_MovementsServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'park': grpc.unary_unary_rpc_method_handler(
                    servicer.park,
                    request_deserializer=cafebot__pb2.Empty.FromString,
                    response_serializer=cafebot__pb2.SimpleResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'robot.Movements', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class Movements(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def park(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/robot.Movements/park',
            cafebot__pb2.Empty.SerializeToString,
            cafebot__pb2.SimpleResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)