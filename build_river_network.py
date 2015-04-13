#!/usr/bin/python3
# -*- coding: utf8 -*-

import os
import sys
import re
import itertools
import traceback
import argparse

import pandas as pd
import numpy as np
import yaml

from river_orders.river import River, RiverSystems

if __debug__:
    pd.set_option("display.width", 160)
    _df = None
    _rs = None


def prepare(df):
    """
    Fixing most common bugs in the DataFrame with initial data
    """
    # 1. Splitting the id by two separate fields
    nan_values = np.delete(df.columns.values, 0)

    df.insert(0, "region", df[pd.isnull(df[nan_values]).all(1)]["id"])
    df["region"] = df["region"].ffill()

    df.insert(1, "river_id", df[~pd.isnull(df[nan_values]).all(1)]["id"])
    df = df[~pd.isnull(df["river_id"])]
    df.set_index(["region", "river_id"], inplace=True, drop=True)
    del df["id"]

    # 2. Fill downwards "»" values
    def _fill(col):
        df.loc[df[col] == "»", col] = np.nan
        df[col] = df[col].ffill()
    for col in ("river_dest", "side"):
        _fill(col)

    # 3. Convert strings to numbers
    def _str_to_numbers(col):
        df.loc[df[col] == "—", col] = np.nan
        df[col] = df[col].apply(float)
    for col in ("ten_km_trib_amount",):
        _str_to_numbers(col)

    return df


def construct(df, **kwargs):
    rs = RiverSystems(**kwargs)

    for index, r in df.iterrows():
        river = River(_name=r.river_full_name, index=index[1], **r)
        dest = River(_name=r.river_dest, index=index[1], **r)
        try:
            rs.add_river(river, dest)
        except Exception:
            print(traceback.format_exc())
            print(rs)
            sys.exit(1)
        else:
            print(index[1], *rs.active_system)

    return rs


def parse_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("datafile", help="Csv file with initial data",
                        type=str)
    parser.add_argument("-f", "--fixture", help="List of fixtures", type=str)
    args = parser.parse_args()
    return args


def main():
    options = parse_options()

    # main data
    df = prepare(pd.read_csv(options.datafile, sep=";"))

    # fixtures list
    if options.fixture:
        with open(options.fixture) as f:
            fixtures = yaml.load(f)
    else:
        fixtures = None

    rs = construct(df, fixtures=fixtures)

    if __debug__:
        global _df, _rs
        _df = df
        _rs = rs

    print("Current river systems: ")
    print(rs)
    rs.draw()


if __name__ == "__main__":
    main()
