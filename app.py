# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import signal
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

app = Flask(__name__)

async def fetch_positions():
    ib = IB()
    await ib.connectAsync('127.0.0.1', 7496, clientId=1)
    positions = ib.positions()
    print(positions)
    ib.disconnect()
    return positions

#Correctly defined function to fetch positions and their latest prices
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

@app.route("/")
def hello():


    return render_template('home.html')

@app.route('/portfolio', methods=['GET', 'POST'])
async def portfolio():
    print("START ASYNC 2")
    positions = await fetch_positions()
    # print(positions)
    # data = pd.read_csv('./data/U7889772_20230703_20240209.csv', delimiter='\t')

    # print(data)
    # Fetch positions including the latest price
    positions_with_prices = await fetch_positions_and_prices()

    # # Convert the list of position dictionaries to a DataFrame
    df = pd.DataFrame(positions_with_prices)

    # Convert DataFrame rows to a list of dictionaries for template iteration
    rows = [row.to_dict() for index, row in df.iterrows()]


    return render_template('portfolio.html', rows=rows)


def shutdown_handler(signal_int: int, frame: FrameType) -> None:
    logger.info(f"Caught Signal {signal.strsignal(signal_int)}")

    from utils.logging import flush

    flush()

    # Safely exit program
    sys.exit(0)


if __name__ == "__main__":
    # Running application locally, outside of a Google Cloud Environment

    # handles Ctrl-C termination
    signal.signal(signal.SIGINT, shutdown_handler)

    app.run(host="localhost", port=8080, debug=True)
else:
    # handles Cloud Run container termination
    signal.signal(signal.SIGTERM, shutdown_handler)
