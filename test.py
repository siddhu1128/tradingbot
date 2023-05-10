import pkg_resources
import configparser

config = configparser.ConfigParser()
config_file = pkg_resources.resource_filename('config', 'config.ini')
# config_file = str(args.config)
config.read(config_file)

# kiteAPI.pushover('Test Notification')
print(config_file)
print(config.get('default', 'DB_FILE'))


verify_order = {}
verify_order['status_message'] = None
retry = 0
while verify_order['status_message'] is None:
    if retry <= 2:
        print('hello')
        retry += 1
    else:
        exit(1)
print('end')