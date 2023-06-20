import configparser
import os
import time

import mysql.connector
import requests
import sqlalchemy
from pyotp import TOTP
from kiteconnect import KiteConnect
import kiteconnect
import json
import pandas as pd
import datetime
import dateutil
import pkg_resources
import http.client, urllib

from sqlalchemy import create_engine
from sqlalchemy.exc import PendingRollbackError
from mysql.connector import errors
import subprocess
import sys
import pytz

os.environ['TZ'] = 'Asia/Kolkata'
time.tzset()

# Load Config file
config = configparser.ConfigParser()
config_file = pkg_resources.resource_filename('config', 'config.ini')
config.read(config_file)

# DB_File = f"{Path(__file__).resolve().parent}/db.sqlite3"
# db = sqlite3.connect(DB_File)

engine_url = f'mysql+mysqlconnector://{config.get("default", "DB_USER")}:{config.get("default", "DB_PASSWORD").replace("@", "%40")}@{config.get("default", "DB_HOST")}:{config.get("default", "DB_PORT")}/{config.get("default", "DB_NAME")}'


class KiteApp:
    # Products
    PRODUCT_MIS = "MIS"
    PRODUCT_CNC = "CNC"
    PRODUCT_NRML = "NRML"
    PRODUCT_CO = "CO"

    # Order types
    ORDER_TYPE_MARKET = "MARKET"
    ORDER_TYPE_LIMIT = "LIMIT"
    ORDER_TYPE_SLM = "SL-M"
    ORDER_TYPE_SL = "SL"

    # Varities
    VARIETY_REGULAR = "regular"
    VARIETY_CO = "co"
    VARIETY_AMO = "amo"

    # Transaction type
    TRANSACTION_TYPE_BUY = "BUY"
    TRANSACTION_TYPE_SELL = "SELL"

    # Validity
    VALIDITY_DAY = "DAY"
    VALIDITY_IOC = "IOC"

    # Exchanges
    EXCHANGE_NSE = "NSE"
    EXCHANGE_BSE = "BSE"
    EXCHANGE_NFO = "NFO"
    EXCHANGE_CDS = "CDS"
    EXCHANGE_BFO = "BFO"
    EXCHANGE_MCX = "MCX"

    def __init__(self, enctoken):
        self.headers = {"Authorization": f"enctoken {enctoken}"}
        self.session = requests.session()
        self.root_url = "https://api.kite.trade"
        # self.root_url = "https://kite.zerodha.com/oms"
        self.session.get(self.root_url, headers=self.headers)

    def instruments(self, exchange=None):
        data = self.session.get(f"{self.root_url}/instruments", headers=self.headers).text.split("\n")
        Exchange = []
        for i in data[1:-1]:
            row = i.split(",")
            if exchange is None or exchange == row[11]:
                Exchange.append({'instrument_token': int(row[0]), 'exchange_token': row[1], 'tradingsymbol': row[2],
                                 'name': row[3][1:-1], 'last_price': float(row[4]),
                                 'expiry': dateutil.parser.parse(row[5]).date() if row[5] != "" else None,
                                 'strike': float(row[6]), 'tick_size': float(row[7]), 'lot_size': int(row[8]),
                                 'instrument_type': row[9], 'segment': row[10],
                                 'exchange': row[11]})
        return Exchange

    def quote(self, instruments):
        data = self.session.get(f"{self.root_url}/quote", params={"i": instruments}, headers=self.headers).json()[
            "data"]
        return data

    def ltp(self, instruments):
        data = self.session.get(f"{self.root_url}/quote/ltp", params={"i": instruments}, headers=self.headers).json()[
            "data"]
        return data

    def historical_data(self, instrument_token, from_date, to_date, interval, continuous=False, oi=False):
        params = {"from": from_date,
                  "to": to_date,
                  "interval": interval,
                  "continuous": 1 if continuous else 0,
                  "oi": 1 if oi else 0}
        lst = self.session.get(
            f"{self.root_url}/instruments/historical/{instrument_token}/{interval}", params=params,
            headers=self.headers).json()["data"]["candles"]
        records = []
        for i in lst:
            record = {"date": dateutil.parser.parse(i[0]), "open": i[1], "high": i[2], "low": i[3],
                      "close": i[4], "volume": i[5], }
            if len(i) == 7:
                record["oi"] = i[6]
            records.append(record)
        return records

    def margins(self):
        margins = self.session.get(f"{self.root_url}/user/margins", headers=self.headers).json()["data"]
        return margins

    def orders(self):
        orders = self.session.get(f"{self.root_url}/orders", headers=self.headers).json()["data"]
        return orders

    def positions(self):
        positions = self.session.get(f"{self.root_url}/portfolio/positions", headers=self.headers).json()["data"]
        return positions

    def place_order(self, variety, exchange, tradingsymbol, transaction_type, quantity, product, order_type, price=None,
                    validity=None, disclosed_quantity=None, trigger_price=None, squareoff=None, stoploss=None,
                    trailing_stoploss=None, tag=None):
        # Remove 'self' from the params dictionary
        params = {k: v for k, v in locals().items() if k != 'self'}

        # Remove any keys with a None value from the params dictionary
        params = {k: v for k, v in params.items() if v is not None}

        # Send the request and handle errors
        response = self.session.post(f"{self.root_url}/orders/{variety}", data=params, headers=self.headers).json()
        return response["data"]

    def modify_order(self, variety, order_id, parent_order_id=None, quantity=None, price=None, order_type=None,
                     trigger_price=None, validity=None, disclosed_quantity=None):
        # Remove 'self' from the params dictionary
        params = {k: v for k, v in locals().items() if k != 'self'}

        # Remove any keys with a None value from the params dictionary
        params = {k: v for k, v in params.items() if v is not None}

        response = self.session.put(f"{self.root_url}/orders/{variety}/{order_id}", data=params,
                                    headers=self.headers).json()
        print(response)
        return response["data"]

    def cancel_order(self, variety, order_id, parent_order_id=None):
        order_id = self.session.delete(f"{self.root_url}/orders/{variety}/{order_id}",
                                       data={"parent_order_id": parent_order_id} if parent_order_id else {},
                                       headers=self.headers).json()["data"]["order_id"]
        return order_id


