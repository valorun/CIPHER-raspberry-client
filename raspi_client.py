#!/usr/bin/python
# coding: utf-8

import os
import time
import logging
from logging.handlers import RotatingFileHandler
import json
import config
import paho.mqtt.client as mqtt


class MotionController():
	def __init__(self, client):
		self.client = client
		if not config.DEBUG:
			import wiringpi as wp
			self.wiringpi = wp
			self.wiringpi.wiringPiSetup()
			self.serial = self.wiringpi.serialOpen('/dev/serial0',9600)
	def command(self, m1Speed, m2Speed):
		logging.info('motion '+str(m1Speed)+", "+str(m2Speed))
		if config.DEBUG:
			return
		self.wiringpi.serialPuts(self.serial,'M1: '+ m1Speed +'\r\n')
		self.wiringpi.serialPuts(self.serial,'M2: '+ m2Speed +'\r\n')
			

class ServoController():
	def __init__(self, client):
		self.client = client
		if not config.DEBUG:
			import maestro
			self.servo = maestro.Controller()

	def command(self, index):
		logging.info('servo '+str(index))
		if config.DEBUG:
			return
		self.servo.runScriptSub(index)

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
		if peers != None or len(peers) != 0:
			for peer in peers:
				if(not config.DEBUG and self.wiringpi.digitalRead(int(peer))==1):
					return

		logging.info('relay ACTIVATED')
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
		self.wiringpi.digitalWrite(gpio, gpio)
		self.update_state(gpio)

	def update_state(self, gpio):
		if config.DEBUG:
			state=1
		else:
			state=self.wiringpi.digitalRead(gpio)
		self.client.publish("server/update_relay", {'gpio':gpio, 'state':state})
		#self.emit('update_state_for_client', gpio, state, config.RASPBERRY_ID)

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

def create_client():

	client = mqtt.Client(config.RASPBERRY_ID)

	if config.DEBUG:
		client.on_log = on_log

	raspi = RaspiController(client)
	motion = None
	relay = None
	servo = None

	def on_disconnect():
		"""
		Automatically disable relays and motors on disconnect.
		"""
		client.publish("server/raspi_disconnect", {'id':config.RASPBERRY_ID})
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
		print("Connected with result code "+str(rc))
		client.publish("server/raspi_connect", {'id':config.RASPBERRY_ID, 'address':config.SERVER_ADDRESS})
		client.subscribe("raspi")
		client.subscribe("raspi/"+config.RASPBERRY_ID+"/#")

	def on_message(client, userdata, msg):
		"""
		Function called when a message is received from the server.
		"""
		topic = msg.topic
		data = msg.payload
		if topic == "raspi/shutdown":
			raspi.shutdown()
		elif topic == "raspi/reboot":
			raspi.reboot()
		elif topic == "raspi/"+config.RASPBERRY_ID+"/motion":
			if motion == None:
				motion = MotionController(client) 
			motion.command(data['m1'], data['m2'])
		elif topic == "raspi/"+config.RASPBERRY_ID+"/servo":
			if servo == None:
				servo = ServoController(client)
			servo.command(data['index'])
		elif topic == "raspi/"+config.RASPBERRY_ID+"/relay/activate":
			if relay == None:
				relay = RelayController(client)
			relay.activate_relay(data['gpio'], data['state'], data['peers'])
		elif topic == "raspi/"+config.RASPBERRY_ID+"/relay/update_state":
			if relay == None:
				relay = RelayController(client)
			relay.update_state(data['gpio'])
		print(topic+" "+str(data))

	def on_log(mqttc, obj, level, string):
		print(string)
	
	client.on_connect = on_connect
	client.on_message = on_message
	client.on_disconnect = on_disconnect

	client.connect(config.SERVER_ADDRESS, config.SERVER_PORT, 60)

	return client

def setup_logger():
	file_handler = RotatingFileHandler(os.path.join(os.path.dirname(__file__),"app.log"), maxBytes=1000)
	formatter = logging.Formatter("%(asctime)s -- %(name)s -- %(levelname)s -- %(message)s")
	file_handler.setFormatter(formatter)
	root_logger=logging.getLogger()
	root_logger.addHandler(file_handler)
	root_logger.setLevel(logging.DEBUG)