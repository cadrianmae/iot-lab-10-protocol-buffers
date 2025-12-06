"""
Lab 10: Protocol Buffers - main.py
Unified MQTT Publisher/Subscriber
Single codebase that runs as either publisher or subscriber based on global config.
Uses Protocol Buffers (proto2) for efficient binary message serialization.
Author: Mae Capacite
Date: 06 / 12 / 2025
"""
import machine, time, network
import sensor_upb2 as pb

# ==== Global Configuration ====

WOKWI_SIM = True
WOKWI_LOCALHOST = "host.wokwi.internal"  # wokwigw hostname for localhost

BROKER_IP = "" if not WOKWI_SIM else WOKWI_LOCALHOST # MQTT broker IP
TOPIC = b"temp/pico"

# Mode detection: Set one to None to auto-detect mode
# OUTPUT_PIN = None -> Publisher mode
# PUB_IDENT = None -> Subscriber mode

# Publisher
OUTPUT_PIN = None
PUB_IDENT = b"pico01"

# Subscriber
# OUTPUT_PIN = 14
# PUB_IDENT = None

class Logger:
    """Simple logger with per-instance names and global log level."""
    DEBUG, INFO, WARN, ERROR = 0, 1, 2, 3
    _level = 0  # DEBUG
    _level_names = ["DEBUG", "INFO", "WARN", "ERROR"]

    def __init__(self, name: str = "main"):
        self.name = name

    @classmethod
    def set_level(cls, level: int):
        """Set global log level for all loggers."""
        cls._level = level

    def _log(self, level: int, msg: str):
        if level >= Logger._level:
            print(f"[{Logger._level_names[level]}] [{self.name}] {msg}")

    def debug(self, msg: str):
        self._log(Logger.DEBUG, msg)

    def info(self, msg: str):
        self._log(Logger.INFO, msg)

    def warn(self, msg: str):
        self._log(Logger.WARN, msg)

    def error(self, msg: str):
        self._log(Logger.ERROR, msg)

# Global logger for module-level functions
log = Logger("main")

# Local umqtt library (flattened for Wokwi)
if 'umqtt' not in globals():
    if WOKWI_SIM:
        log.info("In Wokwi simulation - using umqtt_robust")
        import umqtt_robust as umqtt
    else:
        try:
            import umqtt.robust as umqtt
        except ImportError:
            log.info("umqtt.robust not found, installing via mip")
            import mip
            mip.install("umqtt.simple")
            mip.install("umqtt.robust")
            import umqtt.robust as umqtt

class System:
    """Singleton System class for common functionality."""

    def __init__(self):
        self.sensor = machine.ADC(4)  # Internal temperature sensor
        self.rtc = machine.RTC()
        self.wifi = network.WLAN(network.STA_IF)
        self.log = Logger(self.__class__.__name__)

    def set_wifi(self, ssid, password):
        """Set WiFi credentials."""
        self.wifi_ssid = ssid
        self.wifi_password = password

    def connect_wifi(self, max_retry=3):
        """Connect or reconnect to WiFi network."""
        wifi = self.wifi
        self.log.info(f"Connecting to WiFi SSID: {self.wifi_ssid}")
        wifi.active(True)

        retry_count = 0

        while True:
            wifi.connect(self.wifi_ssid, self.wifi_password)

            if wifi.isconnected():
                break

            retry_count += 1
            self.log.warn(f"WiFi connection failed. Retry {retry_count}/{max_retry}")

            if retry_count >= max_retry:
                self.log.error("Max WiFi connection retries reached. Giving up.")
                return False

            time.sleep(retry_count * 2)  # Exponential backoff

        ip = wifi.ifconfig()[0]
        self.log.info(f"Connected to WiFi. IP address: {ip}")

        return True

    def is_wifi_connected(self):
        """Check if WiFi is connected."""
        return self.wifi.isconnected()

    def disconnect_wifi(self):
        """Disconnect from WiFi network."""
        if not self.is_wifi_connected():
            return

        self.wifi.disconnect()
        self.log.info("Disconnected from WiFi")

    def get_current_time(self):
        """Get current time from RTC."""
        return self.rtc.datetime()

    def get_timestamp(self):
        """Get current timestamp in seconds since epoch."""
        return time.time()

    def read_temp(self):
        """Read temperature from the internal sensor. Returns temperature in Celsius."""
        if WOKWI_SIM:
            import random
            return 20 + random.uniform(-5, 10)  # Fake: 15-30C range

        reading = self.sensor.read_u16()
        voltage = reading * 3.3 / 65535
        temperature_c = 27 - (voltage - 0.706) / 0.001721
        return temperature_c

