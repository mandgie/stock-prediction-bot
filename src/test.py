#!/usr/bin/python
"""Test environment for checking Prophet class."""

from botify import ProphetForcasting

stock_classifier = ProphetForcasting("erc")

for nr in range(20):
    stock_classifier.storing_data()

print(stock_classifier.historic_stock_prices)
