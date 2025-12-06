# Lab 10: Protocol Buffers - Makefile
# Author: Mae Capacite (C21348423)

PROTO_FILE = sensor.proto
PLUGIN = ./uprotobuf_plugin.py

.PHONY: all proto clean

all: proto

# Compile proto schema for MicroPython
proto: $(PROTO_FILE)
	chmod +x $(PLUGIN)
	protoc --plugin=protoc-gen-custom=$(PLUGIN) --custom_out=. $(PROTO_FILE)
	@echo "Generated sensor_upb2.py"

# Clean generated files
clean:
	rm -f *_upb2.py *_pb2.py
	@echo "Cleaned generated files"
