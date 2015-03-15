#!/usr/bin/python
# -*- coding: utf8 -*-

import sys

import pandas as pd
import numpy as np

if __debug__:
    df = None

def fill_repeats(df):
    def _fill(col):
        df.loc[df[col]=='»', col] = np.nan
        df[col] = df[col].ffill()

    map(_fill, ('river_dest','side'))

def main():
    if __debug__:
        global df
    fname = sys.argv[1]
    df = pd.read_csv(fname)

    fill_repeats(df)

if __name__ == "__main__":
    main()
