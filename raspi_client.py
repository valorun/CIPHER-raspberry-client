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

debug=True
CLIENT_MODES=[ActionType.RELAY] # liste de toutes les actions prises en charge par le client

class MotionNamespace(BaseNamespace):
	def on_command(self, *args):
		print('motion', args)
		if debug:
			return
		m1Speed = args[0].split(",")[0]
		m2Speed = args[0].split(",")[1]
		wiringpi.serialPuts(serial,'M1: '+ m1Speed +'\r\n')
		wiringpi.serialPuts(serial,'M2: '+ m2Speed +'\r\n')
	def on_stop(self, *args):
		if debug:
			return
		if(ActionType.MOTION in CLIENT_MODES):
			wiringpi.serialPuts(serial,'M1: 0\r\n')
			wiringpi.serialPuts(serial,'M2: 0\r\n')

class ServoNamespace(BaseNamespace):
	def on_command(self, *args):
		print('servo', args)
		if debug:
			return
		servo.runScriptSub(int(args[0]))

class RelayNamespace(BaseNamespace):
	def on_activate_relay(self, *args):
		print('relay', args)
		if debug:
			self.on_update_state(args[0])
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
		self.on_update_state(args[0])

	#lorque qu'il s'agit d'un relai appairé
	def on_activate_paired_relay(self, *args):
		print('relay', args)
		if debug:
			self.on_update_state(args[0])
			return
		gpio=int(args[0])
		state=args[1]
		peers=args[2]

		for peer in peers:
			if(not debug and wiringpi.digitalRead(int(peer))==1):
				return
		self.on_activate_relay(args[0], args[1])

	def on_update_state(self, *args):
		gpio=args[0]
		if debug:
			state=1
		else:
			state=wiringpi.digitalRead(int(gpio))
		self.emit('update_state_for_client', gpio, state)

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

#arret automatique des relais et des moteurs en cas de deconnexion
def on_disconnect():
	print('Disconnected from server')
	if debug:
		return
	if(ActionType.MOTION in CLIENT_MODES):
		wiringpi.serialPuts(serial,'M1: 0\r\n')
		wiringpi.serialPuts(serial,'M2: 0\r\n')
	if(ActionType.RELAY in CLIENT_MODES):
		for gpio in range(2, 27):
			wiringpi.digitalWrite(gpio,0)



#if debug:
logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
logging.basicConfig()

socketIO = SocketIO('http://localhost', 5000, LoggingNamespace, verify=False)
#socketIO = SocketIO('http://192.168.1.20', 5000, LoggingNamespace, verify=False)

socketIO.on('disconnect', on_disconnect)

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
