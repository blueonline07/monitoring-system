#!/bin/bash
# Wrapper script to run Python with correct protobuf implementation for etcd3 compatibility

export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# Activate venv and run command
source venv/bin/activate
exec "$@"
