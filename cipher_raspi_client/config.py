from os.path import isfile, join, exists, dirname
from configparser import ConfigParser, _UNSET
from .constants import CONFIG_FILE

class ConfigFile(ConfigParser):
    def __init__(self, filepath):
        ConfigParser.__init__(self)
        self.filepath = filepath
        if exists(filepath):
            self.read(filepath)

class ClientConfig(ConfigFile):

    def __init__(self, filepath):
        ConfigFile.__init__(self, filepath)

        self.RASPBERRY_ID = self.get('GENERAL', 'RASPBERRY_ID', 
            fallback='UNKNOWN')

        self.ICON = self.get('GENERAL', 'ICON', 
            fallback='fab fa-raspberry-pi')
    
        self.MQTT_BROKER_URL = self.get('MQTT_BROKER', 'URL', 
            fallback='localhost')

        self.MQTT_BROKER_PORT = self.getint('MQTT_BROKER', 'PORT', 
            fallback=1883)

        self.LOG_FILE = self.get('GENERAL', 'LOG_FILE', 
            fallback=join(dirname(__file__), 'app.log'))

        self.WHEEL_MODE = self.getboolean('MOTION', 'WHEEL_MODE', 
            fallback=False)

        self.DEBUG = self.getboolean('CLIENT', 'DEBUG', 
            fallback=False)


client_config = ClientConfig(CONFIG_FILE)