class PiMQTT:
    """Base MQTT class for common functionality."""
    umqtt  = None

    def __init__(self, system: System) -> None:
        self.system = system
        self.log = Logger(self.__class__.__name__)
        self.client_id = None
        self.broker_ip = None
        self.mqtt_port = None
        self.topic = None
        self.mqtt = None

    def set_config(self, client_id: bytes, broker_ip: str, port: int, topic: bytes):
        """Set MQTT configuration."""
        self.client_id = client_id
        self.broker_ip = broker_ip
        self.mqtt_port = port
        self.topic = topic
        self.log.debug(f"Config set: {client_id.decode()}@{broker_ip}:{port} topic={topic.decode()}")

    def set_callbacks(self):
        """Set MQTT callbacks"""
        raise NotImplementedError("Subclasses should implement this method.")

    def run(self):
        """Run the MQTT client."""
        self.log.info("Starting MQTT client...")
        assert self.client_id is not None, "Client ID not set."
        assert self.topic is not None, "MQTT topic not set."
        self._connect_mqtt(self.client_id)

        try:
            self._run()
        except Exception as e:
            self.log.error(f"MQTT operation failed: {e}")
        finally:
            self._cleanup()

    def _run(self):
        """Internal run method."""
        raise NotImplementedError("Subclasses should implement this method.")

    def _connect_mqtt(self, client_id: bytes):
        """Connect to the MQTT broker."""
        assert self.broker_ip is not None, "Broker IP not set."
        assert self.mqtt_port is not None, "MQTT port not set."

        self.log.debug(f"Connecting to {self.broker_ip}:{self.mqtt_port}")
        self.mqtt = umqtt.MQTTClient(
            client_id=client_id,
            server=self.broker_ip,
            port=self.mqtt_port,
        )

        try:
            self.mqtt.connect()
            self.log.info(f"Connected to {self.broker_ip}:{self.mqtt_port} as {client_id.decode()}")
        except Exception as e:
            self.log.error(f"Failed to connect: {e}")
            self.mqtt = None

    def _cleanup(self):
        """Cleanup resources."""

        if self.mqtt is None: return

        self.mqtt.disconnect()
        self.log.info("Disconnected from broker")
    

class PiMQTTPub(PiMQTT):
    """MQTT Publisher class."""

    def __init__(self, system: System) -> None:
        super().__init__(system)

    def set_config(self, client_id: bytes, broker_ip: str, port: int, topic: bytes, publish_interval: int=10):
        """Set MQTT configuration for publisher."""
        super().set_config(client_id, broker_ip, port, topic)
        self.publish_interval = publish_interval

    def set_callbacks(self, on_get_data=None, on_set_data=None):
        """Set MQTT callbacks for publisher."""
        self.on_get_data = on_get_data
        self.on_set_data = on_set_data
        self.log.debug("Callbacks configured")

    def _run(self):
        """Internal run method for publisher."""
        assert self.publish_interval is not None, "Publish interval not set."
        assert self.on_get_data is not None, "on_get_data callback not set."
        assert self.mqtt is not None, "MQTT client not connected."
        assert self.topic is not None, "MQTT topic not set."

        try:
            while True:
                if self.on_get_data:
                    payload = self.on_get_data()
                else:
                    self.log.warn("No data callback set")
                    continue

                # Protobuf returns bytes directly, no encode needed
                self.mqtt.publish(self.topic, payload)
                self.log.debug(f"Published {len(payload)} bytes to {self.topic.decode()}")
                time.sleep(self.publish_interval)
        except KeyboardInterrupt:
            self.log.info("Publisher interrupted by user")
        except Exception as e:
            self.log.error(f"Publisher loop error: {e}")

class PiMQTTSub(PiMQTT):
    """MQTT Subscriber class."""

    def __init__(self, system: System) -> None:
        super().__init__(system)
        self.on_message = None

    def set_callbacks(self, on_message=None):
        """Set MQTT callbacks for subscriber mode."""
        self.on_message = on_message
        self.log.debug("Message callback configured")

    def _run(self):
        """Internal run method for subscriber."""
        assert self.mqtt is not None, "MQTT client not connected."
        assert self.on_message is not None, "on_message callback not set."
        assert self.topic is not None, "MQTT topic not set."

        self.mqtt.set_callback(self.on_message)
        self.mqtt.subscribe(self.topic)
        self.log.info(f"Subscribed to {self.topic.decode()}")

        try:
            while True:
                self.mqtt.wait_msg()
        except KeyboardInterrupt:
            self.log.info("Subscriber interrupted by user")

def publisher_loop(system: System):
    """Run device in publisher mode - read temp and publish to MQTT."""
    publisher = PiMQTTPub(system)
    publisher.set_config(PUB_IDENT, BROKER_IP, 1883, TOPIC, publish_interval=10)

    def on_get_data():
        """Get data to publish - temperature and time as protobuf."""
        temp = system.read_temp()
        current_time = system.get_current_time()  # (year, month, day, weekday, hour, min, sec, subsec)

        time_msg = pb.TimeMessage()
        time_msg.hour.setValue(current_time[4])
        time_msg.minute.setValue(current_time[5])
        time_msg.second.setValue(current_time[6])

        sensor_msg = pb.SensorreadingMessage()
        sensor_msg.publisher_id.setValue(PUB_IDENT)
        sensor_msg.temperature.setValue(temp)
        sensor_msg.time.setValue(time_msg)

        return sensor_msg.serialize()

    publisher.set_callbacks(on_get_data=on_get_data)

    publisher.run()

