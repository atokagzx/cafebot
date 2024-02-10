SHELL=/bin/bash
ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
PROTO_DIR:=$(ROOT_DIR)/cafebot_proto

all: requirements install

requirements:
	pip install --no-cache-dir submodules/xArm-Python-SDK
	pip install -r $(ROOT_DIR)/requirements.txt

proto:
	python -m grpc_tools.protoc --proto_path=$(PROTO_DIR) --python_out=$(PROTO_DIR) --grpc_python_out=$(PROTO_DIR) $(PROTO_DIR)/*.proto

install: proto
	pip install --no-cache-dir $(ROOT_DIR)

uninstall:
	pip uninstall cafebot_proto -y
	