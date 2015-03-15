#!/usr/bin/python
# -*- coding: utf8 -*-

import sys

import pandas as pd
import numpy as np

pd.set_option('display.width', 160)

if __debug__:
    _df = None


def indexing(df):
    # Splitting the id by two separate fields
    nan_values = np.delete(df.columns.values, 0)

    df.insert(0, 'region', df[pd.isnull(df[nan_values]).all(1)]['id'])
    df['region'] = df['region'].ffill()

    df.insert(1, 'river_id', df[~pd.isnull(df[nan_values]).all(1)]['id'])
    df = df[~pd.isnull(df['river_id'])]

    df.set_index(['region', 'river_id'], inplace=True, drop=True)
    del df['id']
    return df


def fill_repeats(df):
    """
    Заполняет знаки повтора
    """
    def _fill(col):
        df.loc[df[col]=='»', col] = np.nan
        df[col] = df[col].ffill()

    map(_fill, ('river_dest','side'))
    return df


def main():
    if __debug__:
        global _df
    fname = sys.argv[1]
    df = pd.read_csv(fname, sep=';')

    df = indexing(df)
    df = fill_repeats(df)
    _df = df

if __name__ == "__main__":
    main()
