from django.db import models


# from django.apps import AppConfig
#
#
# class BacktestConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'backtest'
#
#     def ready(self):
#         from . import models  # Importing here to avoid circular imports
#
#         # Call your function or method that accesses the app registry here
#         models.do_something()


# Create your models here.
class BankniftyOptions(models.Model):
    # date,instrument_token,exchange_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,instrument_type,segment,exchange,open,high,low,close,volume,oi,vix_open,vix_high,vix_low,vix_close,vix_volume
    date = models.DateTimeField()
    instrument_token = models.IntegerField()
    exchange_token = models.IntegerField()
    tradingsymbol = models.CharField(max_length=250)
    name = models.CharField(max_length=250)
    last_price = models.FloatField()
    expiry = models.CharField(max_length=250)
    strike = models.FloatField()
    tick_size = models.FloatField()
    lot_size = models.IntegerField()
    instrument_type = models.CharField(max_length=250)
    segment = models.CharField(max_length=250)
    exchange = models.CharField(max_length=250)
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.IntegerField()
    oi = models.IntegerField()
    vix_open = models.FloatField()
    vix_high = models.FloatField()
    vix_low = models.FloatField()
    vix_close = models.FloatField()
    vix_volume = models.IntegerField()

    class Meta:
        app_label = 'backtest'


class BankniftyIndex(models.Model):
    date = models.DateTimeField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.IntegerField()

    class Meta:
        app_label = 'backtest'


class NiftyOptions(models.Model):
    # date,instrument_token,exchange_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,instrument_type,segment,exchange,open,high,low,close,volume,oi,vix_open,vix_high,vix_low,vix_close,vix_volume
    date = models.DateTimeField()
    instrument_token = models.IntegerField()
    exchange_token = models.IntegerField()
    tradingsymbol = models.CharField(max_length=250)
    name = models.CharField(max_length=250)
    last_price = models.FloatField()
    expiry = models.CharField(max_length=250)
    strike = models.FloatField()
    tick_size = models.FloatField()
    lot_size = models.IntegerField()
    instrument_type = models.CharField(max_length=250)
    segment = models.CharField(max_length=250)
    exchange = models.CharField(max_length=250)
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.IntegerField()
    oi = models.IntegerField()
    vix_open = models.FloatField()
    vix_high = models.FloatField()
    vix_low = models.FloatField()
    vix_close = models.FloatField()
    vix_volume = models.IntegerField()

    class Meta:
        app_label = 'backtest'


class NiftyIndex(models.Model):
    date = models.DateTimeField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.IntegerField()

    class Meta:
        app_label = 'backtest'


class FinniftyOptions(models.Model):
    # date,instrument_token,exchange_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,instrument_type,segment,exchange,open,high,low,close,volume,oi,vix_open,vix_high,vix_low,vix_close,vix_volume
    date = models.DateTimeField()
    instrument_token = models.IntegerField()
    exchange_token = models.IntegerField()
    tradingsymbol = models.CharField(max_length=250)
    name = models.CharField(max_length=250)
    last_price = models.FloatField()
    expiry = models.CharField(max_length=250)
    strike = models.FloatField()
    tick_size = models.FloatField()
    lot_size = models.IntegerField()
    instrument_type = models.CharField(max_length=250)
    segment = models.CharField(max_length=250)
    exchange = models.CharField(max_length=250)
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.IntegerField()
    oi = models.IntegerField()
    vix_open = models.FloatField()
    vix_high = models.FloatField()
    vix_low = models.FloatField()
    vix_close = models.FloatField()
    vix_volume = models.IntegerField()

    class Meta:
        app_label = 'backtest'


class FinniftyIndex(models.Model):
    date = models.DateTimeField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.IntegerField()

    class Meta:
        app_label = 'backtest'


class IndiaVix(models.Model):
    date = models.DateTimeField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.IntegerField()

    class Meta:
        app_label = 'backtest'
        # unique_together = ["date", "open", "high", "low", "close", "volume"]


class ShortStraddle(models.Model):
    # Date', 'Day', 'Signal', 'ATM', 'Expiry_Date', 'SL_Percent', 'TSL_Percent',
    #              'CE_Entry_Time', 'CE_Entry_Price', 'CE_Quantity', 'CE_Order_Id', 'CE_Stoploss_Order_Id', 'CE_SL_Hit',
    #              'CE_TSL_Hits', 'CE_Exit_Price', 'CE_Exit_Time', 'CE_pnl',
    #              'PE_Entry_Time', 'PE_Entry_Price', 'PE_Quantity', 'PE_Order_Id', 'PE_Stoploss_Order_Id', 'PE_SL_Hit',
    #              'PE_TSL_Hits', 'PE_Exit_Price', 'PE_Exit_Time', 'PE_pnl',
    #              'Total_pnl', 'Win/Loss', 'max_profit', 'max_profit_time'
    Date = models.DateTimeField()
    Day = models.DateTimeField()
    Signal = models.CharField(max_length=250)
    ATM = models.FloatField()
    Expiry_Date = models.DateTimeField()
    SL_Percent = models.IntegerField()
    TSL_Percent = models.IntegerField()
    CE_Entry_Time = models.DateTimeField()
    CE_Entry_Price = models.FloatField()
    CE_Quantity = models.IntegerField()
    CE_Order_Id = models.IntegerField()
    CE_Stoploss_Order_Id = models.IntegerField()
    CE_SL_Hit = models.CharField(max_length=250)
    CE_TSL_Hits = models.CharField(max_length=250)
    CE_Exit_Price = models.FloatField()
    CE_Exit_Time = models.DateTimeField()
    CE_pnl = models.FloatField()
    PE_Entry_Time = models.DateTimeField()
    PE_Entry_Price = models.FloatField()
    PE_Quantity = models.IntegerField()
    PE_Order_Id = models.IntegerField()
    PE_Stoploss_Order_Id = models.IntegerField()
    PE_SL_Hit = models.CharField(max_length=250)
    PE_TSL_Hits = models.CharField(max_length=250)
    PE_Exit_Price = models.FloatField()
    PE_Exit_Time = models.DateTimeField()
    PE_pnl = models.FloatField()
    Total_pnl = models.FloatField()
    Win_Loss = models.CharField(max_length=250)
    max_profit = models.FloatField()
    max_profit_time = models.DateTimeField()

    class Meta:
        app_label = 'backtest'
