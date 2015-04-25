#!/usr/bin/python3
# -*- coding: utf8 -*-

import sys
import traceback
import argparse
import logging
from itertools import chain
from datetime import datetime

import pandas as pd
import numpy as np
import yaml

from river_orders.build import WaterObject, RiverSystems

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
    df.set_index(["volume", "river_id"], inplace=True, drop=True)
    del df["id"]

    # 2. Fill downwards "»" values
    def _fill(col):
        df.loc[[x in ("«", "»") for x in df[col]], col] = np.nan
        df[col] = df[col].ffill()
    for col in ("river_dest", "side"):
        _fill(col)

    # 3. Convert strings to numbers
    def _str_to_numbers(col):
        print("Transforming '{}'...".format(col))
        try:
            df.loc[df[col] == "—", col] = np.nan
            df.loc[df[col] == "-", col] = np.nan
        except Exception as e:
            print(col, e)
        df[col] = df[col].apply(float)
    for col in ("ten_km_trib_amount", "length", "dest_from_end"):
        _str_to_numbers(col)

    return df


def construct(df, **kwargs):
    rss = RiverSystems(**kwargs)

    for index, r in df.iterrows():
        volume = index[0]
        assert(isinstance(volume, str)), "{}: wrong volume: {}".format(r, volume)

        river = WaterObject(_name=r.river_full_name, volume=volume, index=index[1], **r)
        dest = WaterObject(_name=r.river_dest)
        try:
            rss.add_river(river, dest)
        except Exception:
            print(traceback.format_exc())
            print(rss)
            sys.exit(1)
        else:
            message = " ".join(str(m) for m in chain(index, rss.active_system))
            logging.debug(message)

    return rss


def parse_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("datafile", help="CSV file with initial data",
                        type=str)
    parser.add_argument("-f", "--fixture", help="List of fixtures", type=str)
    parser.add_argument("-N", "--node", help="Name of node to draw separate network from", type=str)
    args = parser.parse_args()
    return args


def main():
    # Prepare data
    options = parse_options()

    # Set logger
    prefix = options.datafile.split(".")[0]
    tstamp = datetime.now().strftime("%Y%m%d-%H:%M")
    fname = prefix + "-" + tstamp + ".log"
    logging.basicConfig(filename=fname, level=logging.DEBUG)

    # main data
    df = prepare(pd.read_csv(options.datafile, sep=";"))

    # fixtures list
    if options.fixture:
        with open(options.fixture) as f:
            fixtures = yaml.load(f)
    else:
        fixtures = None

    # Build multiple river systems from initial data
    rss = construct(df, fixtures=fixtures)
    if __debug__:
        global _df, _rss
        _df = df
        _rss = rss
        print(rss)

    # Draw selected part of river_network. If nothing selected, draw everything
    if options.node:
        rss.render(options.node)
    else:
        rss.render()


if __name__ == "__main__":
    main()
