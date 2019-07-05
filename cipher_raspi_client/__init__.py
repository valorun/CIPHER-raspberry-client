import json
import os
import logging
import paho.mqtt.client as Mqtt
from logging.handlers import RotatingFileHandler
from .constants import *
from .raspi_client import RaspiController, ServoController, RelayController, MotionController

mqtt = None

raspi = None
motion = None
relay = None
servo = None

def create_client(debug=False):
	global mqtt, raspi

	mqtt = Mqtt.Client(RASPBERRY_ID)

	raspi = RaspiController(mqtt, debug)

	def on_disconnect(client, userdata, rc):
		"""
		Automatically disable relays and motors on disconnect.
		"""
		global relay, motion
		mqtt.publish('server/raspi_disconnect', json.dumps({'id':RASPBERRY_ID}))
		if motion is not None:
			motion.command(0, 0)
		if relay is not None:
			for gpio in range(2, 27):
				relay.activate_relay(gpio, 0)
		logging.info("Disconnected from server")

	def on_connect(client, userdata, flags, rc):
		"""
		Function called when the client connect to the server.
		"""
		logging.info("Connected with result code " + str(rc))
		notify_server_connection()
		mqtt.subscribe('server/connect')
		mqtt.subscribe('raspi/shutdown')
		mqtt.subscribe('raspi/reboot')
		mqtt.subscribe('raspi/' + RASPBERRY_ID + '/#')

	def notify_server_connection():
		"""
		Give all information about the connected raspberry to the server when needed.
		"""
		mqtt.publish('server/raspi_connect', json.dumps({'id':RASPBERRY_ID}))

	def on_message(client, userdata, msg):
		"""
		Function called when a message is received from the server.
		"""
		global motion, relay, servo
		topic = msg.topic
		try:
			data = json.loads(msg.payload.decode('utf-8'))
		except ValueError:
			data = msg.payload.decode('utf-8')
		if topic == 'raspi/shutdown':
			raspi.shutdown()
		elif topic == 'raspi/reboot':
			raspi.reboot()
		elif topic == 'raspi/' + RASPBERRY_ID + '/motion':
			if motion is None:
				motion = MotionController(mqtt, debug) 
			motion.command(data['direction'], data['speed'])
		elif topic == 'raspi/' + RASPBERRY_ID + '/servo/set_position':
			if servo is None:
				servo = ServoController(mqtt, debug)
			servo.set_position(data['gpio'], data['position'], data['speed'])
		elif topic == 'raspi/' + RASPBERRY_ID + '/servo/sequence': #COMPATIBILITY REASON
			if servo is None:
				servo = ServoController(mqtt, debug)
			servo.sequence(data['index'])
		elif topic == 'raspi/' + RASPBERRY_ID + '/relay/activate':
			if relay is None:
				relay = RelayController(mqtt, debug)
			relay.activate_relay(data['gpio'], data['state'], data['peers'])
		elif topic == 'raspi/' + RASPBERRY_ID + '/relay/update_state':
			if relay is None:
				relay = RelayController(mqtt, debug)
			relay.update_state(data['gpios'])
		elif topic == 'server/connect': #when the server start or restart, notify this raspberry is connected
			notify_server_connection()
		elif topic == 'raspi/' + RASPBERRY_ID + '/command':
			os.system(data['command'])
		logging.info(topic + " " + str(data))
	
	mqtt.on_connect = on_connect
	mqtt.on_message = on_message
	mqtt.on_disconnect = on_disconnect
	mqtt.enable_logger()
	mqtt.will_set('server/raspi_disconnect', json.dumps({'id':RASPBERRY_ID}))

	mqtt.connect(MQTT_BROKER_URL, MQTT_BROKER_PORT, 60)

	return mqtt

def setup_logger(debug=False):
	if debug:
		log_level = 'DEBUG'
	else:
		log_level = 'INFO'
	file_handler = RotatingFileHandler(os.path.join(os.path.dirname(__file__),'app.log'), maxBytes=1024)
	formatter = logging.Formatter("%(asctime)s -- %(name)s -- %(levelname)s -- %(message)s")
	file_handler.setFormatter(formatter)
	root_logger=logging.getLogger()
	root_logger.addHandler(file_handler)
	root_logger.setLevel(log_level)
	
	
