import os
import re
import datetime
import time
import pandas as pd
import argparse
import logging
from pathlib import Path
import json
import calendar
import configparser
import kiteAPI
import pkg_resources
import kiteconnect
from sqlalchemy import create_engine

os.environ['TZ'] = 'Asia/Kolkata'
time.tzset()

parser = argparse.ArgumentParser()
parser.add_argument('--dev', action="store_true", default=False)
parser.add_argument('--continue', dest='continueTrade', action="store_true", default=False)
parser.add_argument('-t', '--token', dest='token', type=str, help="zerodha token")
parser.add_argument('-p', '--profile', dest='profile', default='default', type=str, help="configuration profile")
parser.add_argument('--target', dest='target', type=int, help="target in rupees")
parser.add_argument('-e', '--expiry', dest='expiry_date', type=str, help="Banknifty expiry date")
parser.add_argument('--config', dest='config', required=False, help="config file full path with filename")
logfilegroup = parser.add_mutually_exclusive_group(required=False)
logfilegroup.add_argument('--log', dest='logpath',
                          help="Log location do not give any file names eg: /Users/siddhu/Documents/TradingPot")
logfilegroup.add_argument('--icloud', action="store_true",
                          help="Provide log file patch do not include icloud drive path eg: Documents/test.log")
args = parser.parse_args()

config = configparser.ConfigParser()
config_file = pkg_resources.resource_filename('config', 'config.ini')
# config_file = str(args.config)
config.read(config_file)

if args.icloud:
    # Use icloud drive to save logs
    # Create the log file path in your iCloud Drive
    log_path = str(Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Documents/TradingPot")
    log_file_path = os.path.join(log_path, "/{}.log".format(str(datetime.date.today())))
    swp_file = os.path.join(log_path, "/{}.json".format(str(datetime.date.today())))
else:
    log_path = str(args.logpath)
    log_file_path = "{}/{}.log".format(log_path, str(datetime.date.today()))
    swp_file = "{}/{}.json".format(log_path, str(datetime.date.today()))

log_path = config.get('default', 'LOG_DIR')
log_file_path = "{}/{}.log".format(log_path, str(datetime.date.today()))
swp_file = "{}/{}.json".format(log_path, str(datetime.date.today()))


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a file handler that writes to the log file
handler = logging.FileHandler(log_file_path)

# Set the logging level for the handler
handler.setLevel(logging.DEBUG)

# Create a formatter for the log messages
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Set up the logger
logging.Formatter.converter = time.localtime

# Set the formatter for the handler
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)

# Flush the handler to write the logs to the file
handler.flush()

logging.getLogger("urllib3").setLevel(logging.WARNING)

# # Getting Expiry date
if not args.expiry_date:
    day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    current_date = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).date()
    current_day = day_name[current_date.weekday()]
    if current_date.weekday() == 3:
        expiry_date = current_date + datetime.timedelta(days=7)
    elif current_date.weekday() == 4:
        expiry_date = current_date + datetime.timedelta(days=6)
    elif current_date.weekday() == 5:
        current_date = current_date + datetime.timedelta(days=2)
        current_day = day_name[current_date.weekday()]
    elif current_date.weekday() == 6:
        current_date = current_date + datetime.timedelta(days=1)
        current_day = day_name[current_date.weekday()]
    else:
        expiry_date = current_date - datetime.timedelta(days=(current_date.weekday() - 3))
    expiry_day = day_name[expiry_date.weekday()]
else:
    expiry_date = args.expiry_date

# Arguments
## EXPIRY_DATE  should be in yyyy-mm-dd
try:
    EXPIRY_DATE = expiry_date
    STOPLOSS = int(config.get('default', 'STOPLOSS'))
    TRAILING_STOPLOSS = config.get('default', 'TRAILING_STOPLOSS')
    EXIT_TIME = config.get('default', 'EXIT_TIME')
    SIGNAL = config.get('default', 'SIGNAL')
    QUANTITY = int(config.get('default', 'QUANTITY'))
    TICK_SIZE = float(config.get('default', 'TICK_SIZE'))
    api_key = config.get('default', 'api_key')
    api_secret = config.get('default', 'api_secret')
    USERNAME = config.get('default', 'USERNAME')
    PASSWORD = config.get('default', 'PASSWORD')
    TOTP_Key = config.get('default', 'TOTP_Key')
except Exception as e:
    print(e)
    kiteAPI.pushover('Error: {}'.format(e))

# Globals
trading_log = pd.DataFrame()
trailing_stoploss_log = {}
ATR_TIME = "12:30"
engine = create_engine(kiteAPI.engine_url)


# funtions
def verifyOrder(order_id):
    data = {}
    orders = kite.orders()
    for i in range(len(orders)):
        if orders[i]['order_id'] == str(order_id):
            # {'placed_by': 'TMT026', 'order_id': '230324002577714', 'exchange_order_id': '1100000018841258', 'parent_order_id': None, 'status': 'COMPLETE',
            # 'status_message': None, 'status_message_raw': None, 'order_timestamp': '2023-03-24 13:43:35', 'exchange_update_timestamp': '2023-03-24 13:43:35',
            # 'exchange_timestamp': '2023-03-24 13:43:35', 'variety': 'regular', 'modified': False, 'exchange': 'NSE', 'tradingsymbol': 'IDEA', 'instrument_token': 3677697,
            # 'order_type': 'MARKET', 'transaction_type': 'SELL', 'validity': 'DAY', 'validity_ttl': 0, 'product': 'MIS', 'quantity': 1, 'disclosed_quantity': 0, 'price': 0,
            # 'trigger_price': 0, 'average_price': 6.25, 'filled_quantity': 1, 'pending_quantity': 0, 'cancelled_quantity': 0, 'market_protection': 0, 'meta': {}, 'tag': 'TradingPot', 'tags': ['TradingPot'], 'guid': '01XSxB6GMlcFusV'}
            return orders[i]


