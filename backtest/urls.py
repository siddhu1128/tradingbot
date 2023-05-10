from django.urls import path
from .views import *

urlpatterns = [
    path('', backtest, name='backtest'),
]