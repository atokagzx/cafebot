#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='cafebot_proto',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'grpcio',
        'grpcio-tools',
    ]
)
