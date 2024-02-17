import pandas as pd
import pandas_gbq
from datetime import time
from google.cloud import bigquery
from google.oauth2 import service_account
import os

path = '/Users/philippezanetti/percival_whiskerfield/venv/bin/python3 /Users/philippezanetti/percival_whiskerfield/key_sql.json'
print(os.path.exists(path))

credentials = service_account.Credentials.from_service_account_file(path)
bqclient = bigquery.Client(credentials=credentials)
print(bqclient)
project_id = 'family-office-sheet'

def test():
    test = pandas_gbq.read_gbq(
        '''
        SELECT *

        FROM `family-office-sheet.Consolidated.Test_Stocks_Meta` as stocks_meta


        ''', project_id=project_id, credentials=credentials
    )
    return test

def latest_portfolio():
    latest_portfolio = pandas_gbq.read_gbq(
        '''
        WITH RankedPositions AS (
            SELECT *,
                   ROW_NUMBER() OVER(PARTITION BY IB_ticker, exchange_x ORDER BY Datetime DESC) AS Rank
            FROM `family-office-sheet.Consolidated.Positions`
        )
        SELECT *
        FROM RankedPositions
        WHERE Rank = 1
        ''',
        project_id=project_id, credentials=credentials
    )
    return latest_portfolio
