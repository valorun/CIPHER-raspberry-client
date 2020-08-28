import json
import os
import logging
import paho.mqtt.client as Mqtt
from logging.handlers import RotatingFileHandler
from logging.config import dictConfig
from .config import client_config
from .raspi_client import RaspiController, ServoController, RelayController, MotionController

mqtt = None

raspi = None
motion = None
relay = None
servo = None

def create_client(debug=False):
	global mqtt, raspi

	mqtt = Mqtt.Client(client_config.RASPBERRY_ID)

	raspi = RaspiController(mqtt, debug)

	def on_disconnect(client, userdata, rc):
		"""
		Automatically disable relays and motors on disconnect.
		"""
		global relay, motion
		mqtt.publish('server/raspi_disconnect', json.dumps({'id':client_config.RASPBERRY_ID}))
		if motion is not None:
			motion.command('stop', 0)
		if relay is not None:
			relay.stop()

		logging.info("Disconnected from server")

	def on_connect(client, userdata, flags, rc):
		"""
		Function called when the client connect to the server.
		"""
		logging.info("Connected with result code " + str(rc))
		client.subscribe('server/connect')
		client.subscribe('raspi/shutdown')
		client.subscribe('raspi/reboot')
		client.subscribe('client/' + client_config.RASPBERRY_ID + '/#')
		notify_server_connection()


	def notify_server_connection():
		"""
		Give all information about the connected raspberry to the server when needed.
		"""
		mqtt.publish('client/connect', json.dumps({'id':client_config.RASPBERRY_ID, 'icon':client_config.ICON}))

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
		elif topic == 'client/' + client_config.RASPBERRY_ID + '/motion':
			if motion is None:
				motion = MotionController(mqtt, debug) 
			motion.command(data['direction'], data['speed'])
		elif topic == 'client/' + client_config.RASPBERRY_ID + '/servo/set_position':
			if servo is None:
				servo = ServoController(mqtt, debug)
			servo.set_position(data['gpio'], data['position'], data['speed'])
		elif topic == 'client/' + client_config.RASPBERRY_ID + '/servo/get_position':
			if servo is None:
				servo = ServoController(mqtt, debug)
			servo.get_position(data['gpio']) # SET LES RANGES AU LANCEMENT DE CIPHER, ET RENVOYER LES RESULTS
		elif topic == 'client/' + client_config.RASPBERRY_ID + '/servo/sequence': #COMPATIBILITY REASON
			if servo is None:
				servo = ServoController(mqtt, debug)
			servo.sequence(data['index'])
		elif topic == 'client/' + client_config.RASPBERRY_ID + '/relay/activate':
			if relay is None:
				relay = RelayController(mqtt, debug)
			relay.activate_relay(data['gpio'], data['state'])
		elif topic == 'client/' + client_config.RASPBERRY_ID + '/relay/update_state':
			if relay is None:
				relay = RelayController(mqtt, debug)
			relay.update_state(data['gpios'])
		elif topic == 'server/connect': #when the server start or restart, notify this raspberry is connected
			notify_server_connection()
		elif topic == 'client/' + client_config.RASPBERRY_ID + '/command':
			os.system(data['command'])			
		elif topic == 'client/' + client_config.RASPBERRY_ID + '/exit':
			exit(0)
		logging.info(topic + " " + str(data))
	
	mqtt.on_connect = on_connect
	mqtt.on_message = on_message
	mqtt.on_disconnect = on_disconnect
	#mqtt.enable_logger()
	mqtt.will_set('server/client_disconnect', json.dumps({'id':client_config.RASPBERRY_ID}))

	mqtt.connect(client_config.MQTT_BROKER_URL, client_config.MQTT_BROKER_PORT, 60)

	return mqtt

def setup_logger(debug=False):
	if debug:
		log_level = 'DEBUG'
	else:
		log_level = 'INFO'
	
	dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': '%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(name)s: %(message)s',
        }},
        'handlers': { 
            'default': { 
                'formatter': 'default',
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',  # Default is stderr
            },
            'file': { 
                'formatter': 'default',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': client_config.LOG_FILE,
                'maxBytes': 1024
            }
        },

        'root': {
            'level': log_level,
            'handlers': ['default', 'file']
        },
    })
	
	
