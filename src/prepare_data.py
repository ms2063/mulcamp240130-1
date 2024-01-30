import os
import shutil

import pandas as pd
import urllib.request
from loguru import logger
import numpy as np
from datetime import date, datetime, timedelta, time
from tqdm import tqdm


def download_file(directory, filename):
    url = f"https://github.com/khanhnamle1994/instacart-orders/raw/master/data/{filename}?download="
    logger.debug(f"Downloading {filename}...")
    urllib.request.urlretrieve(url, os.path.join(directory, filename))


def add_total_number_of_days(df):
    df_total_nb_days = df.groupby("user_id").days_since_prior_order.sum().reset_index().rename(
        columns={"days_since_prior_order": "total_days_on_platform"})
    df_total_nb_days['user_id'] = df_total_nb_days['user_id'].astype(int)
    df = pd.merge(df, df_total_nb_days, on=["user_id"])
    return df


def add_dates(df):
    dates = []
    dates_hour = []

    hour_of_day = df["order_hour_of_day"].to_list()
    delta_days = df["days_since_prior_order"].to_list()
    total_days = df["total_days_on_platform"].to_list()

    for day, total_day in tqdm(zip(delta_days, total_days), total=len(df), position=0, leave=True):
        if (np.isnan(day)):
            dates.append(date(2023, 10, 1) - timedelta(days=total_day))
        else:
            dates.append(dates[-1] + timedelta(days=day))

    for hour, date_ in tqdm(zip(hour_of_day, dates), total=len(df), position=0, leave=True):
        dates_hour.append(datetime.combine(date_, time(hour, 0)))

    df["datetime"] = dates_hour
    df["date"] = dates
    return df


def prepare_orders_df(df_orders, df_order_products):
    df_orders = df_orders[df_orders["eval_set"] == "prior"]
    df_order_products = df_order_products.groupby("order_id")["product_id"].apply(list).to_frame().reset_index()
    df = df_orders.merge(df_order_products, on=["order_id"])

    df = add_total_number_of_days(df)
    df = add_dates(df)

    df["basket_size"] = df["product_id"].apply(len)
    return df


def save_weekly_orders(df_orders):
    last_date, first_date = df["date"].max(), df["date"].min()

    logger.debug(f"Saving weekly orders...")

    for i in tqdm(range(int((last_date - first_date).days/7))):
        week_end = last_date
        week_start = week_end - timedelta(days=7)
        df_to_save = df[(df["date"] <= week_end) & (df["date"] > week_start)]
        filename = f"../data/processed/orders_{str(df_to_save['date'].max())}_{str(df_to_save['date'].min())}.zip"
        df_to_save.to_csv(filename, compression={'method': 'zip', 'archive_name': 'orders.csv'})
        last_date = week_start


if __name__ == "__main__":
    files = ["order_products__prior.csv", "orders.csv", "products.csv", "aisles.csv", "departments.csv"]
    logger.debug(f"Downloading {len(files)} files")

    shutil.rmtree('../data', ignore_errors=True)
    os.mkdir("../data")
    os.mkdir("../data/raw")
    os.mkdir("../data/processed")

    for file in files:
        download_file(directory="../data/raw", filename=file)

    # Process df_orders
    logger.debug(f"Processing df_orders")
    df_order_products = pd.read_csv("../data/raw/order_products__prior.csv")
    df_orders = pd.read_csv("../data/raw/orders.csv")

    df = prepare_orders_df(df_orders, df_order_products)
    save_weekly_orders(df)

    # Process df_new_users
    logger.debug(f"Processing df_new_users")
    df_new_users = df[df["order_number"] == 1][["user_id", "date"]
                                               ].sort_values(["date", "user_id"]).reset_index(drop=True)
    df_new_users.to_csv("../data/processed/new_users.zip",
                        compression={'method': 'zip', 'archive_name': 'new_users.csv'})

    # Process df_engagement
    logger.debug(f"Processing df_new_users")
    df_new_users = df[["user_id", "days_since_prior_order"]].sort_values(
        ["days_since_prior_order", "user_id"]).reset_index(drop=True)
    df_new_users.to_csv("../data/processed/engagement.zip",
                        compression={'method': 'zip', 'archive_name': 'engagement.csv'})

    # Process df_retention
    logger.debug(f"Processing df_retention")
    df_retention = df[["user_id", "date"]].sort_values(["date", "user_id"]).reset_index(drop=True)
    df_retention.to_csv("../data/processed/retention.zip",
                        compression={'method': 'zip', 'archive_name': 'retention.csv'})

    # Process df_volumes
    logger.debug(f"Processing df_volumes")
    df_volumes = df.groupby("date").agg(order_number=("order_number", "count"),
                                        basket_size=("basket_size", "sum")).reset_index()
    df_volumes.to_csv("../data/processed/volumes.zip", compression={'method': 'zip', 'archive_name': 'volumes.csv'})

    # Process df_users
