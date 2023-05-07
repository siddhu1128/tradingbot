from setuptools import setup, find_packages, Command
import os


class ConfigCommand(Command):
    description = 'Generate config.ini file from user input'
    user_options = [
        ('STOPLOSS', None, 'Stoploss'),
        ('TRAILINGSTOPLOSS', None, 'Trailg stoploss 40:20'),
        ('EXITTIME', None, '15:10:00'),
        ('SIGNAL', None, 'BANKNIFTY'),
        ('QUANTITY', None, "quantity"),
        ('TICKSIZE', None, "0.05"),
        ('apikey', None, 'Kite API key'),
        ('apisecret', None, 'Kite api secret'),
        ('USERNAME', None, 'Kite Username'),
        ('PASSWORD', None, 'Kite Password'),
        ('TOTPKey', None, 'Kite TOTP'),
        ('DUMPFILELOCATION', None, 'DUMP FILE LOCATION')
    ]

    def initialize_options(self):
        self.STOPLOSS = None
        self.TRAILINGSTOPLOSS = None
        self.EXITTIME = None
        self.SIGNAL = None
        self.QUANTITY = None
        self.TICKSIZE = None
        self.apikey = None
        self.apisecret = None
        self.USERNAME = None
        self.PASSWORD = None
        self.TOTPKey = None
        self.DUMPFILELOCATION = None

    def finalize_options(self):
        pass

    def run(self):
        config_file = os.path.join(os.path.dirname(__file__), 'config', 'config.ini')
        config_template = """
[default]
;Stoploss order [REQUIRED]
STOPLOSS = {STOPLOSS}
;Assume a:b is Trailing Stoploss if Insturment moves a% then stoploss will be lpt price - b% [REQUIRED]
TRAILING_STOPLOSS = {TRAILINGSTOPLOSS}
;Time which script should be square-off all orders and cancel pending orders [REQUIRED]
EXIT_TIME = {EXITTIME}
;Only BANKNIFTY supported for now [REQUIRED]
SIGNAL = {SIGNAL}
;Quantity will be banknifty lot size [REQUIRED]
QUANTITY = {QUANTITY}
;Tick size keep it default should be multiples of 5 [REQUIRED]
TICK_SIZE = {TICKSIZE}
;Zerodha API key [REQUIRED]
api_key = {apikey}
;Zerodha API Secret Key [REQUIRED]
api_secret = {apisecret}
;Zerodha Username [REQUIRED]
USERNAME = {USERNAME}
;Zerodha Password [REQUIRED]
PASSWORD = {PASSWORD}
;TOTP_Key search in google to get it [REQUIRED]
TOTP_Key = {TOTPKey}
; Dump directory
DATA_FILE_LOCATION = {DUMPFILELOCATION}
"""

        STOPLOSS = input('Enter STOPLOSS eg: 20 : ')
        TRAILINGSTOPLOSS = input('Enter TRAILING_STOPLOSS eg: 40:20 : ')
        EXITTIME = input('Enter EXIT_TIME eg: 15:10:00 : ')
        SIGNAL = input('Enter SIGNAL eg: BANKNIFTY : ')
        QUANTITY = input('Enter QUANTITY eg: 25 : ')
        TICKSIZE = input('Enter TICK_SIZE eg: 0.05 : ')
        apikey = input('Enter your Kite Connect API Key: ')
        apisecret = input('Enter your Kite Connect API Secret: ')
        USERNAME = input('Enter your Kite Connect Username: ')
        PASSWORD = input('Enter your Kite Connect Password: ')
        TOTPKey = input('Enter your Kite Connect TOTP Key: ')
        DUMPFILELOCATION = input('Enter your Dump Files Directory path: ')

        with open(config_file, 'w') as config_file:
            config_file.write(config_template.format(
                STOPLOSS=STOPLOSS,
                TRAILINGSTOPLOSS=TRAILINGSTOPLOSS,
                EXITTIME=EXITTIME,
                SIGNAL=SIGNAL,
                QUANTITY=QUANTITY,
                TICKSIZE=TICKSIZE,
                apikey=apikey,
                apisecret=apisecret,
                USERNAME=USERNAME,
                PASSWORD=PASSWORD,
                TOTPKey=TOTPKey,
                DUMPFILELOCATION=DUMPFILELOCATION
            ))
        print('{} file generated successfully.'.format(config_file))


setup(
    name='tradingbot',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        # List your package's dependencies here
        'pandas',
        'requests',
        'kiteconnect',
        'pyotp',
        'python-dateutil',
        'django-bootstrap4',
        'urllib3==1.26.6'
    ],
    # Use data_files in code with below code
    # config_file = os.path.join(os.path.dirname(__file__), 'config', 'config.ini')
    data_files=[('config', ['config/config.ini'])],
    scripts=['short_straddle.py'],
    url='https://github.com/siddhu1128/tradingbot',
    license='',
    author='Siddhartha',
    author_email='siddhartha.dasari11@gmail.com',
    description='Algo trading',
    cmdclass={
        'configure': ConfigCommand,
    },
    entry_points={
        'console_scripts': [
            'scheduleBankNiftyHistoricalData = tradingbot.kiteAPI:schedule_banknifty_historical_data'
        ]
    }
)
