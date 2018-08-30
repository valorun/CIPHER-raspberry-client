#!/usr/bin/python
# coding: utf-8

import os
import time
from enum import Enum
from socketIO_client import SocketIO, BaseNamespace, LoggingNamespace
import logging
import json
import config


class MotionNamespace(BaseNamespace):
	def on_command(self, *args):
		print('motion', args)
		if config.DEBUG:
			return
		m1Speed = args[0].split(",")[0]
		m2Speed = args[0].split(",")[1]
		wiringpi.serialPuts(serial,'M1: '+ m1Speed +'\r\n')
		wiringpi.serialPuts(serial,'M2: '+ m2Speed +'\r\n')
	def on_stop(self, *args):
		if config.DEBUG:
			return
		wiringpi.serialPuts(serial,'M1: 0\r\n')
		wiringpi.serialPuts(serial,'M2: 0\r\n')

class ServoNamespace(BaseNamespace):
	def on_command(self, *args):
		print('servo', args)
		if config.DEBUG:
			return
		servo.runScriptSub(int(args[0]))

class RelayNamespace(BaseNamespace):
	def on_activate_relay(self, *args):
		print('relay', args)
		gpio=int(args[0])
		state=args[1]
		raspi_id=args[2]
		
		if raspi_id != config.RASPBERRY_ID: #on vérifie que la requete est bien destinée à ce raspberry
			return
		print('relay ACTIVATED')
		if config.DEBUG:
			self.on_update_state(args[0])
			return
		if(state=="" ): #dans le cas ou un etat n'est pas specifie
			state=wiringpi.digitalRead(gpio)
			if(state==1):
				state=0
			else:
				state=1
		wiringpi.pinMode(gpio,1)
		wiringpi.digitalWrite(gpio,int(state))
		self.on_update_state(args[0])

	#lorsque qu'il s'agit d'un relai appairé
	def on_activate_paired_relay(self, *args):
		print('relay', args)
		if config.DEBUG:
			self.on_update_state(args[0])
			return
		gpio=int(args[0])
		state=args[1]
		peers=args[2]
		raspi_id=args[3]
		if raspi_id != config.RASPBERRY_ID:
			return

		for peer in peers:
			if(not config.DEBUG and wiringpi.digitalRead(int(peer))==1):
				return
		self.on_activate_relay(args[0], args[1])

	def on_update_state(self, *args):
		gpio=args[0]
		if config.DEBUG:
			state=1
		else:
			state=wiringpi.digitalRead(int(gpio))
		self.emit('update_state_for_client', gpio, state, config.RASPBERRY_ID)

class RaspiNamespace(BaseNamespace):
	def on_shutdown(self, *args):
		print('shutdown', args)
		if config.DEBUG:
			return
		os.system('shutdown -h now')
		
	def on_reboot(self, *args):
		print('reboot', args)
		if config.DEBUG:
			return
		os.system('reboot -h now')
		
	def on_connect(self):
		self.emit('raspi_connect', config.RASPBERRY_ID, config.RELAY_MODE, config.MOTION_MODE, config.SERVO_MODE)
		
	def on_reconnect(self):
		self.emit('raspi_connect', config.RASPBERRY_ID, config.RELAY_MODE, config.MOTION_MODE, config.SERVO_MODE)
	

#arret automatique des relais et des moteurs en cas de deconnexion
def on_disconnect():
	print('Disconnected from server')
	raspi_namespace.emit('disconnect')
	if config.DEBUG:
		return
	if(config.MOTION_MODE):
		wiringpi.serialPuts(serial,'M1: 0\r\n')
		wiringpi.serialPuts(serial,'M2: 0\r\n')
	if(config.RELAY_MODE):
		for gpio in range(2, 27):
			wiringpi.digitalWrite(gpio,0)



#if config.DEBUG:
logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
logging.basicConfig()

socketIO = SocketIO(config.SERVER_ADDRESS, config.SERVER_PORT, LoggingNamespace, verify=False)
#socketIO = SocketIO('http://192.168.1.20', 5000, LoggingNamespace, verify=False)

socketIO.on('disconnect', on_disconnect)


raspi_namespace = socketIO.define(RaspiNamespace, '/raspi')


if(config.MOTION_MODE):
	motion_namespace = socketIO.define(MotionNamespace, '/motion')
	if not config.DEBUG:
		import wiringpi, sys
		wiringpi.wiringPiSetup()
		serial = wiringpi.serialOpen('/dev/serial0',9600)
if(config.SERVO_MODE):
	servo_namespace = socketIO.define(ServoNamespace, '/servo')
	if not config.DEBUG:
		import maestro
		servo = maestro.Controller()
if(config.RELAY_MODE):
	relay_namespace = socketIO.define(RelayNamespace, '/relay')
	if not config.DEBUG:
		import wiringpi
		wiringpi.wiringPiSetupGpio() 

socketIO.wait()