def create_orders(CE_Dict, PE_Dict):
    order_data = {}

    # # Test Data
    # CE_Trading_Signal = 'IDEA'
    # PE_Trading_Signal = 'YESBANK'
    # QUANTITY = 1
    # # End of Test Data

    order_data['CE_Trading_Signal'] = CE_Trading_Signal
    order_data['PE_Trading_Signal'] = PE_Trading_Signal
    if not args.dev:
        # Zerodha Sell call
        CE_Order = kite.place_order(
            variety=VARIETY,
            exchange=EXCHANGE,
            tradingsymbol=order_data['CE_Trading_Signal'],
            transaction_type=kite.TRANSACTION_TYPE_SELL,
            quantity=QUANTITY,
            product=kite.PRODUCT_MIS,
            order_type=ORDER_TYPE,
            price=PRICE,
            tag=TAG
        )
        time.sleep(10)
        order_data['CE_Order_Id'] = CE_Order
        verify_order = verifyOrder(order_data['CE_Order_Id'])
        try:
            if verify_order['status'] == kite.STATUS_COMPLETE:
                order_data['CE_AVG_Price'] = verify_order["average_price"]
                order_data['CE_Entry_Time'] = str(verify_order["order_timestamp"])
                logger.info('{} {} order placed successfully. Status: {}'.format(order_data['CE_Trading_Signal'],
                                                                     kite.TRANSACTION_TYPE_SELL, verify_order['status']))
            else:
                logger.error('Retrying {} {} order Status: {}, Reason: {}'.format(order_data['CE_Trading_Signal'],
                                                                             kite.TRANSACTION_TYPE_SELL,
                                                                                  verify_order['status'],
                                                                             verify_order['status_message']))
                kiteAPI.pushover('Error: Retrying {} {} order Status: {}, Reason: {}'.format(order_data['CE_Trading_Signal'],
                                                                                             kite.TRANSACTION_TYPE_SELL,
                                                                                             verify_order['status'],
                                                                                             verify_order['status_message']))
                retry = 0
                while verify_order['status'] != kite.STATUS_COMPLETE and verify_order['status'] != 'PENDING' and verify_order['status'] != 'OPEN PENDING':
                    if retry <= 2:
                        CE_Order = kite.place_order(
                            variety=VARIETY,
                            exchange=EXCHANGE,
                            tradingsymbol=order_data['CE_Trading_Signal'],
                            transaction_type=kite.TRANSACTION_TYPE_SELL,
                            quantity=QUANTITY,
                            product=kite.PRODUCT_MIS,
                            order_type=ORDER_TYPE,
                            price=PRICE,
                            tag=TAG
                        )
                        time.sleep(10)
                        order_data['CE_Order_Id'] = CE_Order
                        verify_order = verifyOrder(order_data['CE_Order_Id'])
                        if verify_order['status'] == kite.STATUS_COMPLETE:
                            order_data['CE_AVG_Price'] = verify_order["average_price"]
                            order_data['CE_Entry_Time'] = str(verify_order["order_timestamp"])
                            logger.info('{} {} order placed successfully. Status: {}'.format(order_data['CE_Trading_Signal'],
                                                                                 kite.TRANSACTION_TYPE_SELL, verify_order['status']))
                        else:
                            logger.error('Retrying {} {} order Status: {}, Reason: {}'.format(order_data['CE_Trading_Signal'],
                                                                                         kite.TRANSACTION_TYPE_SELL,
                                                                                              verify_order['status'],
                                                                                         verify_order['status_message']))
                            kiteAPI.pushover('Error: Retrying {} {} order Status: {}, Reason: {}'.format(order_data['CE_Trading_Signal'],
                                                                                                         kite.TRANSACTION_TYPE_SELL,
                                                                                                         verify_order['status'],
                                                                                                         verify_order['status_message']))
                        retry += 1
                        time.sleep(5)
                    else:
                        logger.error('Unable to place {} {} order Status: {}, Reason: {}'.format(order_data['CE_Trading_Signal'],
                                                                              kite.TRANSACTION_TYPE_SELL,
                                                                                 verify_order['status'],
                                                                              verify_order['status_message']))
                        kiteAPI.pushover('Error: Unable to place {} {} order Status: {}, Reason: {}'.format(order_data['CE_Trading_Signal'],
                                                                                                            kite.TRANSACTION_TYPE_SELL,
                                                                                                            verify_order['status'],
                                                                                                            verify_order['status_message']))
                        exit(1)
        except KeyError as e:
            logger.error(
                '{} {} order not available'.format(order_data['CE_Trading_Signal'], kite.TRANSACTION_TYPE_SELL))
            kiteAPI.pushover('Error: {} {} order not available'.format(order_data['CE_Trading_Signal'], kite.TRANSACTION_TYPE_SELL))

        # Zerodha Sell put
        PE_Order = kite.place_order(
            variety=VARIETY,
            exchange=EXCHANGE,
            tradingsymbol=order_data['PE_Trading_Signal'],
            transaction_type=kite.TRANSACTION_TYPE_SELL,
            quantity=QUANTITY,
            product=kite.PRODUCT_MIS,
            order_type=kite.ORDER_TYPE_MARKET,
            tag="TradingPot"
        )
        time.sleep(10)
        order_data['PE_Order_Id'] = PE_Order
        verify_order = verifyOrder(order_data['PE_Order_Id'])
        try:
            if verify_order['status'] == kite.STATUS_COMPLETE:
                order_data['PE_AVG_Price'] = verify_order["average_price"]
                order_data['PE_Entry_Time'] = str(verify_order["order_timestamp"])
                logger.info('{} {} order placed successfully. Status: {}'.format(order_data['PE_Trading_Signal'],
                                                                     kite.TRANSACTION_TYPE_SELL, verify_order['status']))
            else:
                logger.error('Retrying {} {} order Status: {}, Reason: {}'.format(order_data['PE_Trading_Signal'],
                                                                             kite.TRANSACTION_TYPE_SELL,
                                                                                  verify_order['status'],
                                                                             verify_order['status_message']))
                kiteAPI.pushover('Error: Retrying {} {} order Status:{}, Reason: {}'.format(order_data['PE_Trading_Signal'],
                                                                                            kite.TRANSACTION_TYPE_SELL,
                                                                                            verify_order['status'],
                                                                                            verify_order['status_message']))
                retry = 0
                while verify_order['status'] != kite.STATUS_COMPLETE and verify_order['status'] != 'PENDING' and verify_order['status'] != 'OPEN PENDING':
                    if retry <= 2:
                        PE_Order = kite.place_order(
                            variety=VARIETY,
                            exchange=EXCHANGE,
                            tradingsymbol=order_data['PE_Trading_Signal'],
                            transaction_type=kite.TRANSACTION_TYPE_SELL,
                            quantity=QUANTITY,
                            product=kite.PRODUCT_MIS,
                            order_type=kite.ORDER_TYPE_MARKET,
                            tag="TradingPot"
                        )
                        time.sleep(10)
                        order_data['PE_Order_Id'] = PE_Order
                        verify_order = verifyOrder(order_data['PE_Order_Id'])
                        if verify_order['status'] == kite.STATUS_COMPLETE:
                            order_data['PE_AVG_Price'] = verify_order["average_price"]
                            order_data['PE_Entry_Time'] = str(verify_order["order_timestamp"])
                            logger.info('{} {} order placed successfully. Status: {}'.format(order_data['PE_Trading_Signal'],
                                                                                 kite.TRANSACTION_TYPE_SELL, verify_order['status']))
                        else:
                            logger.error('Retrying {} {} order Status:{}, Reason: {}'.format(order_data['PE_Trading_Signal'],
                                                                                  kite.TRANSACTION_TYPE_SELL,
                                                                                    verify_order['status'],
                                                                                  verify_order['status_message']))
                            kiteAPI.pushover('Error: Retrying {} {} order Status: {}, Reason: {}'.format(order_data['PE_Trading_Signal'],
                                                                                                         kite.TRANSACTION_TYPE_SELL,
                                                                                                         verify_order['status'],
                                                                                                         verify_order['status_message']))
                        retry += 1
                        time.sleep(5)
                    else:
                        logger.error('Unable to place {} {} order Status:{}, Reason: {}'.format(order_data['PE_Trading_Signal'],
                                                                              kite.TRANSACTION_TYPE_SELL,
                                                                                verify_order['status'],
                                                                              verify_order['status_message']))
                        kiteAPI.pushover('Error: Unable to place {} {} order Status: {}, Reason: {}'.format(order_data['PE_Trading_Signal'],
                                                                                                            kite.TRANSACTION_TYPE_SELL,
                                                                                                            verify_order['status'],
                                                                                                            verify_order['status_message']))
                        exit(1)
        except KeyError as e:
            logger.error(
                '{} {} order not available'.format(order_data['PE_Trading_Signal'], kite.TRANSACTION_TYPE_SELL))
            kiteAPI.pushover('Error: {} {} order not available'.format(order_data['PE_Trading_Signal'], kite.TRANSACTION_TYPE_SELL))

        # Create stoploss orders based on ce and pe avg prices
        order_data['CE_Stoploss_Price'] = round(
            (order_data['CE_AVG_Price'] + (order_data['CE_AVG_Price'] * (STOPLOSS / 100))) / TICK_SIZE) * TICK_SIZE
        order_data['PE_Stoploss_Price'] = round(
            (order_data['PE_AVG_Price'] + (order_data['PE_AVG_Price'] * (STOPLOSS / 100))) / TICK_SIZE) * TICK_SIZE

        CE_Stoploss_Order = kite.place_order(
            variety=VARIETY,
            exchange=EXCHANGE,
            tradingsymbol=order_data['CE_Trading_Signal'],
            transaction_type=kite.TRANSACTION_TYPE_BUY,
            quantity=QUANTITY,
            product=kite.PRODUCT_MIS,
            order_type=kite.ORDER_TYPE_SL,
            price=order_data['CE_Stoploss_Price'],
            trigger_price=round((int(order_data['CE_Stoploss_Price']) - (
                    int(order_data['CE_Stoploss_Price']) * 0.01)) / TICK_SIZE) * TICK_SIZE,
            tag="TradingPot"
        )
        time.sleep(10)
        order_data['CE_Stoploss_Order_Id'] = CE_Stoploss_Order
        verify_order = verifyOrder(order_data['CE_Stoploss_Order_Id'])
        try:
            if verify_order['status'] == 'TRIGGER PENDING':
                logger.info('Stoploss order for {} {} placed successfully. Status: {}'.format(order_data['CE_Trading_Signal'],
                                                                                  kite.TRANSACTION_TYPE_BUY, verify_order['status']))
            else:
                retry = 0
                while verify_order['status'] != 'TRIGGER PENDING':
                    if retry <= 2:
                        logger.error('Retrying {} {} order Status:{}, Reason: {}'.format(order_data['CE_Trading_Signal'],
                                                                                     kite.TRANSACTION_TYPE_BUY,
                                                                                         verify_order['status'],
                                                                                     verify_order['status_message']))
                        kiteAPI.pushover('Error: Retrying {} {} order Status:{}, Reason: {}'.format(order_data['CE_Trading_Signal'],
                                                                                                    kite.TRANSACTION_TYPE_BUY,
                                                                                                    verify_order['status'],
                                                                                                    verify_order['status_message']))
                        CE_Stoploss_Order = kite.place_order(
                            variety=VARIETY,
                            exchange=EXCHANGE,
                            tradingsymbol=order_data['CE_Trading_Signal'],
                            transaction_type=kite.TRANSACTION_TYPE_BUY,
                            quantity=QUANTITY,
                            product=kite.PRODUCT_MIS,
                            order_type=kite.ORDER_TYPE_SL,
                            price=order_data['CE_Stoploss_Price'],
                            trigger_price=round((int(order_data['CE_Stoploss_Price']) - (
                                    int(order_data['CE_Stoploss_Price']) * 0.01)) / TICK_SIZE) * TICK_SIZE,
                            tag="TradingPot"
                        )
                        time.sleep(10)
                        order_data['CE_Stoploss_Order_Id'] = CE_Stoploss_Order
                        verify_order = verifyOrder(order_data['CE_Stoploss_Order_Id'])
                        retry += 1
                        time.sleep(5)
                    else:
                        logger.error('Unable to place {} {} order Status: {}, Reason: {}'.format(order_data['CE_Trading_Signal'],
                                                                                     kite.TRANSACTION_TYPE_BUY,
                                                                                     verify_order['status'],
                                                                                     verify_order['status_message']))
                        kiteAPI.pushover('Error: Unable to place {} {} order Status: {}, Reason: {}'.format(order_data['CE_Trading_Signal'],
                                                                                                            kite.TRANSACTION_TYPE_BUY,
                                                                                                            verify_order['status'],
                                                                                                            verify_order['status_message']))
                        exit(1)
        except KeyError as e:
            logger.error('{} {} order not available'.format(order_data['CE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))
            kiteAPI.pushover('Error: {} {} order not available'.format(order_data['CE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))

        # Create stoploss orders based on ce and pe avg prices
        PE_Stoploss_Order = kite.place_order(
            variety=VARIETY,
            exchange=EXCHANGE,
            tradingsymbol=order_data['PE_Trading_Signal'],
            transaction_type=kite.TRANSACTION_TYPE_BUY,
            quantity=QUANTITY,
            product=kite.PRODUCT_MIS,
            order_type=kite.ORDER_TYPE_SL,
            price=order_data['PE_Stoploss_Price'],
            trigger_price=round((int(order_data['PE_Stoploss_Price']) - (
                    int(order_data['PE_Stoploss_Price']) * 0.01)) / TICK_SIZE) * TICK_SIZE,
            tag="TradingPot"
        )
        time.sleep(10)
        order_data['PE_Stoploss_Order_Id'] = PE_Stoploss_Order
        verify_order = verifyOrder(order_data['PE_Stoploss_Order_Id'])
        try:
            if verify_order['status'] == 'TRIGGER PENDING':
                logger.info('Stoploss order for {} {} placed successfully. Status: {}'.format(order_data['PE_Trading_Signal'],
                                                                                  kite.TRANSACTION_TYPE_BUY, verify_order['status']))
            else:
                retry = 0
                while verify_order['status'] != 'TRIGGER PENDING':
                    if retry <= 2:
                        logger.error('Retrying {} {} order Status: {}, Reason: {}'.format(order_data['PE_Trading_Signal'],
                                                                              kite.TRANSACTION_TYPE_BUY,
                                                                              verify_order['status'],
                                                                              verify_order['status_message']))
                        kiteAPI.pushover('Error: Retrying {} {} order Status: {}, Reason: {}'.format(order_data['PE_Trading_Signal'],
                                                                                                     kite.TRANSACTION_TYPE_BUY,
                                                                                                     verify_order['status'],
                                                                                                     verify_order['status_message']))
                        PE_Stoploss_Order = kite.place_order(
                            variety=VARIETY,
                            exchange=EXCHANGE,
                            tradingsymbol=order_data['PE_Trading_Signal'],
                            transaction_type=kite.TRANSACTION_TYPE_BUY,
                            quantity=QUANTITY,
                            product=kite.PRODUCT_MIS,
                            order_type=kite.ORDER_TYPE_SL,
                            price=order_data['PE_Stoploss_Price'],
                            trigger_price=round((int(order_data['PE_Stoploss_Price']) - (
                                    int(order_data['PE_Stoploss_Price']) * 0.01)) / TICK_SIZE) * TICK_SIZE,
                            tag="TradingPot"
                        )
                        time.sleep(10)
                        order_data['PE_Stoploss_Order_Id'] = PE_Stoploss_Order
                        verify_order = verifyOrder(order_data['PE_Stoploss_Order_Id'])
                        retry += 1
                        time.sleep(5)
                    else:
                        logger.error('Unable to place {} {} order Status: {}, Reason: {}'.format(order_data['PE_Trading_Signal'],
                                                                                     kite.TRANSACTION_TYPE_BUY,
                                                                                     verify_order['status'],
                                                                                     verify_order['status_message']))
                        kiteAPI.pushover('Error: Unable to place {} {} order Status: {}, Reason: {}'.format(order_data['PE_Trading_Signal'],
                                                                                                            kite.TRANSACTION_TYPE_BUY,
                                                                                                            verify_order['status'],
                                                                                                            verify_order['status_message']))
                        exit(1)
        except KeyError as e:
            logger.error('{} {} order not available'.format(order_data['PE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))
            kiteAPI.pushover('Error: {} {} order not available'.format(order_data['PE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))

    else:
        try:
            order_data['CE_AVG_Price'] = CE_Dict["{}:{}".format(EXCHANGE, order_data['CE_Trading_Signal'])][
                'last_price']
            order_data['PE_AVG_Price'] = PE_Dict["{}:{}".format(EXCHANGE, order_data['PE_Trading_Signal'])][
                'last_price']
        except KeyError as e:
            logger.warning('Unable to fetch LTP prices retrying...!!!')
            time.sleep(5)
            CE_Dict = kite.ltp(["{}:{}".format(EXCHANGE, order_data['CE_Trading_Signal'])])
            PE_Dict = kite.ltp(["{}:{}".format(EXCHANGE, order_data['PE_Trading_Signal'])])

            order_data['CE_AVG_Price'] = CE_Dict["{}:{}".format(EXCHANGE, order_data['CE_Trading_Signal'])][
                'last_price']
            order_data['PE_AVG_Price'] = PE_Dict["{}:{}".format(EXCHANGE, order_data['PE_Trading_Signal'])][
                'last_price']
        order_data['CE_Stoploss_Price'] = int(order_data['CE_AVG_Price']) + (
                int(order_data['CE_AVG_Price']) * (int(STOPLOSS) / 100))
        order_data['PE_Stoploss_Price'] = int(order_data['PE_AVG_Price']) + (
                int(order_data['PE_AVG_Price']) * (int(STOPLOSS) / 100))
        order_data['CE_Order_Id'] = 0
        order_data['PE_Order_Id'] = 0
        order_data['CE_Stoploss_Order_Id'] = 0
        order_data['PE_Stoploss_Order_Id'] = 0
        order_data['CE_Entry_Time'] = str(Current_Time).split(' ')[1]
        logger.info('SELLING {} at {} Price'.format(order_data['CE_Trading_Signal'], order_data['CE_AVG_Price']))
        order_data['PE_Entry_Time'] = str(Current_Time).split(' ')[1]
        logger.info('SELLING {} at {} Price'.format(order_data['PE_Trading_Signal'], order_data['PE_AVG_Price']))
    with open(swp_file, "w") as outfile:
        json.dump(order_data, outfile)
    return order_data


def live_data(order_data):
    trade_data = order_data
    ce_trailing_count = 0
    pe_trailing_count = 0
    trade_data['ce_trailing_dict'] = {}
    trade_data['pe_trailing_dict'] = {}
    trade_data['ce_trailing_count'] = 0
    trade_data['pe_trailing_count'] = 0
    trade_data['ce_sl_hit_price'] = 0
    trade_data['pe_sl_hit_price'] = 0
    trade_data['atr_time'] = ATR_TIME
    if trade_data.get('CE_TRAILING_STOPLOSS_PRICE') is None:
        trade_data['CE_TRAILING_STOPLOSS_PRICE'] = round((int(order_data['CE_AVG_Price']) - (
                int(order_data['CE_AVG_Price']) * (
                int(TRAILING_STOPLOSS.split(':')[0]) / 100))) / TICK_SIZE) * TICK_SIZE
    if trade_data.get('PE_TRAILING_STOPLOSS_PRICE') is None:
        trade_data['PE_TRAILING_STOPLOSS_PRICE'] = round((int(order_data['PE_AVG_Price']) - (
                int(order_data['PE_AVG_Price']) * (
                int(TRAILING_STOPLOSS.split(':')[0]) / 100))) / TICK_SIZE) * TICK_SIZE
    Market_Close_datetime = datetime.datetime.strptime('{} {}'.format(str(datetime.date.today()), '15:15:00'),
                                                       '%Y-%m-%d %H:%M:%S')

    # Square off all trades at market end time
    while datetime.datetime.strptime(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                     '%Y-%m-%d %H:%M:%S') <= Market_Close_datetime:
        while True:
            try:
                CE_Spot_Dict = kite.ltp(["{}:{}".format(EXCHANGE, trade_data['CE_Trading_Signal'])])
                PE_Spot_Dict = kite.ltp(["{}:{}".format(EXCHANGE, trade_data['PE_Trading_Signal'])])
                break
            except kiteconnect.exceptions.DataException:
                time.sleep(5)
        trade_data['CE_Spot_Price'] = CE_Spot_Dict["{}:{}".format(EXCHANGE, trade_data['CE_Trading_Signal'])][
            'last_price']
        trade_data['PE_Spot_Price'] = PE_Spot_Dict["{}:{}".format(EXCHANGE, trade_data['PE_Trading_Signal'])][
            'last_price']

        if trade_data.get('max_profit') is None:
            trade_data['max_profit'] = 0
        if trade_data.get('max_loss') is None:
            trade_data['max_loss'] = 0
        # Verify Orders
        if not args.dev:
            # CE stoploss order
            ce_sl_order = verifyOrder(trade_data['CE_Stoploss_Order_Id'])
            print('ce_sl_order: {}'.format(ce_sl_order))
            try:
                if ce_sl_order['status'] == kite.STATUS_COMPLETE:
                    logger.info('{} Stoploss Triggered at {} price'.format(trade_data['CE_Trading_Signal'],
                                                                           ce_sl_order["average_price"]))
                    trade_data['ce_exit_price'] = ce_sl_order["average_price"]
                    trade_data['ce_exit_time'] = str(ce_sl_order["exchange_timestamp"])
                else:
                    trade_data['ce_exit_price'] = None
                    trade_data['ce_exit_time'] = None
            except KeyError as e:
                logger.error(
                    '{} {} order not available'.format(trade_data['CE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))
                kiteAPI.pushover('Error: {} {} order not available'.format(trade_data['CE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))
            print('ce_exit_price: {}'.format(trade_data['ce_exit_price']))
            # PE stoploss order
            pe_sl_order = verifyOrder(trade_data['PE_Stoploss_Order_Id'])
            print('pe_sl_order: {}'.format(pe_sl_order))
            try:
                if pe_sl_order['status'] == kite.STATUS_COMPLETE:
                    logger.info('{} Stoploss Triggered at {} price'.format(trade_data['PE_Trading_Signal'],
                                                                           pe_sl_order["average_price"]))
                    trade_data['pe_exit_price'] = pe_sl_order["average_price"]
                    trade_data['pe_exit_time'] = str(pe_sl_order["exchange_timestamp"])
                else:
                    trade_data['pe_exit_price'] = None
                    trade_data['pe_exit_time'] = None
            except KeyError as e:
                logger.error(
                    '{} {} order not available'.format(trade_data['PE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))
                kiteAPI.pushover('Error: {} {} order not available'.format(trade_data['PE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))
            print('pe_exit_price: {}'.format(trade_data['pe_exit_price']))

        # Cancel all orders at 15:10
        if datetime.datetime.now() >= datetime.datetime.now().replace(hour=int(EXIT_TIME.split(':')[0]),
                                                                      minute=int(EXIT_TIME.split(':')[1]),
                                                                      second=int(EXIT_TIME.split(':')[2])):
            logger.info('Its time to say good bye...!!!')
            logger.info('Market is closing sweeping out all orders and positions...!!!')
            if trade_data.get('ce_exit_price') is None:
                if not args.dev:
                    CE_Cancel_Order = kite.cancel_order(variety=VARIETY, order_id=trade_data['CE_Stoploss_Order_Id'])
                    CE_Squareoff_Order = kite.place_order(
                        variety=VARIETY,
                        exchange=EXCHANGE,
                        tradingsymbol=trade_data['CE_Trading_Signal'],
                        transaction_type=kite.TRANSACTION_TYPE_BUY,
                        quantity=QUANTITY,
                        product=kite.PRODUCT_MIS,
                        order_type=kite.ORDER_TYPE_MARKET,
                        tag="TradingPot"
                    )
                    trade_data['ce_exit_price'] = trade_data['CE_Spot_Price']
                    time.sleep(10)
                    CE_verify_order = verifyOrder(CE_Squareoff_Order)
                    print("Line 573, CE_verify_order: {}".format(CE_verify_order))
                    try:
                        if CE_verify_order['status'] == kite.STATUS_COMPLETE or CE_verify_order['status'] == 'PENDING' or CE_verify_order['status'] == 'OPEN PENDING':
                            trade_data['ce_exit_price'] = trade_data['CE_Spot_Price']
                            trade_data['ce_exit_time'] = str(CE_verify_order["order_timestamp"]).split(' ')[1]
                            logger.info('{} Squared off successfully..!!!'.format(trade_data['CE_Trading_Signal']))
                        else:
                            logger.error('[Important] Unable to Square off orders please verify manually...!!!')
                            kiteAPI.pushover('Error: [Important] Unable to Square off orders please verify manually...!!!')
                            continue
                    except KeyError as e:
                        logger.error("Unable to place square-off orders")
                        kiteAPI.pushover("Error: Unable to place square-off orders")
                else:
                    trade_data['ce_exit_price'] = trade_data['CE_Spot_Price']
                    trade_data['ce_exit_time'] = str(Current_Time).split(' ')[1]

            if trade_data.get('pe_exit_price') is None:
                if not args.dev:
                    PE_Cancel_Order = kite.cancel_order(variety=VARIETY, order_id=trade_data['PE_Stoploss_Order_Id'])
                    PE_Squareoff_Order = kite.place_order(
                        variety=VARIETY,
                        exchange=EXCHANGE,
                        tradingsymbol=trade_data['PE_Trading_Signal'],
                        transaction_type=kite.TRANSACTION_TYPE_BUY,
                        quantity=QUANTITY,
                        product=kite.PRODUCT_MIS,
                        order_type=kite.ORDER_TYPE_MARKET,
                        tag="TradingPot"
                    )
                    trade_data['pe_exit_price'] = trade_data['PE_Spot_Price']
                    time.sleep(10)
                    PE_verify_order = verifyOrder(PE_Squareoff_Order)
                    print("Line 605, PE_verify_order: {}".format(PE_verify_order))
                    try:
                        if PE_verify_order['status'] == kite.STATUS_COMPLETE or PE_verify_order['status'] == 'PENDING' or PE_verify_order['status'] == 'OPEN PENDING':
                            trade_data['pe_exit_price'] = trade_data['PE_Spot_Price']
                            trade_data['pe_exit_time'] = str(PE_verify_order["order_timestamp"]).split(' ')[1]
                            logger.info('{} Squared off successfully..!!!'.format(trade_data['PE_Trading_Signal']))
                        else:
                            logger.error('[Important] Unable to Square off orders please verify manually...!!!')
                            kiteAPI.pushover('Error: [Important] Unable to Square off orders please verify manually...!!!')
                            continue
                    except KeyError as e:
                        logger.error("Unable to place square-off orders")
                        kiteAPI.pushover("Error: Unable to place square-off orders")
                else:
                    trade_data['pe_exit_price'] = trade_data['PE_Spot_Price']
                    trade_data['pe_exit_time'] = str(Current_Time).split(' ')[1]


        # If Target reached
        trade_data['CE_PnL'] = round(
            ((trade_data['CE_AVG_Price'] - trade_data['CE_Spot_Price']) * QUANTITY) if trade_data.get(
                'ce_exit_price') is None else ((trade_data['CE_AVG_Price'] - trade_data['ce_exit_price']) * QUANTITY),
            2)
        trade_data['PE_PnL'] = round(
            ((trade_data['PE_AVG_Price'] - trade_data['PE_Spot_Price']) * QUANTITY) if trade_data.get(
                'pe_exit_price') is None else ((trade_data['PE_AVG_Price'] - trade_data['pe_exit_price']) * QUANTITY),
            2)
        if round(sum([trade_data['CE_PnL'], trade_data['PE_PnL']]), 2) >= trade_data['target'] or round(sum([trade_data['CE_PnL'], trade_data['PE_PnL']]), 2) <= (trade_data['target'] * -1):
            logger.info('Total PnL reached the target/Loss...!!!')
            logger.info('Squaring off all orders and positions...!!!')
            if trade_data.get('ce_exit_price') is None:
                if not args.dev:
                    CE_Cancel_Order = kite.cancel_order(variety=VARIETY, order_id=trade_data['CE_Stoploss_Order_Id'])
                    CE_Squareoff_Order = kite.place_order(
                        variety=VARIETY,
                        exchange=EXCHANGE,
                        tradingsymbol=trade_data['CE_Trading_Signal'],
                        transaction_type=kite.TRANSACTION_TYPE_BUY,
                        quantity=QUANTITY,
                        product=kite.PRODUCT_MIS,
                        order_type=kite.ORDER_TYPE_MARKET,
                        tag="TradingPot"
                    )
                    trade_data['ce_exit_price'] = trade_data['CE_Spot_Price']
                    time.sleep(10)
                    CE_verify_order = verifyOrder(CE_Squareoff_Order)
                    print("Line 573, CE_verify_order: {}".format(CE_verify_order))
                    try:
                        if CE_verify_order['status'] == kite.STATUS_COMPLETE or CE_verify_order['status'] == 'PENDING' or CE_verify_order['status'] == 'OPEN PENDING':
                            trade_data['ce_exit_price'] = trade_data['CE_Spot_Price']
                            trade_data['ce_exit_time'] = str(CE_verify_order["order_timestamp"]).split(' ')[1]
                            logger.info('{} Squared off successfully..!!!'.format(trade_data['CE_Trading_Signal']))
                        else:
                            logger.error('[Important] Unable to Square off orders please verify manually...!!!')
                            kiteAPI.pushover('Error: [Important] Unable to Square off orders please verify manually...!!!')
                            continue
                    except KeyError as e:
                        logger.error("Unable to place square-off orders")
                        kiteAPI.pushover("Error: Unable to place square-off orders")
                else:
                    trade_data['ce_exit_price'] = trade_data['CE_Spot_Price']
                    trade_data['ce_exit_time'] = str(Current_Time).split(' ')[1]

            if trade_data.get('pe_exit_price') is None:
                if not args.dev:
                    PE_Cancel_Order = kite.cancel_order(variety=VARIETY, order_id=trade_data['PE_Stoploss_Order_Id'])
                    PE_Squareoff_Order = kite.place_order(
                        variety=VARIETY,
                        exchange=EXCHANGE,
                        tradingsymbol=trade_data['PE_Trading_Signal'],
                        transaction_type=kite.TRANSACTION_TYPE_BUY,
                        quantity=QUANTITY,
                        product=kite.PRODUCT_MIS,
                        order_type=kite.ORDER_TYPE_MARKET,
                        tag="TradingPot"
                    )
                    trade_data['pe_exit_price'] = trade_data['PE_Spot_Price']
                    time.sleep(10)
                    PE_verify_order = verifyOrder(PE_Squareoff_Order)
                    print("Line 605, PE_verify_order: {}".format(PE_verify_order))
                    try:
                        if PE_verify_order['status'] == kite.STATUS_COMPLETE or PE_verify_order['status'] == 'PENDING' or PE_verify_order['status'] == 'OPEN PENDING':
                            trade_data['pe_exit_price'] = trade_data['PE_Spot_Price']
                            trade_data['pe_exit_time'] = str(PE_verify_order["order_timestamp"]).split(' ')[1]
                            logger.info('{} Squared off successfully..!!!'.format(trade_data['PE_Trading_Signal']))
                        else:
                            logger.error('[Important] Unable to Square off orders please verify manually...!!!')
                            kiteAPI.pushover('Error: [Important] Unable to Square off orders please verify manually...!!!')
                            continue
                    except KeyError as e:
                        logger.error("Unable to place square-off orders")
                        kiteAPI.pushover("Error: Unable to place square-off orders")
                else:
                    trade_data['pe_exit_price'] = trade_data['PE_Spot_Price']
                    trade_data['pe_exit_time'] = str(Current_Time).split(' ')[1]

        # Trailing stoploss
        if (trade_data['CE_Spot_Price'] <= trade_data['CE_TRAILING_STOPLOSS_PRICE']) & (
                trade_data.get('ce_exit_price') is None):  # TESTBLOCK Change this to <= modified for testing
            trade_data['CE_Stoploss_Price'] = round((round((int(trade_data['CE_Spot_Price']) + (
                    int(trade_data['CE_Spot_Price']) * (
                    int(TRAILING_STOPLOSS.split(':')[1]) / 100))) / TICK_SIZE) * TICK_SIZE), 2)
            logger.info('{} LTP reaches {}% Trailing stoploss by {}%'.format(trade_data['CE_Trading_Signal'],
                                                                             TRAILING_STOPLOSS.split(':')[0],
                                                                             TRAILING_STOPLOSS.split(':')[1]))
            kiteAPI.pushover('{} LTP reaches {}% Trailing stoploss by {}%'.format(trade_data['CE_Trading_Signal'],
                                                                                  TRAILING_STOPLOSS.split(':')[0],
                                                                                  TRAILING_STOPLOSS.split(':')[1]))
            if not args.dev:
                try:
                    if ce_sl_order['status'] == 'TRIGGER PENDING':
                        CE_Stoploss_Order = kite.modify_order(variety=VARIETY,
                                                              order_id=trade_data['CE_Stoploss_Order_Id'],
                                                              price=trade_data['CE_Stoploss_Price'],
                                                              trigger_price=round((int(
                                                                  trade_data['CE_Stoploss_Price']) - (int(trade_data[
                                                                                                              'CE_Stoploss_Price']) * 0.01)) / TICK_SIZE) * TICK_SIZE)
                        logger.info(
                            'Order_Id:{} Modified stoploss order at price {}'.format(trade_data['CE_Stoploss_Order_Id'],
                                                                                     trade_data['CE_Stoploss_Price']))
                        logger.info('Stoploss order for {} {} modified/trailed successfully'.format(
                            trade_data['CE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))
                    else:
                        logger.error('Unable to modify {} {} order Reason: {}'.format(trade_data['CE_Trading_Signal'],
                                                                                      kite.TRANSACTION_TYPE_BUY,
                                                                                      ce_sl_order['status_message']))
                        kiteAPI.pushover('Error: Unable to modify {} {} order Reason: {}'.format(trade_data['CE_Trading_Signal'],
                                                                                                 kite.TRANSACTION_TYPE_BUY,
                                                                                                 ce_sl_order['status_message']))
                        continue
                except KeyError as e:
                    logger.error(
                        '{} {} order not available'.format(trade_data['CE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))
                    kiteAPI.pushover('Error: {} {} order not available'.format(trade_data['CE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))

            # if trailing stoploss hits modify trailing stoploss price to current price
            trade_data['CE_TRAILING_STOPLOSS_PRICE'] = round((int(trade_data['CE_Spot_Price']) - (
                    int(trade_data['CE_Spot_Price']) * (
                    int(TRAILING_STOPLOSS.split(':')[0]) / 100))) / TICK_SIZE) * TICK_SIZE
            logger.info('{} Next Traling stoploss price {}'.format(trade_data['CE_Trading_Signal'],
                                                                   trade_data['CE_TRAILING_STOPLOSS_PRICE']))
            ce_trailing_count += 1
            logger.info('Stoploss trailed successfully Trail_count: {}'.format(trade_data['ce_trailing_count']))
            trade_data['ce_trailing_dict'][ce_trailing_count] = "{} TSL:{} SL: {}".format(trade_data['CE_Spot_Price'],
                                                                                          trade_data[
                                                                                              'CE_Stoploss_Price'],
                                                                                          str(Current_Time).split(' ')[
                                                                                              1])

        # Trailing stoploss
        if (trade_data['PE_Spot_Price'] <= trade_data['PE_TRAILING_STOPLOSS_PRICE']) & (
                trade_data.get('pe_exit_price') is None):  # TESTBLOCK Change this to <= modified for testing
            trade_data['PE_Stoploss_Price'] = round((round((int(trade_data['PE_Spot_Price']) + (
                    int(trade_data['PE_Spot_Price']) * (
                    int(TRAILING_STOPLOSS.split(':')[1]) / 100))) / TICK_SIZE) * TICK_SIZE), 2)
            logger.info('{} LTP reaches {}% Trailing stoploss by {}%'.format(trade_data['PE_Trading_Signal'],
                                                                             TRAILING_STOPLOSS.split(':')[0],
                                                                             TRAILING_STOPLOSS.split(':')[1]))
            kiteAPI.pushover('{} LTP reaches {}% Trailing stoploss by {}%'.format(trade_data['PE_Trading_Signal'],
                                                                                  TRAILING_STOPLOSS.split(':')[0],
                                                                                  TRAILING_STOPLOSS.split(':')[1]))
            if not args.dev:
                try:
                    if pe_sl_order['status'] == 'TRIGGER PENDING':
                        PE_Stoploss_Order = kite.modify_order(variety=VARIETY,
                                                              order_id=trade_data['PE_Stoploss_Order_Id'],
                                                              # Trying to change with initial order ids instead of stoploss order ids
                                                              price=trade_data['PE_Stoploss_Price'],
                                                              trigger_price=round((int(
                                                                  trade_data['PE_Stoploss_Price']) - (int(trade_data[
                                                                                                              'PE_Stoploss_Price']) * 0.01)) / TICK_SIZE) * TICK_SIZE, )

                        logger.info('Stoploss order for {} {} modified/trailed successfully'.format(
                            trade_data['PE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))
                        logger.info(
                            'Order_Id:{} Modified stoploss order at price {}'.format(trade_data['PE_Stoploss_Order_Id'],
                                                                                     trade_data['PE_Stoploss_Price']))
                    else:
                        logger.error('Unable to modify {} {} order Reason: {}'.format(trade_data['PE_Trading_Signal'],
                                                                                      kite.TRANSACTION_TYPE_BUY,
                                                                                      pe_sl_order['status_message']))
                        kiteAPI.pushover('Error: Unable to modify {} {} order Reason: {}'.format(trade_data['PE_Trading_Signal'],
                                                                                                 kite.TRANSACTION_TYPE_BUY,
                                                                                                 pe_sl_order['status_message']))
                        continue
                except KeyError as e:
                    logger.error(
                        '{} {} order not available'.format(trade_data['PE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))
                    kiteAPI.pushover('Error: {} {} order not available'.format(trade_data['PE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))
            # if trailing stoploss hits modify trailing stoploss price to current price
            trade_data['PE_TRAILING_STOPLOSS_PRICE'] = round((int(trade_data['PE_Spot_Price']) - (
                    int(trade_data['PE_Spot_Price']) * (
                    int(TRAILING_STOPLOSS.split(':')[0]) / 100))) / TICK_SIZE) * TICK_SIZE
            logger.info('{} Next Traling stoploss price {}'.format(trade_data['PE_Trading_Signal'],
                                                                   trade_data['PE_TRAILING_STOPLOSS_PRICE']))
            ce_trailing_count += 1
            logger.info('Stoploss trailed successfully Trail_count: {}'.format(trade_data['pe_trailing_count']))
            trade_data['pe_trailing_dict'][pe_trailing_count] = "{} TSL:{} SL: {}".format(trade_data['PE_Spot_Price'],
                                                                                          trade_data[
                                                                                              'PE_Stoploss_Price'],
                                                                                          str(Current_Time).split(' ')[
                                                                                              1])

        # ATR Strategy ###########################################
        if not bool(trade_data['ce_trailing_dict']) or not bool(trade_data['pe_trailing_dict']):
            curr_time = time.strftime("%H:%M")
            if curr_time >= trade_data['atr_time']:
                # code here
                if not args.dev:
                    ce_sl_order = verifyOrder(trade_data['CE_Stoploss_Order_Id'])
                    pe_sl_order = verifyOrder(trade_data['PE_Stoploss_Order_Id'])
                    try:
                        if ce_sl_order['status'] == 'TRIGGER PENDING':
                            trade_data['CE_Stoploss_Price'] = round(float(trade_data['CE_Spot_Price']) + float(kiteAPI.getATR(trade_data['CE_Trading_Signal'])))
                            CE_Stoploss_Order = kite.modify_order(variety=VARIETY,
                                                                  order_id=trade_data['CE_Stoploss_Order_Id'],
                                                                  price=(int(trade_data['CE_Stoploss_Price']) / TICK_SIZE) * TICK_SIZE,
                                                                  trigger_price=round((int(trade_data['CE_Stoploss_Price']) - (int(trade_data['CE_Stoploss_Price']) * 0.01)) / TICK_SIZE) * TICK_SIZE)
                            logger.info(
                                'Order_Id:{} Modified stoploss order at price {}'.format(trade_data['CE_Stoploss_Order_Id'],
                                                                                         trade_data['CE_Stoploss_Price']))
                            logger.info('ATR: {} {} modified/trailed successfully'.format(
                                trade_data['CE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))
                            kiteAPI.pushover('ATR: {} {} modified/trailed with price {}'.format(
                                trade_data['CE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY, trade_data['CE_Stoploss_Price']))
                    except KeyError as e:
                        logger.error(
                            '{} {} order not available'.format(trade_data['CE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))
                        kiteAPI.pushover('Error: {} {} order not available'.format(trade_data['CE_Trading_Signal'],
                                                                                   kite.TRANSACTION_TYPE_BUY))

                    try:
                        if pe_sl_order['status'] == 'TRIGGER PENDING':
                            trade_data['PE_Stoploss_Price'] = round(float(trade_data['PE_Spot_Price']) + float(kiteAPI.getATR(trade_data['PE_Trading_Signal'])))
                            PE_Stoploss_Order = kite.modify_order(variety=VARIETY,
                                                                  order_id=trade_data['PE_Stoploss_Order_Id'],
                                                                  # Trying to change with initial order ids instead of stoploss order ids
                                                                  price=(int(trade_data['PE_Stoploss_Price']) / TICK_SIZE) * TICK_SIZE,
                                                                  trigger_price=round((int(trade_data['PE_Stoploss_Price']) - (int(trade_data['PE_Stoploss_Price']) * 0.01)) / TICK_SIZE) * TICK_SIZE)

                            logger.info('ATR: {} {} modified/trailed successfully'.format(
                                trade_data['PE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))
                            kiteAPI.pushover('ATR: {} {} modified/trailed with price {}'.format(
                                trade_data['PE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY, trade_data['PE_Stoploss_Price']))
                            logger.info(
                                'Order_Id:{} Modified stoploss order at price {}'.format(trade_data['PE_Stoploss_Order_Id'],
                                                                                         trade_data['PE_Stoploss_Price']))
                    except KeyError as e:
                        logger.error(
                            '{} {} order not available'.format(trade_data['PE_Trading_Signal'], kite.TRANSACTION_TYPE_BUY))
                        kiteAPI.pushover('Error: {} {} order not available'.format(trade_data['PE_Trading_Signal'],
                                                                                   kite.TRANSACTION_TYPE_BUY))

                trade_data['atr_time'] = (datetime.datetime.strptime(trade_data['atr_time'], "%H:%M") + datetime.timedelta(
                    minutes=30)).strftime("%H:%M")
        # End of ATR Strategy #########################

        trade_data['CE_PnL'] = round(
            ((trade_data['CE_AVG_Price'] - trade_data['CE_Spot_Price']) * QUANTITY) if trade_data.get(
                'ce_exit_price') is None else ((trade_data['CE_AVG_Price'] - trade_data['ce_exit_price']) * QUANTITY),
            2)
        trade_data['PE_PnL'] = round(
            ((trade_data['PE_AVG_Price'] - trade_data['PE_Spot_Price']) * QUANTITY) if trade_data.get(
                'pe_exit_price') is None else ((trade_data['PE_AVG_Price'] - trade_data['pe_exit_price']) * QUANTITY),
            2)
        if trade_data['max_profit'] < round(sum([trade_data['CE_PnL'], trade_data['PE_PnL']]), 2):
            trade_data['max_profit'] = round(sum([trade_data['CE_PnL'], trade_data['PE_PnL']]), 2)
            trade_data['max_profit_time'] = str(datetime.datetime.now().time()).split('.')[0]
        if trade_data['max_loss'] > round(sum([trade_data['CE_PnL'], trade_data['PE_PnL']]), 2):
            trade_data['max_loss'] = round(sum([trade_data['CE_PnL'], trade_data['PE_PnL']]), 2)
            trade_data['max_loss_time'] = str(datetime.datetime.now().time()).split('.')[0]
        logger.info("{} ENTRY_TIME: {}, AVG_PRICE: {}, SL: {}, TSL: {}, LTP: {}, Exit_Price: {}, PnL: {}".format(
            trade_data['CE_Trading_Signal'], trade_data['CE_Entry_Time'], round(trade_data['CE_AVG_Price'], 2),
            round(trade_data['CE_Stoploss_Price'], 2), round(trade_data['CE_TRAILING_STOPLOSS_PRICE'], 2),
            round(trade_data['CE_Spot_Price'], 2),
            trade_data['ce_exit_price'],
            round(trade_data['CE_PnL'], 2)))
        logger.info("{} ENTRY_TIME: {}, AVG_PRICE: {}, SL: {}, TSL: {}, LTP: {}, Exit_Price: {}, PnL: {}".format(
            trade_data['PE_Trading_Signal'], trade_data['PE_Entry_Time'], round(trade_data['PE_AVG_Price'], 2),
            round(trade_data['PE_Stoploss_Price'], 2), round(trade_data['PE_TRAILING_STOPLOSS_PRICE'], 2),
            round(trade_data['PE_Spot_Price'], 2),
            trade_data['pe_exit_price'],
            round(trade_data['PE_PnL'], 2)))
        if 'max_profit_time' not in trade_data:
            trade_data['max_profit_time'] = '00:00:00'
        if 'max_loss_time' not in trade_data:
            trade_data['max_loss_time'] = '00:00:00'
        logger.info('Total PnL: {}, Max_profit: {}, Max_profit_time: {}, Target: {}'.format(round(sum([trade_data['CE_PnL'], trade_data['PE_PnL']]), 2),
                                                           trade_data['max_profit'], trade_data['max_profit_time'], trade_data['target']))
        with open(swp_file, "w") as outfile:
            json.dump(trade_data, outfile)
        time.sleep(5)

        # Database
        record = [{
            'Date': datetime.datetime.now(), 'Day': datetime.date.today(), 'Signal': SIGNAL, 'ATM': ATM, 'Expiry_Date': EXPIRY_DATE, 'SL_Percent': STOPLOSS, 'TSL_Percent': TRAILING_STOPLOSS,
            'CE_Entry_Time': trade_data['CE_Entry_Time'], 'CE_Entry_Price': trade_data['CE_AVG_Price'], 'CE_Quantity': QUANTITY, 'CE_Order_Id': trade_data['CE_Order_Id'] if trade_data.get('CE_Order_Id') is not None else None,
            'CE_Stoploss_Order_Id': trade_data['CE_Stoploss_Order_Id'] if trade_data.get('CE_Stoploss_Order_Id') is not None else None, 'CE_SL_Hit': trade_data['ce_sl_hit_price'],
            'CE_TSL_Hits': str(trade_data['ce_trailing_dict']), 'CE_Exit_Price': trade_data['ce_exit_price'] if trade_data.get('ce_exit_price') is not None else 0, 'CE_Exit_Time': trade_data['ce_exit_time'] if trade_data.get('ce_exit_price') is not None else None,
            'CE_pnl': round(trade_data['CE_PnL'], 2),
            'PE_Entry_Time': trade_data['PE_Entry_Time'], 'PE_Entry_Price': trade_data['PE_AVG_Price'], 'PE_Quantity': QUANTITY, 'PE_Order_Id': trade_data['PE_Order_Id'] if trade_data.get('PE_Order_Id') is not None else None,
            'PE_Stoploss_Order_Id': trade_data['PE_Stoploss_Order_Id'] if trade_data.get('PE_Stoploss_Order_Id') is not None else None, 'PE_SL_Hit': trade_data['pe_sl_hit_price'],
            'PE_TSL_Hits': str(trade_data['pe_trailing_dict']), 'PE_Exit_Price': trade_data['pe_exit_price'] if trade_data.get('pe_exit_price') is not None else 0, 'PE_Exit_Time': trade_data['pe_exit_time'] if trade_data.get('pe_exit_price') is not None else None,
            'PE_pnl': round(trade_data['PE_PnL'], 2),
            'Total_pnl': round(sum([trade_data['CE_PnL'], trade_data['PE_PnL']]), 2),
            'Win_Loss': ('win' if round(sum([trade_data['CE_PnL'], trade_data['PE_PnL']]), 2) > 0 else 'loss'),
            'max_profit': trade_data['max_profit'], 'max_profit_time':trade_data['max_profit_time'], 'max_loss': trade_data['max_loss'], 'max_loss_time':trade_data['max_loss_time'],
            'banknifty_price': kite.ltp('NSE:NIFTY BANK')['NSE:NIFTY BANK']['last_price'],
            'india_vix': kite.ltp('NSE:INDIA VIX')['NSE:INDIA VIX']['last_price'],
            'CE_Price': trade_data['CE_Spot_Price'],
            'PE_Price': trade_data['PE_Spot_Price']
        }]
        df = pd.DataFrame(record)
        df.to_sql('backtest_shortstraddle', con=engine, if_exists='append', index=False, method='multi')
        # End of Database

        # Break if both orders have exit price
        if trade_data.get('ce_exit_price') is not None and trade_data.get('pe_exit_price') is not None:
            trade_data['ce_exit_price'] = verifyOrder(trade_data['CE_Stoploss_Order_Id'])['average_price']
            trade_data['pe_exit_price'] = verifyOrder(trade_data['PE_Stoploss_Order_Id'])['average_price']
            break
    return trade_data


## Auto Login Funtion
kite = kiteAPI.autologin(profile=args.profile)

# Checking Gap Percentage
gapPercent = kiteAPI.getGapPercent('NIFTY BANK', 'NSE', str(datetime.date.today() - datetime.timedelta(days=5)), str(datetime.date.today())).iloc[-1]['gapPercent']
kiteAPI.pushover("Gap Percent: {}".format(gapPercent))
logger.info("Gap Percent: {}".format(gapPercent))
if gapPercent is not None:
    if abs(gapPercent) >= 0.4:
        wait_time = "10:15"
        while True:
            current_time = time.strftime("%H:%M")
            if current_time >= wait_time:
                break
            time.sleep(60)


EXCHANGE = kite.EXCHANGE_NFO
VARIETY = kite.VARIETY_REGULAR
ORDER_TYPE = kite.ORDER_TYPE_MARKET
PRICE = None  # PRICE ONLY FOR TESTING TESTBLOCK
TAG = "TradingBot"
BN_Dict = kite.ltp(["NSE:NIFTY BANK"])
try:
    BN_LTP = BN_Dict['NSE:NIFTY BANK']['last_price']
except TypeError as e:
    logger.error('Enctoken expired please update enctoken and try again...!!!')
    kiteAPI.pushover('Error: Enctoken expired please update enctoken and try again...!!!')
    exit(1)
ATM = 100 * round(BN_LTP / 100)
CE_Trading_Signal = False
PE_Trading_Signal = False
CE_Symbol_List = [
    "BANKNIFTY" + "{}".format(
        str(EXPIRY_DATE).split('-')[0][-2:] + re.sub(r'^0', '', str(EXPIRY_DATE).split('-')[1]) + re.sub(r'^0', '',
                                                                                                         str(EXPIRY_DATE).split(
                                                                                                             '-')[
                                                                                                             2])) + "{}".format(
        ATM) + "CE",
    "BANKNIFTY" + "{}".format(
        str(EXPIRY_DATE).split('-')[0][-2:] + re.sub(r'^0', '', str(EXPIRY_DATE).split('-')[1]) + '{:02d}'.format(
            int(re.sub(r'^0', '', str(EXPIRY_DATE).split('-')[2])))) + "{}".format(ATM) + "CE",
    "BANKNIFTY" + "{}".format(str(EXPIRY_DATE).split('-')[0][-2:] + '{:02d}'.format(
        int(re.sub(r'^0', '', str(EXPIRY_DATE).split('-')[1]))) + '{:02d}'.format(
        int(re.sub(r'^0', '', str(EXPIRY_DATE).split('-')[2])))) + "{}".format(ATM) + "CE",
    "BANKNIFTY" + "{}".format(str(EXPIRY_DATE).split('-')[0][-2:] + '{:02d}'.format(
        int(re.sub(r'^0', '', str(EXPIRY_DATE).split('-')[1]))) + re.sub(r'^0', '',
                                                                         str(EXPIRY_DATE).split('-')[2])) + "{}".format(
        ATM) + "CE",
    "BANKNIFTY" + "{}".format(
        str(EXPIRY_DATE).split('-')[0][-2:] + EXPIRY_DATE.strftime('%b').upper() + re.sub(r'^0', '',
                                                                                          str(EXPIRY_DATE).split('-')[
                                                                                              2])) + "{}".format(
        ATM) + "CE",
]
instrument_list = kite.instruments()
ce = 0
while ce < len(CE_Symbol_List):
    for instrument in instrument_list:
        if instrument['exchange'] == 'NFO' and instrument['tradingsymbol'] == CE_Symbol_List[ce]:
            CE_Trading_Signal = CE_Symbol_List[ce]
            break
    ce += 1

PE_Symbol_List = [
    "BANKNIFTY" + "{}".format(
        str(EXPIRY_DATE).split('-')[0][-2:] + re.sub(r'^0', '', str(EXPIRY_DATE).split('-')[1]) + re.sub(r'^0', '',
                                                                                                         str(EXPIRY_DATE).split(
                                                                                                             '-')[
                                                                                                             2])) + "{}".format(
        ATM) + "PE",
    "BANKNIFTY" + "{}".format(
        str(EXPIRY_DATE).split('-')[0][-2:] + re.sub(r'^0', '', str(EXPIRY_DATE).split('-')[1]) + '{:02d}'.format(
            int(re.sub(r'^0', '', str(EXPIRY_DATE).split('-')[2])))) + "{}".format(ATM) + "PE",
    "BANKNIFTY" + "{}".format(str(EXPIRY_DATE).split('-')[0][-2:] + '{:02d}'.format(
        int(re.sub(r'^0', '', str(EXPIRY_DATE).split('-')[1]))) + '{:02d}'.format(
        int(re.sub(r'^0', '', str(EXPIRY_DATE).split('-')[2])))) + "{}".format(ATM) + "PE",
    "BANKNIFTY" + "{}".format(str(EXPIRY_DATE).split('-')[0][-2:] + '{:02d}'.format(
        int(re.sub(r'^0', '', str(EXPIRY_DATE).split('-')[1]))) + re.sub(r'^0', '',
                                                                         str(EXPIRY_DATE).split('-')[2])) + "{}".format(
        ATM) + "PE",
    "BANKNIFTY" + "{}".format(
        str(EXPIRY_DATE).split('-')[0][-2:] + EXPIRY_DATE.strftime('%b').upper() + re.sub(r'^0', '',
                                                                                          str(EXPIRY_DATE).split('-')[
                                                                                              2])) + "{}".format(
        ATM) + "PE",
]
pe = 0
while pe < len(PE_Symbol_List):
    for instrument in instrument_list:
        if instrument['exchange'] == 'NFO' and instrument['tradingsymbol'] == PE_Symbol_List[pe]:
            PE_Trading_Signal = PE_Symbol_List[pe]
            break
    pe += 1

if not CE_Trading_Signal or not PE_Trading_Signal:
    last_day_of_month = calendar.monthrange(EXPIRY_DATE.year, EXPIRY_DATE.month)[1]
    last_date = datetime.date(EXPIRY_DATE.year, EXPIRY_DATE.month, last_day_of_month)

    # Calculate the number of days between the last date and the last Thursday
    days_until_last_thursday = (last_date.weekday() - 3) % 7

    # Subtract the number of days to get the last Thursday date
    last_thursday = last_date - datetime.timedelta(days=days_until_last_thursday)
    if EXPIRY_DATE == last_thursday:
        for instrument in instrument_list:
            ce_symbol = "BANKNIFTY" + "{}".format(
                str(EXPIRY_DATE).split('-')[0][-2:] + EXPIRY_DATE.strftime('%b').upper()) + "{}".format(ATM) + "CE"
            pe_symbol = "BANKNIFTY" + "{}".format(
                str(EXPIRY_DATE).split('-')[0][-2:] + EXPIRY_DATE.strftime('%b').upper()) + "{}".format(ATM) + "PE"
            if instrument['exchange'] == 'NFO' and instrument['tradingsymbol'] == ce_symbol:
                CE_Trading_Signal = ce_symbol
            if instrument['exchange'] == 'NFO' and instrument['tradingsymbol'] == pe_symbol:
                PE_Trading_Signal = pe_symbol

try:
    CE_Dict = kite.ltp(["{}:{}".format(EXCHANGE, CE_Trading_Signal)])
    PE_Dict = kite.ltp(["{}:{}".format(EXCHANGE, PE_Trading_Signal)])
except Exception as e:
    logger.error(
        "Unable to fetch BANKNIFTY Options Symbols... CE: {}, PE: {}".format(CE_Trading_Signal, PE_Trading_Signal))
    kiteAPI.pushover("Error: Unable to fetch BANKNIFTY Options Symbols... CE: {}, PE: {}".format(CE_Trading_Signal, PE_Trading_Signal))
    exit(1)

Exit_Time = datetime.datetime.strptime('{} {}'.format(str(datetime.date.today()), EXIT_TIME), '%Y-%m-%d %H:%M:%S')
Current_datetime = datetime.datetime.now()
Current_Time = datetime.datetime.strptime(Current_datetime.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')

# margin = kite.margins("equity")

if not os.path.isfile(swp_file):
    # Create orders
    order_data = create_orders(CE_Dict, PE_Dict)
else:
    with open(swp_file, 'r') as f:
        order_data = json.load(f)

# order_data['target'] = int(margin['utilised']['debits'] * 0.01)
order_data['target'] = ((int(QUANTITY/25) * 165000) * 0.01)
trade_data = live_data(order_data)
