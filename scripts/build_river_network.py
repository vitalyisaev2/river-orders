#!/usr/bin/python
# -*- coding: utf8 -*-

import sys

import pandas as pd
import numpy as np

pd.set_option('display.width', 160)

if __debug__:
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
        df.loc[df[col]=='»', col] = np.nan
        df[col] = df[col].ffill()
    map(_fill, ('river_dest','side'))

    # Short names
    def _get_main_name(name):
        assert(all(c in name for c in ('(',')')) or all(c not in name for c in ('(',')')))
        if "(" in name:
            return name.split("(")[0].strip()
        else:
            return name

    df.insert(0, 'river_main_name', df['river_full_name'].apply(_get_main_name))

    return df


def construct(df):
    stack = []
    for index, row in df.iterrows():
        river_curr = row['river_main_name']
        dest_curr = row['river_dest']
        if len(stack) == 0:
            stack.append(dest)
        else:



def main():
    if __debug__:
        global _df
    fname = sys.argv[1]
    df = pd.read_csv(fname, sep=';')

    df = prepare(df)
    _df = df

if __name__ == "__main__":
    main()
