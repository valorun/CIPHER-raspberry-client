from os.path import join, dirname

RASPBERRY_ID='test'
MQTT_BROKER_URL='localhost'
MQTT_BROKER_PORT=1883 # default is 1883

LOG_FILE=join(dirname(__file__), 'app.log')

WHEEL_MODE=True