def autologin(method=None, profile='default'):
    session = requests.Session()
    response = session.post("https://kite.zerodha.com/api/login", data={'user_id': config.get(profile, 'USERNAME'),
                                                                        'password': config.get(profile, 'PASSWORD')})
    request_id = json.loads(response.text)['data']['request_id']
    twofa_pin = TOTP(config.get(profile, 'TOTP_Key')).now()
    response_1 = session.post("https://kite.zerodha.com/api/twofa",
                              data={'user_id': config.get(profile, 'USERNAME'), 'request_id': request_id,
                                    'twofa_value': twofa_pin,
                                    'twofa_type': 'totp'})
    enctoken = response_1.headers["Set-Cookie"].split("enctoken=")[1].split(";")[0]
    if method != 'enctoken':
        kite = KiteConnect(api_key=config.get(profile, 'api_key'))
        kite_url = kite.login_url()

        try:
            session.get(kite_url)
        except Exception as e:
            e_msg = str(e)
            # print(e_msg)
            request_token = e_msg.split('request_token=')[1].split(' ')[0].split('&action')[0]
            print('Successful Login with Request Token:{}'.format(request_token))

        access_token = kite.generate_session(request_token, config.get(profile, 'api_secret'))['access_token']
        kite.set_access_token(access_token)

    else:
        kite = KiteApp(enctoken)

    kite.timeout = 60
    return kite


