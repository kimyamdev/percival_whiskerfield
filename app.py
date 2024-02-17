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
import os
import random
import sys
from types import FrameType
from flask import Flask
from utils.logging import logger

import aiohttp
import asyncio
import async_timeout
from flask import Flask, render_template, redirect, url_for, flash, jsonify
from ib_insync import *
import pandas as pd

from BQ_queries import test, latest_portfolio

from forex_python.converter import CurrencyRates

from datetime import datetime

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

    image_folder = './static/images'  # Ensure this path is correct
    images = os.listdir(image_folder)
    random_images = random.sample(images, 3)  # Pick 5 unique images at random
    image_paths = [f'./static/images/{image}' for image in random_images]  # Adjust if your path differs

    return render_template('home.html', image_paths=image_paths)

@app.route('/get-new-images')
def get_new_images():
    image_folder = './static/images'  # Ensure this path is correct
    images = os.listdir(image_folder)
    random_images = random.sample(images, 3)  # Pick 5 unique images at random
    image_paths = [f'./static/images/{image}' for image in random_images]  # Adjust if your path differs
    return jsonify(image_paths)


@app.route("/about")
def about():
    # Your birth date
    birth_date = datetime(year=1978, month=4, day=19)
    
    # Calculate the time difference in seconds and format it
    time_since_birth = (datetime.now() - birth_date).total_seconds()
    formatted_seconds = "{:,}".format(int(time_since_birth))

    # Format the birth date
    formatted_date = birth_date.strftime("%A, %d %B %Y")

    # Pass the formatted values to your template
    return render_template('about.html', formatted_date=formatted_date, formatted_seconds=formatted_seconds)

@app.route('/portfolio', methods=['GET', 'POST'])
def portfolio():
    
    merged_df = latest_portfolio()

    merged_df = merged_df.sort_values(by="ValueInSGD", ascending=False)

    # Convert DataFrame rows to a list of dictionaries for template iteration
    rows = [row.to_dict() for index, row in merged_df.iterrows()]

    def calculate_and_render_category_totals(category_column, merged_df):

        # Calculate the total value for each category in SGD
        category_totals_sgd = merged_df.groupby(category_column)['ValueInSGD'].sum().reset_index()
        category_totals_sgd = category_totals_sgd.rename(columns={category_column: 'Category'})  # Rename the column for clarity

        # Calculate the total value across all categories to find percentages
        total_value_sgd = category_totals_sgd['ValueInSGD'].sum()

        # Calculate the percentage of each category's total value relative to the overall total
        category_totals_sgd['Percentage'] = (category_totals_sgd['ValueInSGD'] / total_value_sgd) * 100

        # Ensure the DataFrame is formatted nicely for display
        category_totals_sgd = category_totals_sgd.round(2)
        category_totals_sgd = category_totals_sgd.sort_values(by="Percentage", ascending=False)

        # Convert DataFrame rows to a list of dictionaries for template iteration
        rows = [row.to_dict() for index, row in merged_df.iterrows()]

        return category_totals_sgd.to_dict('records'), rows

    # Example usage for different categories:
    super_asset_class_totals, super_asset_class_rows = calculate_and_render_category_totals('Super_Asset_Class', merged_df)
    custom_class_totals, custom_class_rows = calculate_and_render_category_totals('Custom_Class', merged_df)
    sector_totals, sector_rows = calculate_and_render_category_totals('Sector', merged_df)
    theme_totals, theme_rows = calculate_and_render_category_totals('Theme', merged_df)
    geography_totals, geography_rows = calculate_and_render_category_totals('Geography', merged_df)
    exchange_totals, exchange_rows = calculate_and_render_category_totals('exchange_x', merged_df)

    return render_template('portfolio.html',
                    rows=rows,
                    super_asset_class_totals=super_asset_class_totals, 
                    super_asset_class_rows=super_asset_class_rows,
                    custom_class_totals=custom_class_totals,
                    custom_class_rows=custom_class_rows,
                    sector_totals=sector_totals,
                    sector_rows=sector_rows,
                    theme_totals=theme_totals,
                    theme_rows=theme_rows,
                    exchange_totals=exchange_totals,
                    exchange_rows=exchange_rows,
                    geography_totals=geography_totals,
                    geography_rows=geography_rows,
                    )


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
