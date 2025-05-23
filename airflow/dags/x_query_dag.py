from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def run_x_query():
    exec(open("C:/CryptoBot/x_query.py").read())

default_args = {"start_date": datetime(2025, 3, 4), "retries": 1}
dag = DAG("x_query_dag", default_args=default_args, schedule_interval="0 8 * * *")
task = PythonOperator(task_id="run_x_query", python_callable=run_x_query, dag=dag)