def getHistoricalData(from_date, to_date, timeframe, profile='default'):
    # eg: 2023-05-23, 2023-05-27, minute, BANKNIFTY, NFO-OPT
    pushover("Historical Data Job started...!!!")
    engine = create_engine(engine_url)
    # Autologin
    kite = autologin(profile)
    while True:
        try:
            # get dump of all NSE instruments
            instrument_df = pd.DataFrame(kite.instruments())
            nse_df = pd.DataFrame(kite.instruments('NSE'))
            break
        except kiteconnect.exceptions.DataException:
            time.sleep(5)

    try:
        from_date = datetime.datetime.strptime(str(from_date), '%Y-%m-%d').date()
        to_date = datetime.datetime.strptime(str(to_date), '%Y-%m-%d').date()
    except ValueError as err:
        from_date = datetime.datetime.strptime(str(from_date), '%Y-%m-%d %H:%M:%S')
        to_date = datetime.datetime.strptime(str(to_date), '%Y-%m-%d %H:%M:%S')

    # India Vix
    vix_token = nse_df[nse_df.tradingsymbol == 'INDIA VIX'].iloc[0].instrument_token
    vix_dict = kite.historical_data(vix_token, from_date, to_date, "minute")
    vix_df = pd.DataFrame(vix_dict)
    # vix_df.to_sql('backtest_indiavix', con=engine, if_exists='replace', index=False)
    vix_df.to_sql('backtest_indiavix', con=engine, if_exists='append', index=False, method='multi')

    vix_df.set_index('date', inplace=True)
    print(f"India VIX Historical Data collected succesfullly...!!!")
    vix_df = vix_df.rename(columns={'open': 'vix_open', 'high': 'vix_high', 'low': 'vix_low', 'close': 'vix_close',
                                    'volume': 'vix_volume'})

    # BankNifty Index
    bn_token = nse_df[nse_df.tradingsymbol == 'NIFTY BANK'].iloc[0].instrument_token
    bn_dict = kite.historical_data(bn_token, from_date, to_date, "minute")
    bn_df = pd.DataFrame(bn_dict)
    bn_df.to_sql('backtest_bankniftyindex', con=engine, if_exists='append', index=False, method='multi')
    bn_df.set_index('date', inplace=True)
    print(f"Banknifty Index Historical Data collected succesfullly...!!!")

    # Nifty Index
    nf_token = nse_df[nse_df.tradingsymbol == 'NIFTY 50'].iloc[0].instrument_token
    nf_dict = kite.historical_data(nf_token, from_date, to_date, "minute")
    nf_df = pd.DataFrame(nf_dict)
    nf_df.to_sql('backtest_niftyindex', con=engine, if_exists='append', index=False, method='multi')
    nf_df.set_index('date', inplace=True)
    print(f"Nifty Index Historical Data collected succesfullly...!!!")

    # FINNifty Index
    fn_token = nse_df[nse_df.tradingsymbol == 'NIFTY FIN SERVICE'].iloc[0].instrument_token
    fn_dict = kite.historical_data(fn_token, from_date, to_date, "minute")
    fn_df = pd.DataFrame(fn_dict)
    fn_df.to_sql('backtest_finniftyindex', con=engine, if_exists='append', index=False, method='multi')
    fn_df.set_index('date', inplace=True)
    print(f"Finnifty Index Historical Data collected succesfullly...!!!")

    signals = ['BANKNIFTY', 'NIFTY', 'FINNIFTY']
    for i in signals:
        if i == 'BANKNIFTY':
            signal = 'BANKNIFTY'
            table = 'backtest_bankniftyoptions'
        elif i == 'NIFTY':
            signal = 'NIFTY'
            table = 'backtest_niftyoptions'
        elif i == 'FINNIFTY':
            signal = 'FINNIFTY'
            table = 'backtest_finniftyoptions'
        # exchange = "NFO-OPT"
        # fut_df = instrument_df[instrument_df["segment"] == exchange.upper()]
        # BN_df = fut_df[fut_df.name == signal.upper()]
        BN_df = instrument_df[instrument_df.name == signal.upper()]
        BN_OPT_df = pd.DataFrame()

        for index, row in BN_df.iterrows():
            instrument = row["instrument_token"]
            try:
                data = pd.DataFrame(kite.historical_data(instrument, from_date, to_date, timeframe, oi=True))
                time.sleep(0.5)
                data["instrument_token"] = row["instrument_token"]
                data["exchange_token"] = row["exchange_token"]
                data["tradingsymbol"] = row["tradingsymbol"]
                data["name"] = row["name"]
                data["last_price"] = row["last_price"]
                data["expiry"] = row["expiry"]
                data["strike"] = row["strike"]
                data["tick_size"] = row["tick_size"]
                data["lot_size"] = row["lot_size"]
                data["instrument_type"] = row["instrument_type"]
                data["segment"] = row["segment"]
                data["exchange"] = row["exchange"]
                BN_OPT_df = pd.concat([BN_OPT_df, data])
            except kiteconnect.exceptions.NetworkException as e:
                print('error: {}'.format(e))

        BN_OPT_df.set_index('date', inplace=True)
        BN_OPT_df = BN_OPT_df.sort_values(by='date')
        Final_df = pd.concat([BN_OPT_df, vix_df], axis=1).reset_index()
        engine = create_engine(engine_url, pool_recycle=3600, pool_timeout=30, pool_pre_ping=True)
        chunk_size = 1000  # Adjust the chunk size as per your requirement
        for i in range(0, len(Final_df), chunk_size):
            chunk = Final_df[i:i+chunk_size]
            chunk.to_sql(table, con=engine, if_exists='append', index=False, method='multi')
        print(f"{signal} Options Historical Data collected succesfullly...!!!")
    pushover("Historical Data collected successfully...!!!")


