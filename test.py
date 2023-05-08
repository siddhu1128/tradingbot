import pkg_resources
import configparser
import kiteAPI

config = configparser.ConfigParser()
config_file = pkg_resources.resource_filename('config', 'config.ini')
# config_file = str(args.config)
config.read(config_file)

kiteAPI.pushover('Test Notification')
print(config_file)
print(int(config.get('default', 'STOPLOSS')))