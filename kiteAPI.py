import configparser
import os
import time

import requests
from pyotp import TOTP
from kiteconnect import KiteConnect
import kiteconnect
import json
import pandas as pd
import datetime
import dateutil
import pkg_resources
import http.client, urllib
import sqlite3
import django
from pathlib import Path

# Load Config file
config = configparser.ConfigParser()
config_file = pkg_resources.resource_filename('config', 'config.ini')
# config_file = "/Users/siddhu/IdeaProjects/config.ini"
config.read(config_file)

# db = sqlite3.connect(f"{Path(__file__).resolve().parent}/db.sqlite3")
DB_File = f"{Path(__file__).resolve().parent}/db.sqlite3"
db = sqlite3.connect(DB_File)
django.setup()


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
    vix_df = pd.DataFrame(kite.historical_data(vix_token, from_date, to_date, "minute"))
    vix_df.set_index('date', inplace=True)
    vix_df.to_sql('backtest_indiavix', db, if_exists='replace')
    vix_df = vix_df.rename(columns={'open': 'vix_open', 'high': 'vix_high', 'low': 'vix_low', 'close': 'vix_close',
                                    'volume': 'vix_volume'})

    # BankNifty Index
    bn_token = nse_df[nse_df.tradingsymbol == 'NIFTY BANK'].iloc[0].instrument_token
    bn_df = pd.DataFrame(kite.historical_data(bn_token, from_date, to_date, "minute"))
    bn_df.set_index('date', inplace=True)
    bn_df.to_sql('backtest_bankniftyindex', db, if_exists='replace')

    # Nifty Index
    nf_token = nse_df[nse_df.tradingsymbol == 'NIFTY 50'].iloc[0].instrument_token
    nf_df = pd.DataFrame(kite.historical_data(nf_token, from_date, to_date, "minute"))
    nf_df.set_index('date', inplace=True)
    nf_df.to_sql('backtest_niftyindex', db, if_exists='replace')

    # FINNifty Index
    fn_token = nse_df[nse_df.tradingsymbol == 'NIFTY FIN SERVICE'].iloc[0].instrument_token
    fn_df = pd.DataFrame(kite.historical_data(fn_token, from_date, to_date, "minute"))
    fn_df.set_index('date', inplace=True)
    fn_df.to_sql('backtest_finniftyindex', db, if_exists='replace')

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
            data = pd.DataFrame(kite.historical_data(instrument, from_date, to_date, timeframe, oi=True))
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
        BN_OPT_df.set_index('date', inplace=True)
        BN_OPT_df = BN_OPT_df.sort_values(by='date')
        Final_df = pd.concat([BN_OPT_df, vix_df], axis=1)
        Final_df.to_sql(table, db, if_exists='replace')


def schedule_historical_data():
    today_date = datetime.date.today()
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


# scheduleHistoricalDump('BANKNIFTY', 'NFO-OPT', 'minute', profile='default')
# getHistoricalData((datetime.date.today() - datetime.timedelta(60)), datetime.date.today(), 'minute', 'BANKNIFTY',
#                   'NFO-OPT', profile='default')

# getGapPercent('INDIA VIX', 'NSE', '2023-04-05', '2023-05-09', profile='default')

# schedule_historical_data()
