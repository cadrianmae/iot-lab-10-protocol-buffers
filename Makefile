# Lab 10: Protocol Buffers - Makefile
# Author: Mae Capacite (C21348423)

PROTO_FILE = sensor.proto
PLUGIN = ./uprotobuf_plugin.py

# Pico deployment settings
# Usage: make deploy-pico PICO=/dev/ttyACM0
PICO ?= auto
PICO_FILES = main.py uprotobuf.py sensor_upb2.py umqtt_simple.py umqtt_robust.py

.PHONY: all proto clean deploy-pico list-picos run-pico

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

# List connected Picos
list-picos:
	mpremote connect list

# Deploy files to Pico
# Usage: make deploy-pico [PICO=/dev/ttyACM0]
deploy-pico: proto
ifeq ($(PICO),auto)
	@echo "Deploying to auto-detected Pico..."
	mpremote cp $(PICO_FILES) :
else
	@echo "Deploying to $(PICO)..."
	mpremote connect $(PICO) cp $(PICO_FILES) :
endif
	@echo "Deployed: $(PICO_FILES)"

# Run main.py on Pico (without copying)
# Usage: make run-pico [PICO=/dev/ttyACM0]
run-pico:
ifeq ($(PICO),auto)
	mpremote run main.py
else
	mpremote connect $(PICO) run main.py
endif

# Deploy and run
# Usage: make deploy-run [PICO=/dev/ttyACM0]
deploy-run: deploy-pico run-pico
