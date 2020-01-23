import os

RASPBERRY_ID='test'
MQTT_BROKER_URL='localhost'
MQTT_BROKER_PORT=1883 # default is 1883

LOG_FILE=os.path.join(os.path.dirname(__file__), 'app.log')

WHEEL_MODE=True