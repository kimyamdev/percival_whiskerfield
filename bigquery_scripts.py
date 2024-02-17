from google.cloud import bigquery
import pandas as pd
from ib_insync_scripts import fetch_portfolio_df
import asyncio
from datetime import datetime

import pandas as pd
import pandas_gbq
from datetime import time
from google.cloud import bigquery
from google.oauth2 import service_account

import os

path = '/Users/philippezanetti/percival_whiskerfield/key_sql.json'
print(os.path.exists(path))


try:
    credentials = service_account.Credentials.from_service_account_file(path)
    print(credentials)
except Exception as e:
    print(f"An error occurred: {e}")


# Replace 'your_table_id' with your table ID
project_id = 'family-office-sheet'
dataset_id = 'Consolidated'
table_id = 'Positions'
table_full_path = f"{project_id}.{dataset_id}.{table_id}"

# Assuming 'df' is your DataFrame
# Make sure your DataFrame matches the schema in BigQuery

df = asyncio.run(fetch_portfolio_df())

print(df.columns)

def send_to_bigquery(df):
    bool_columns = df.select_dtypes(include=['bool']).columns
    df[bool_columns] = df[bool_columns].astype(str)
    df['Datetime'] = datetime.now()
    client = bigquery.Client(project=project_id, credentials=credentials)
    job_config = bigquery.LoadJobConfig()
    job_config.write_disposition = bigquery.WriteDisposition.WRITE_APPEND  # Append to the existing table
    job_config.autodetect = True  # Auto-detect the schema

    load_job = client.load_table_from_dataframe(
        df, table_full_path, job_config=job_config
    )  # Make an API request.
    load_job.result()  # Wait for the job to complete.

    print(f"Dataframe appended to {table_full_path} successfully.")

Example: send_to_bigquery(df)
