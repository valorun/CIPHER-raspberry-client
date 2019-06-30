import os
import logging
import json
from .config import DEBUG, RASPBERRY_ID, WHEEL_MODE

class MotionController():
	def __init__(self, client):
		self.client = client
		if not DEBUG:
			import wiringpi as wp
			self.wiringpi = wp
			self.wiringpi.wiringPiSetup()
			self.serial = self.wiringpi.serialOpen('/dev/serial0',9600)
	def command(self, direction, speed):
		logging.info('moving '+direction+', '+str(speed))
		if DEBUG:
			return
		m1Speed = 0
		m2Speed = 0
		if direction == 'forwards':
			m1Speed = speed
			m2Speed = speed
		if direction == 'backwards':
			m1Speed = -speed
			m2Speed = -speed
		if direction == 'left':
			if WHEEL_MODE:
				m1Speed = -speed
			m2Speed = speed
		if direction == 'right':
			m1Speed = speed
			if WHEEL_MODE:
				m2Speed = -speed

		# the speeds used by the control card are between 0 and 2047
		self.wiringpi.serialPuts(self.serial,'M1: '+ str(int(m1Speed * 2047/100)) +'\r\n')
		self.wiringpi.serialPuts(self.serial,'M2: '+ str(int(m2Speed * 2047/100)) +'\r\n')
			

class ServoController():
	def __init__(self, client):
		self.client = client
		if not DEBUG:
			import maestro
			self.servo = maestro.Controller()

	def set_position(self, gpio:str, position:int, speed:int):
		logging.info('servo ' + str(gpio) + ', position ' + str(position) + ', speed ' + str(speed) )
		if DEBUG:
			return
		speed = int(speed/100 * 60) #conversion to maestro speed
		self.servo.setSpeed(int(gpio), speed)
		position = position * 4 #conversion to maestro position (quarter micro-sec)
		self.servo.setTarget(int(gpio), position)

	def sequence(self, index:int):
		logging.info('servo sequence ' + str(index))
		if DEBUG:
			return
		self.servo.runScriptSub(index)

class RelayController():
	def __init__(self, client):
		self.client = client
		if not DEBUG:
			import wiringpi as wp
			self.wiringpi = wp
			self.wiringpi.wiringPiSetupGpio() 

	def activate_relay(self, gpio, state, peers=None):
		logging.info('relay ' + str(gpio)+', ' + str(state) + ', ' + str(peers))
		#check if the peers relays aren't activated
		if peers is not None and len(peers) != 0:
			for peer in peers:
				if(not DEBUG and self.wiringpi.digitalRead(int(peer))==1):
					return

		logging.info('relay ' + str(gpio) + ' ACTIVATED')
		gpio = int(gpio)
		if DEBUG:
			self.update_state(gpio)
			return
		if(state=='' ): #in the case where a state is not specified
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
			if DEBUG:
				state=1
			else:
				state=self.wiringpi.digitalRead(gpio)
			relays_list.append({'gpio':gpio, 'state':state, 'raspi_id':RASPBERRY_ID})
		self.client.publish('server/update_relays_state', json.dumps({'relays':relays_list}))

class RaspiController():
	def __init__(self, client):
		self.client = client

	def shutdown(self):
		logging.info('shutdown')
		if DEBUG:
			return
		os.system('shutdown -h now')
		
	def reboot(self):
		logging.info('reboot')
		if DEBUG:
			return
		os.system('reboot -h now')