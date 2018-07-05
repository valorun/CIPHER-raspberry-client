#!/usr/bin/python
# coding: utf-8

import os
import time
from enum import Enum
from socketIO_client import SocketIO, BaseNamespace, LoggingNamespace
import logging

class ActionType(Enum): # differents types d'actions pris en charge par les rasperries
	MOTION=1
	SERVO=2
	RELAY=3

debug=False
CLIENT_MODES=[ActionType.MOTION, ActionType.RELAY]

class MotionNamespace(BaseNamespace):
	def on_command(self, *args):
		print('motion', args)
		if debug:
			return
		m1Speed = args[0].split(",")[0]
		m2Speed = args[0].split(",")[1]
		wiringpi.serialPuts(serial,'M1: '+ m1Speed +'\r\n')
		wiringpi.serialPuts(serial,'M2: '+ m2Speed +'\r\n')
class ServoNamespace(BaseNamespace):
	def on_command(self, *args):
		print('servo', args)
		if debug:
			return
		servo.runScriptSub(int(args[0]))

class RelayNamespace(BaseNamespace):
	def on_command(self, *args):
		print('relay', args)
		if debug:
			self.on_get_state(args[0])
			return
		gpio=int(args[0])
		state=args[1]
		if(state=="" ): #dans le cas ou un etat n'est pas specifie
			state=wiringpi.digitalRead(gpio)
			if(state==1):
				state=0
			else:
				state=1
		wiringpi.pinMode(gpio,1)
		wiringpi.digitalWrite(gpio,int(state))
		self.on_get_state(args[0])
		
	#lorsqu'on demande de mettre à jour l'état d'un pin
	def on_update_state(self, *args):
		gpio=int(args[0])
		if debug:
			state=0
		else:
			state=wiringpi.digitalRead(gpio)
		self.emit('update_state', gpio, state)
	#lorque le serveur souhaite récupérer l'état d'un pin
	def on_get_state(self, *args):
		gpio=int(args[0])
		if debug:
			state=0
		else:
			state=wiringpi.digitalRead(gpio)
		self.emit('get_state', gpio, state)
	
class RaspiNamespace(BaseNamespace):
	def on_shutdown(self, *args):
		print('shutdown', args)
		if debug:
			return
		os.system('shutdown -h now')
	def on_reboot(self, *args):
		print('reboot', args)
		if debug:
			return
		os.system('reboot -h now')


#if debug:
logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
logging.basicConfig()

socketIO = SocketIO('https://192.168.1.78', 5000, LoggingNamespace, verify=False)

raspi_namespace = socketIO.define(RaspiNamespace, '/raspi')

if(ActionType.MOTION in CLIENT_MODES):
	motion_namespace = socketIO.define(MotionNamespace, '/motion')
	if not debug:
		import wiringpi, sys
		wiringpi.wiringPiSetup()
		serial = wiringpi.serialOpen('/dev/serial0',9600)
if(ActionType.SERVO in CLIENT_MODES):
	servo_namespace = socketIO.define(ServoNamespace, '/servo')
	if not debug:
		import maestro
		servo = maestro.Controller()
if(ActionType.RELAY in CLIENT_MODES):
	relay_namespace = socketIO.define(RelayNamespace, '/relay')
	if not debug:
		import wiringpi
		wiringpi.wiringPiSetupGpio() 

socketIO.wait()
