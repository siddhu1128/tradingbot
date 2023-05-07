import datetime
import pandas as pd
import configparser
import os

# Load Config file
config = configparser.ConfigParser()
config_file = os.path.join(os.path.dirname(__file__), 'config', 'config.ini')
# config_file = "/Users/siddhu/IdeaProjects/config.ini"
config.read(config_file)


def short_straddle(signal, timeframe='minute', exchange='NFO-OPT',
                   from_date=(datetime.date.today() - datetime.timedelta(60)), to_date=datetime.date.today(),
                   entry_time='09:15:00', exit_time='15:29:00', stoploss=20,
                   trailing_stoploss=None, target=None, profile='default'):
    input_date = datetime.datetime.strptime(str(from_date), '%Y-%m-%d')
    to_date = datetime.datetime.strptime(str(to_date), '%Y-%m-%d')
    if signal == 'BANKNIFTY':
        expiry_day = 3
    DUMP_FILE_LOCATION = config.get(profile, 'DATA_FILE_LOCATION')
    while input_date <= to_date:
        # Compute the number of days until the next Thursday (3 = Thursday)
        days_until_expiry = (expiry_day - input_date.weekday()) % 7
        # Add the number of days until the next Thursday to the input date
        expiry_date = input_date + datetime.timedelta(days=days_until_expiry)
        # Get historical data from dumps
        DUMP_FILE = f"{DUMP_FILE_LOCATION}/{signal}_{exchange}_{timeframe}_{input_date.year}.csv"
        if os.path.isfile(DUMP_FILE):
            historical_df = pd.read_csv(DUMP_FILE)
            available_start_date = historical_df.iloc[1]['date']
            date_format = '%Y-%m-%d %H:%M:%S%z'
            available_date = datetime.datetime.strptime(available_start_date, date_format).date()
            if available_date > from_date:
                print("Data not available, Data available from {}".format(available_start_date))
            else:
                # strategy code here
                historical_df
        else:
            print("Dump file not available")
            exit(1)

short_straddle('BANKNIFTY')