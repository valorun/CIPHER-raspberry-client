import os
import logging
import json
from .config import client_config

class MotionController():
	def __init__(self, client, debug=False):
		self.client = client
		self.debug = debug
		if not debug:
			import wiringpi as wp
			self.wiringpi = wp
			self.wiringpi.wiringPiSetup()
			self.serial = self.wiringpi.serialOpen('/dev/serial0',9600)

	def command(self, direction, speed):
		if direction == 'stop':
			logging.info("Stopping motion")
		else:
			logging.info("Moving " + direction + ", " + str(speed))

		if self.debug:
			return
		m1Speed = 0
		m2Speed = 0
		if direction == 'forwards':
			m1Speed = speed
			m2Speed = speed
		elif direction == 'backwards':
			m1Speed = -speed
			m2Speed = -speed
		elif direction == 'left':
			if not client_config.WHEEL_MODE:
				m1Speed = -speed
			m2Speed = speed
		elif direction == 'right':
			m1Speed = speed
			if not client_config.WHEEL_MODE:
				m2Speed = -speed
		elif direction == 'stop':
			m1Speed = 0
			m2Speed = 0
		else:
			logging.warning("Unknown direction '" + direction + "', stopping motion ...")
			m1Speed = 0
			m2Speed = 0
		# the speeds used by the control card are between 0 and 2047
		self.wiringpi.serialPuts(self.serial,'M1: '+ str(int(m1Speed * 2047/100)) +'\r\n')
		self.wiringpi.serialPuts(self.serial,'M2: '+ str(int(m2Speed * 2047/100)) +'\r\n')

class ServoController():
	def __init__(self, client, debug=False):
		self.client = client
		self.debug = debug
		if not debug:
			from . import maestro
			self.servo = maestro.Controller()

	def set_position(self, gpio:str, position:int, speed:int):
		logging.info("Servo " + str(gpio) + ", position " + str(position) + ", speed " + str(speed) )
		if self.debug:
			return
		speed = int(speed/100 * 60) #conversion to maestro speed
		self.servo.setSpeed(int(gpio), speed)
		position = position * 4 #conversion to maestro position (quarter micro-sec)
		self.servo.setTarget(int(gpio), position)

	def get_position(self, gpio:str):
		gpio = int(gpio)
		if self.debug:
			position = 0
			speed = 0
		else:
			position = self.servo.getPosition(gpio)
			speed = self.servo.getSpeed(gpio)
		self.client.publish('server/servo/receive_position', json.dumps({'gpio':gpio, 'position':position, 'speed':speed}))

	def sequence(self, index:int):
		logging.info("Servo sequence " + str(index))
		if self.debug:
			return
		self.servo.runScriptSub(index)

class RelayController():
	def __init__(self, client, debug=False):
		self.client = client
		self.debug = debug
		self.relays = [] # list of pins corresponding to activated relays
		if not debug:
			import wiringpi as wp
			self.wiringpi = wp
			self.wiringpi.wiringPiSetupGpio() 

	def activate_relay(self, gpio, state):
		if state == 1:
			logging.info("Relay " + str(gpio) + " activated.")
		else:
			logging.info("Relay " + str(gpio) + " desactivated.")

		gpio = int(gpio)
		if self.debug:
			self.update_state([gpio])
			return
		if(state == '' ): #in the case where a state is not specified
			state = self.wiringpi.digitalRead(gpio)
			if(state == 1):
				state = 0
			else:
				state = 1
		self.wiringpi.pinMode(gpio, 1)
		self.wiringpi.digitalWrite(gpio, state)
		if state == 1 and gpio not in self.relays:
			self.relays.append(gpio)
		self.update_state([gpio])

	def update_state(self, gpios):
		"""
		Send the state of all specified relays to the server
		"""
		relays_list = []
		logging.info("Updating relays on server")
		for g in gpios:
			gpio = int(g)
			if self.debug:
				state = 1
			else:
				state = self.wiringpi.digitalRead(gpio)
			relays_list.append({'gpio':gpio, 'state':state, 'raspi_id':client_config.RASPBERRY_ID})
		self.client.publish('server/update_relays_state', json.dumps({'relays':relays_list}))

	def stop(self):
		for r in self.relays:
			self.activate_relay(r, 0)

class RaspiController():
	def __init__(self, client, debug=False):
		self.client = client
		self.debug = debug

	def shutdown(self):
		logging.info('Shutting down ...')
		if self.debug:
			return
		os.system('shutdown -h now')
		
	def reboot(self):
		logging.info('Rebooting ...')
		if self.debug:
			return
		os.system('reboot -h now')