def schedule_historical_data():
    today_date = datetime.date.today()
    # today_date = today_date - datetime.timedelta(days=1)
    start_date = f"{today_date} 09:15:00"
    end_date = f"{today_date} 15:29:00"
    getHistoricalData(start_date, end_date, 'minute', profile='default')


def getGapPercent(signal, exchange, from_date, to_date, profile='default'):
    while True:
        try:
            kite = autologin(profile)
            # Get the instrument token for BANKNIFTY
            instrument = kite.instruments(exchange)
            break
        except kiteconnect.exceptions.DataException:
            time.sleep(5)

    instrument_df = pd.DataFrame(instrument)
    date_format = '%Y-%m-%d'
    for i in range(len(instrument)):
        if instrument[i]["tradingsymbol"] == signal.upper():
            instrument_token = instrument[i]["instrument_token"]

    # Get the previous day's closing price of BANKNIFTY
    historical_candles = kite.historical_data(instrument_token,
                                              datetime.datetime.strptime(from_date, date_format).date(),
                                              datetime.datetime.strptime(to_date, date_format).date(), "minute")
    historical_df = pd.DataFrame(historical_candles)
    date_df = historical_df['date'].dt.date.drop_duplicates()
    gapPercentDict = {}
    for i in range(len(date_df)):
        if i == 0:
            pass
        else:
            curr_date = date_df.iloc[i]
            curr_datetime = datetime.datetime(curr_date.year, curr_date.month, curr_date.day, 9, 15,
                                              tzinfo=datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
            current_day_open = historical_df[historical_df['date'] == curr_datetime].open.iloc[0]
            prev_date = date_df.iloc[i - 1]
            prev_datetime = datetime.datetime(prev_date.year, prev_date.month, prev_date.day, 15, 29,
                                              tzinfo=datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
            previous_day_close = historical_df[historical_df['date'] == prev_datetime].close.iloc[0]
            gapPercentDict[date_df.iloc[i]] = round(
                ((current_day_open - previous_day_close) / previous_day_close) * 100, 2)
    gap_percentage_df = pd.DataFrame.from_dict(gapPercentDict, orient='index', columns=['gapPercent'])
    return gap_percentage_df


def pushover(message, profile='default'):
    API_TOKEN = config.get(profile, 'Pushover_API_Key')
    USER_KEY = config.get(profile, 'Pushover_USER_Key')
    conn = http.client.HTTPSConnection("api.pushover.net:443")
    conn.request("POST", "/1/messages.json",
                 urllib.parse.urlencode({
                     "token": API_TOKEN,
                     "user": USER_KEY,
                     "message": message,
                 }), {"Content-type": "application/x-www-form-urlencoded"})
    return conn.getresponse()


def monitor():
    kite = autologin()
    swp_file = "{}/{}.json".format(config.get('default', 'LOG_DIR'), str(datetime.date.today()))

    if not os.path.isfile(swp_file):
        # Create orders
        sys.exit(0)
    else:
        with open(swp_file, 'r') as f:
            order_data = json.load(f)

    def verifyOrder(order_id):
        orders = kite.orders()
        for i in range(len(orders)):
            if orders[i]['order_id'] == str(order_id):
                return orders[i]

    CE_Order_Id = order_data['CE_Order_Id']
    PE_Order_Id = order_data['PE_Order_Id']
    CE_Stoploss_Order_Id = order_data['CE_Stoploss_Order_Id']
    PE_Stoploss_Order_Id = order_data['PE_Stoploss_Order_Id']

    if verifyOrder(CE_Stoploss_Order_Id) == 'TRIGGER PENDING' or verifyOrder(
            PE_Stoploss_Order_Id) == 'TRIGGER PENDING' or verifyOrder(
            CE_Order_Id) != kite.STATUS_COMPLETE or verifyOrder(PE_Order_Id) != kite.STATUS_COMPLETE:
        try:
            # Use pgrep to check if the cron job is running
            process = subprocess.Popen(['pgrep', '-f', 'short_straddle'], stdout=subprocess.PIPE)
            stdout, _ = process.communicate()
            process.wait()

            # If pgrep returned any output, the cron job is running
            if stdout:
                print("Cronjob Running Successfully...!!")
            else:
                print("[Important] Cronjob Not Running please verify...!!")
                pushover("[Important] Cronjob Not Running please verify...!!")
        except Exception as e:
            print("Monitoring Error occurred:", e)
            pushover("Monitoring Error occurred:", e)


def pnlmetrics():
    exit_time = "15:15"
    current_time = time.strftime("%H:%M")
    if current_time >= exit_time:
        sys.exit(0)
    kite = autologin()
    swp_file = "{}/{}.json".format(config.get('default', 'LOG_DIR'), str(datetime.date.today()))

    if not os.path.isfile(swp_file):
        # Create orders
        sys.exit(0)
    else:
        with open(swp_file, 'r') as f:
            order_data = json.load(f)
    engine = create_engine(engine_url)
    CE_Trading_Signal = order_data['CE_Trading_Signal']
    PE_Trading_Signal = order_data['PE_Trading_Signal']
    positions = kite.positions()['net']
    banknifty_gap_percent = getGapPercent('NIFTY BANK', 'NSE', str(datetime.date.today() - datetime.timedelta(days=5)),
                                          str(datetime.date.today())).iloc[-1]['gapPercent']
    banknifty_price = kite.ltp('NSE:NIFTY BANK')['NSE:NIFTY BANK']['last_price']
    india_vix_price = kite.ltp('NSE:INDIA VIX')['NSE:INDIA VIX']['last_price']
    for pos in positions:
        if pos['tradingsymbol'] == CE_Trading_Signal:
            ce_traded_price = pos['sell_price']
            ce_quantity = pos['sell_quantity']
            ce_buyprice = pos['buy_price']
            ce_last_price = pos['last_price']
        if pos['tradingsymbol'] == PE_Trading_Signal:
            pe_traded_price = pos['sell_price']
            pe_buyprice = pos['buy_price']
            pe_quantity = pos['sell_quantity']
            pe_last_price = pos['last_price']

    if ce_buyprice == 0:
        ce_pnl = round((float(ce_traded_price) - float(kite.ltp(f'NFO:{CE_Trading_Signal}')[f'NFO:{CE_Trading_Signal}']['last_price'])) * int(ce_quantity), 2)
    else:
        ce_pnl = round((float(ce_traded_price) - float(ce_buyprice)) * int(ce_quantity),2)

    if pe_buyprice == 0:
        pe_pnl = round((float(pe_traded_price) - float(kite.ltp(f'NFO:{PE_Trading_Signal}')[f'NFO:{PE_Trading_Signal}']['last_price'])) * int(pe_quantity), 2)
    else:
        pe_pnl = round((float(pe_traded_price) - float(pe_buyprice)) * int(pe_quantity), 2)

    record = [{'date': datetime.datetime.now(), 'banknifty_price': banknifty_price,
               'banknifty_gap_percent': banknifty_gap_percent, 'ce_pnl': ce_pnl, 'pe_pnl': pe_pnl,
               'total_pnl': sum([ce_pnl, pe_pnl]), 'ce_quantity': ce_quantity, 'ce_price': ce_last_price,
               'ce_traded_price': ce_traded_price, 'pe_traded_price': pe_traded_price, 'pe_price': pe_last_price,
               'pe_quantity': pe_quantity, 'india_vix': india_vix_price}]
    df = pd.DataFrame(record)
    df.to_sql('backtest_metrics', con=engine, if_exists='append', index=False, method='multi')


def getATR(symbol, interval=15, duration=5):
    interval = f"{interval}minute"
    kite = autologin()
    instrument_df = pd.DataFrame(kite.instruments("NFO"))
    instrument = instrument_df[instrument_df.tradingsymbol==symbol].instrument_token.values[0]
    df = pd.DataFrame(kite.historical_data(instrument, datetime.date.today()-datetime.timedelta(duration), datetime.date.today(), interval))
    n = 20
    df['H-L']=abs(df['high']-df['low'])
    df['H-PC']=abs(df['high']-df['close'].shift(1))
    df['L-PC']=abs(df['low']-df['close'].shift(1))
    df['TR']=df[['H-L','H-PC','L-PC']].max(axis=1, skipna=False)
    df['ATR'] = df['TR'].ewm(com=n, min_periods=n).mean()
    ATR = round(df['ATR'].iloc[-1], 2)
    return ATR


# getATR("BANKNIFTY2362243500CE")
# scheduleHistoricalDump('BANKNIFTY', 'NFO-OPT', 'minute', profile='default')
# getHistoricalData((datetime.date.today() - datetime.timedelta(60)), datetime.date.today(), 'minute', 'BANKNIFTY',
#                   'NFO-OPT', profile='default')

# getGapPercent('INDIA VIX', 'NSE', '2023-04-05', '2023-05-09', profile='default')

# schedule_historical_data()
