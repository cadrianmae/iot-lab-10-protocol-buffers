# Fundamentals of Iot - Lab 10: Protocol Buffers

## Team Members

- Mae Capacite (C21348423)

## Prerequisites

Dev environment:
- protoc (Protocol Buffers compiler)
- Python protobuf library
- Make
- Python 3.12+
- pip
- mpremote
- mosquitto (MQTT broker)
- mosquitto-clients (MQTT client tools)

Raspberry Pi Pico:
- Raspberry Pi Pico W
- MicroPython firmware on the Pico W

Raspberry Pi (host):
- Mosquitto (MQTT broker)

## Setup

1. Clone the repository:
```bash
git clone
cd lab-10-protocol-buffers
```

2. Make proto files:
```bash
make proto
```

3. Run the MQTT broker on the Raspberry Pi:
```bash
mosquitto
```

4. Run publisher and subscriber on the Raspberry Pi Pico:
```bash
make deploy-pico PICO=/dev/ttyACM0  # or appropriate port
```

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make proto` | Compile sensor.proto to sensor_upb2.py |
| `make clean` | Remove generated *_pb2.py files |
| `make list-picos` | List connected Pico devices |
| `make deploy-pico` | Deploy files to auto-detected Pico |
| `make deploy-pico PICO=/dev/ttyACM0` | Deploy to specific Pico |
| `make run-pico` | Run main.py on Pico |
| `make deploy-run` | Deploy and run in one step |

## Configuration

Edit global variables in `main.py`:

**Publisher mode:**
```python
OUTPUT_PIN = None
PUB_IDENT = b"pico01"
```

**Subscriber mode:**
```python
OUTPUT_PIN = 14
PUB_IDENT = None
```
