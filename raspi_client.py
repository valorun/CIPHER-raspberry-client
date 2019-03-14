import os
import time
import logging
from logging.handlers import RotatingFileHandler
import json
import config
import paho.mqtt.client as Mqtt


class MotionController():
	def __init__(self, client):
		self.client = client
		if not config.DEBUG:
			import wiringpi as wp
			self.wiringpi = wp
			self.wiringpi.wiringPiSetup()
			self.serial = self.wiringpi.serialOpen('/dev/serial0',9600)
	def command(self, direction, speed):
		logging.info('moving '+direction+", "+str(speed))
		if config.DEBUG:
			return
		m1Speed = 0
		m2Speed = 0
		if direction == "forwards":
			m1Speed = speed
			m2Speed = speed
		if direction == "backwards":
			m1Speed = -speed
			m2Speed = -speed
		if direction == "left":
			m2Speed = speed
		if direction == "right":
			m1Speed = speed

		# the speeds used by the control card are between 0 and 2047
		self.wiringpi.serialPuts(self.serial,'M1: '+ str(int(m1Speed * 2047/100)) +'\r\n')
		self.wiringpi.serialPuts(self.serial,'M2: '+ str(int(m2Speed * 2047/100)) +'\r\n')
			

class ServoController():
	def __init__(self, client):
		self.client = client
		if not config.DEBUG:
			import maestro
			self.servo = maestro.Controller()

	def command(self, gpio, position, speed):
		logging.info('servo ' + str(gpio) + ', position ' + str(position) + ', speed ' + str(speed) )
		if config.DEBUG:
			return
		speed = int(speed/100 * 60) #conversion to maestro speed
		self.servo.setSpeed(int(gpio), speed)
		position = int(position/100 * 6000) #conversion to maestro position
		self.servo.setTarget(int(gpio), position)

class RelayController():
	def __init__(self, client):
		self.client = client
		if not config.DEBUG:
			import wiringpi as wp
			self.wiringpi = wp
			self.wiringpi.wiringPiSetupGpio() 

	def activate_relay(self, gpio, state, peers=None):
		logging.info('relay '+str(gpio)+", "+str(state)+", "+str(peers))
		#check if the peers relays aren't activated
		if peers != None and len(peers) != 0:
			for peer in peers:
				if(not config.DEBUG and self.wiringpi.digitalRead(int(peer))==1):
					return

		logging.info('relay ' + str(gpio) + 'ACTIVATED')
		gpio = int(gpio)
		if config.DEBUG:
			self.update_state(gpio)
			return
		if(state=="" ): #in the case where a state is not specified
			state=self.wiringpi.digitalRead(gpio)
			if(state==1):
				state=0
			else:
				state=1
		self.wiringpi.pinMode(gpio,1)
		self.wiringpi.digitalWrite(gpio, state)
		self.update_state([gpio])

	def update_state(self, gpios):
		"""
		Send the state of all specified relays to the server
		"""
		relays_list = []
		logging.info('Updating relays on server')
		for g in gpios:
			gpio = int(g)
			if config.DEBUG:
				state=1
			else:
				state=self.wiringpi.digitalRead(gpio)
			relays_list.append({'gpio':gpio, 'state':state, 'raspi_id':config.RASPBERRY_ID})
		self.client.publish("server/update_relays_state", json.dumps({'relays':relays_list}))

class RaspiController():
	def __init__(self, client):
		self.client = client

	def shutdown(self):
		logging.info('shutdown')
		if config.DEBUG:
			return
		os.system('shutdown -h now')
		
	def reboot(self):
		logging.info('reboot')
		if config.DEBUG:
			return
		os.system('reboot -h now')

mqtt = None

raspi = None
motion = None
relay = None
servo = None

def create_client():
	global mqtt, raspi

	mqtt = Mqtt.Client(config.RASPBERRY_ID)

	raspi = RaspiController(mqtt)

	def on_disconnect(client, userdata, rc):
		"""
		Automatically disable relays and motors on disconnect.
		"""
		global relay, motion
		mqtt.publish("server/raspi_disconnect", json.dumps({'id':config.RASPBERRY_ID}))
		if(motion != None):
			motion.command(0, 0)
		if(relay != None):
			for gpio in range(2, 27):
				relay.activate_relay(gpio, 0)
		logging.info('Disconnected from server')

	def on_connect(client, userdata, flags, rc):
		"""
		Function called when the client connect to the server.
		"""
		logging.info("Connected with result code "+str(rc))
		notify_server_connection()
		mqtt.subscribe("server/connect")
		mqtt.subscribe("raspi/shutdown")
		mqtt.subscribe("raspi/reboot")
		mqtt.subscribe("raspi/"+config.RASPBERRY_ID+"/#")

	def notify_server_connection():
		"""
		Give all information about the connected raspberry to the server when needed.
		"""
		mqtt.publish("server/raspi_connect", json.dumps({'id':config.RASPBERRY_ID}))

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
		if topic == "raspi/shutdown":
			raspi.shutdown()
		elif topic == "raspi/reboot":
			raspi.reboot()
		elif topic == "raspi/"+config.RASPBERRY_ID+"/motion":
			if motion == None:
				motion = MotionController(mqtt) 
			motion.command(data['direction'], data['speed'])
		elif topic == "raspi/"+config.RASPBERRY_ID+"/servo":
			if servo == None:
				servo = ServoController(mqtt)
			servo.command(data['gpio'], data['position'], data['speed'])
		elif topic == "raspi/"+config.RASPBERRY_ID+"/relay/activate":
			if relay == None:
				relay = RelayController(mqtt)
			relay.activate_relay(data['gpio'], data['state'], data['peers'])
		elif topic == "raspi/"+config.RASPBERRY_ID+"/relay/update_state":
			if relay == None:
				relay = RelayController(mqtt)
			relay.update_state(data['gpios'])
		elif topic == "server/connect": #when the server start or restart, notify this raspberry is connected
			notify_server_connection()
		logging.info(topic+" "+str(data))
	
	mqtt.on_connect = on_connect
	mqtt.on_message = on_message
	mqtt.on_disconnect = on_disconnect
	mqtt.enable_logger()
	mqtt.will_set("server/raspi_disconnect", json.dumps({'id':config.RASPBERRY_ID}))

	mqtt.connect(config.MQTT_BROKER_URL, config.MQTT_BROKER_PORT, 60)

	return mqtt

def setup_logger():
	if config.DEBUG:
		log_level = 'DEBUG'
	else:
		log_level = 'INFO'
	file_handler = RotatingFileHandler(os.path.join(os.path.dirname(__file__),"app.log"), maxBytes=1024)
	formatter = logging.Formatter("%(asctime)s -- %(name)s -- %(levelname)s -- %(message)s")
	file_handler.setFormatter(formatter)
	root_logger=logging.getLogger()
	root_logger.addHandler(file_handler)
	root_logger.setLevel(log_level)
	
	