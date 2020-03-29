#!/usr/bin/python
"""Module for prediction stock prices."""
import random
from fbprophet import Prophet
import pandas as pd

class ProphetForcasting:

    def __init__(self, stock):
        self.stock = stock
        self.historic_stock_prices = []

    def storing_data(self):
        """Gather data every 30 sec and store it in a list"""
        latest_stock_price = random.randint(80, 100)
        self.historic_stock_prices.append(latest_stock_price)

    def make_prediction(self):
        """Make prediction if thre."""
        pass
