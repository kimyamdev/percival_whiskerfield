import signal
import os
import random
import sys
from types import FrameType
from flask import Flask
from utils.logging import logger
import aiohttp
import asyncio
import async_timeout
from flask import Flask, render_template, redirect, url_for, flash
from ib_insync import *
import pandas as pd
from BQ_queries import test, latest_portfolio
from forex_python.converter import CurrencyRates
from datetime import datetime

async def fetch_positions_and_prices():
    print("START ASYNC")
    ib = IB()
    await ib.connectAsync('127.0.0.1', 7496, clientId=1)

    positions = ib.positions()
    positions_with_prices = []

    for pos in positions:
        # Request market data
        contract = pos.contract
        ib.reqMktData(contract, '', False, False)
        await asyncio.sleep(1)  # Small delay to ensure the market data request is processed

        # Assuming market data has been received, access it
        market_data = ib.ticker(contract)
        last_price = market_data.marketPrice()

        positions_with_prices.append({
            'account': pos.account,
            'symbol': contract.symbol,
            'exchange': contract.exchange,
            'currency': contract.currency,
            'position': pos.position,
            'averageCost': pos.avgCost,
            'latestPrice': last_price
        })

    ib.disconnect()
    return positions_with_prices

async def fetch_portfolio_df():
    positions_with_prices = await fetch_positions_and_prices()
    # Convert the list of position dictionaries to a DataFrame
    positions_df = pd.DataFrame(positions_with_prices)
    # Renaming the column in positions_df to match the df for a seamless merge
    positions_df.rename(columns={'symbol': 'IB_Ticker'}, inplace=True)
    latest_portfolio_df = latest_portfolio()

    # Performing an inner join on the IB_Ticker column
    merged_df = pd.merge(latest_portfolio_df, positions_df, on='IB_Ticker', how='inner')

    c = CurrencyRates()

    def fetch_exchange_rate(currency):
        return c.get_rate(currency, 'SGD')

    print(f"Test FX USD: {fetch_exchange_rate('USD')}")

    # Adjust amounts for GBP and convert all values to SGD
    merged_df['Position_Amount'] = merged_df['position'] * merged_df['latestPrice']
    merged_df['ValueInSGD'] = merged_df.apply(lambda x: x['Position_Amount'] if x['currency'] == 'SGD' else (x['Position_Amount'] / 100 if x['currency'] == 'GBP' else x['Position_Amount']) * fetch_exchange_rate(x['currency']), axis=1)
    merged_df['Weight'] = merged_df['ValueInSGD'] / merged_df['ValueInSGD'].sum()
    merged_df = merged_df.sort_values(by="ValueInSGD", ascending=False)
    return merged_df