def subscriber_loop(system: System):
    """Run device in subscriber mode - subscribe to MQTT topic and process messages."""

    led = machine.Pin(OUTPUT_PIN, machine.Pin.OUT)
    subscriber = PiMQTTSub(system)
    subscriber.set_config(b"pico_subscriber", BROKER_IP, 1883, TOPIC)



    def process_message(topic, msg):
        """Process incoming MQTT message (protobuf)."""
        topic_str = topic.decode()

        sensor_msg = pb.SensorreadingMessage()
        sensor_msg.parse(msg)

        pub_ident = sensor_msg.publisher_id._value
        temp = sensor_msg.temperature._value
        time_msg = sensor_msg.time._value  # Nested TimeMessage
        hour = time_msg.hour._value
        minute = time_msg.minute._value
        second = time_msg.second._value

        # For simplicity, use current system timestamp
        timestamp = system.get_timestamp()

        log.debug(f"Received message on {topic_str}: pub_id={pub_ident.decode()}, temp={temp:.2f}C, time={hour}:{minute}:{second}")
        return (pub_ident, temp, timestamp, hour, minute, second)

    window_size = 10 * 60  # 10 minutes in seconds 

    # map of data from devices - stores messages in last 10 mins
    # pub_ident -> list of (timestamp, temp, hour, minute, second)
    data = {}
        
    def save_data(data_tuple):
        """Save processed data and maintain sliding window."""
        if data_tuple is None:
            log.warn("No data to save")
            return

        pub_ident, temp, timestamp, hour, minute, second = data_tuple

        try:
            message_time = int(timestamp)
        except ValueError:
            log.error("Invalid timestamp format")
            return

        # Create entry if not exists
        if pub_ident not in data:
            data[pub_ident] = []

        # Save new data point with RTC time
        data[pub_ident].append((message_time, temp, hour, minute, second))

        log.debug(f"Data for {pub_ident}: {data[pub_ident]}")

    def clean_up_data():
        """Clean up old data points outside the sliding window."""
        current_time = system.get_timestamp()

        for pub_ident in data:
            old_len = len(data[pub_ident])
            data[pub_ident] = [entry for entry in data[pub_ident]
                               if current_time - entry[0] <= window_size]
            removed = old_len - len(data[pub_ident])
            if removed > 0:
                log.debug(f"Removed {removed} old data points for {pub_ident}")

    def calc_avg_temp_last_10min():
        """Calculate average of LATEST temperature from each active publisher."""
        current_time = system.get_timestamp()
        latest_temps = []

        for pub_ident, data_points in data.items():
            if not data_points:
                continue
            # Get most recent reading for this publisher
            # Format: (timestamp, temp, hour, minute, second)
            latest_entry = data_points[-1]
            latest_ts, latest_temp = latest_entry[0], latest_entry[1]
            # Only include if within window
            if current_time - latest_ts <= window_size:
                latest_temps.append(latest_temp)
                log.debug(f"Latest from {pub_ident}: {latest_temp:.2f}C at {latest_entry[2]:02d}:{latest_entry[3]:02d}:{latest_entry[4]:02d}")

        if not latest_temps:
            log.info("No active publishers in the last 10 minutes")
            return None

        avg_temp = sum(latest_temps) / len(latest_temps)
        log.info(f"Average temp ({len(latest_temps)} publishers): {avg_temp:.2f}C")

        return avg_temp


    def on_message(topic, msg):
        """Process incoming MQTT messages."""

        msg_data = process_message(topic, msg)

        save_data(msg_data)
        clean_up_data()
        avg_temp = calc_avg_temp_last_10min()

        # Control LED based on average temperature
        if avg_temp is not None:
            if avg_temp > 25:
                led.on()
                log.info("LED ON (avg > 25C)")
            else:
                led.off()
                log.info("LED OFF (avg <= 25C)")

        log.debug(f"Current data store: {data}")

    subscriber.set_callbacks(on_message=on_message)

    subscriber.run()

def main():
    """Main function to run as publisher or subscriber based on configuration."""

    # Initialize system
    system = System()
    system.set_wifi("Wokwi-GUEST", "")
    system.connect_wifi()

    # Auto mode detection based on global variables
    if OUTPUT_PIN is None and PUB_IDENT is not None:
        log.info("Auto-detected: PUBLISHER mode (OUTPUT_PIN is None)")
        publisher_loop(system)
    elif PUB_IDENT is None and OUTPUT_PIN is not None:
        log.info("Auto-detected: SUBSCRIBER mode (PUB_IDENT is None)")
        subscriber_loop(system)
    else:
        log.error("Invalid config: Set OUTPUT_PIN=None for publisher, PUB_IDENT=None for subscriber")


if __name__ == "__main__":
    main()


