from django.db import models


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


class BankniftyIndex(models.Model):
    date = models.DateTimeField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.IntegerField()


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


class NiftyIndex(models.Model):
    date = models.DateTimeField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.IntegerField()


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


class FinniftyIndex(models.Model):
    date = models.DateTimeField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.IntegerField()


class IndiaVix(models.Model):
    date = models.DateTimeField()
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.IntegerField()



