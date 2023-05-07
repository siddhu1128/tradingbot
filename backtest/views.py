from django.shortcuts import render


# Create your views here.
def backtest(request):
    return render(request, 'backtest/backtest.html')
