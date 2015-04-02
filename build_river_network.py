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
    pd.set_option('display.width', 160)
    _df = None


def prepare(df):
    # Splitting the id by two separate fields
    nan_values = np.delete(df.columns.values, 0)

    df.insert(0, 'region', df[pd.isnull(df[nan_values]).all(1)]['id'])
    df['region'] = df['region'].ffill()

    df.insert(1, 'river_id', df[~pd.isnull(df[nan_values]).all(1)]['id'])
    df = df[~pd.isnull(df['river_id'])]
    df.set_index(['region', 'river_id'], inplace=True, drop=True)
    del df['id']

    # Fill downwards "»" values
    def _fill(col):
        df.loc[df[col] == '»', col] = np.nan
        df[col] = df[col].ffill()

    for col in ('river_dest', 'side'):
        _fill(col)

    return df


def construct(df, **kwargs):
    rs = RiverSystems(**kwargs)

    for index, row in df.iterrows():
        river = River(row['river_full_name'], index[1])
        dest = River(row['river_dest'], index[1])
        try:
            rs.add_river(river, dest)
        except Exception:
            print(traceback.format_exc())
            print(rs)
            # import pdb; pdb.set_trace()
            sys.exit(1)
        else:
            print(index[1], *rs.active_system)

    return rs


def parse_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("datafile", help="Csv file with initial data",
                        type=str)
    parser.add_argument("-f", "--fixture",
                        help="List of fixtures",
                        type=str)
    args = parser.parse_args()
    return args


def main():
    options = parse_options()

    # main data
    df = pd.read_csv(options.datafile, sep=';')
    df = prepare(df)

    # fixtures list
    if os.path.isfile(options.fixture):
        with open(options.fixture) as f:
            fixtures = yaml.load(f)
    else:
        fixtures = None

    if __debug__:
        global _df
        _df = df

    rs = construct(df, fixtures=fixtures)
    print(rs)

if __name__ == "__main__":
    main()
