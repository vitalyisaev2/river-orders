#!/usr/bin/python
# -*- coding: utf8 -*-

import sys
import re

import pandas as pd
import numpy as np

pd.set_option('display.width', 160)

if __debug__:
    _df = None

class RiverStack(list):
    patterns = [
        ur'^протока р. ([а-яА-Я-]+)$',
    ]
    def __init__(self):
        self.rivers = []

    def __str__(self):
        return "<-".join(self.rivers)

    def __getitem__(self, index):
        return self.rivers[index]

    def __len__(self):
        return len(self.rivers)

    def push(self, item):
        return self.rivers.append(item)

    def pop(self):
        return self.rivers.pop()

    def __contains__(self, dest):
        for river in self.rivers:
            if dest == river:
                return True

        unicode_rivers = [r.decode('utf8') for r in self.rivers]

        for pattern in self.patterns:
            m = re.search(pattern, dest.decode('utf8'))
            if m:
                name = m.groups()[0]
                #exists = name in self.rivers
                exists = name in unicode_rivers
                print(u"\t'{}' -> '{}'; exists: {}".format(pattern, name, exists))
                if exists:
                    return True


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
    map(_fill, ('river_dest', 'side'))

    # Short names
    def _get_main_name(name):
        assert(all(c in name for c in ('(', ')')) or all(c not in name for c in ('(', ')')))
        if "(" in name:
            return name.split("(")[0].strip()
        else:
            return name

    df.insert(0, 'river_main_name', df['river_full_name'].apply(_get_main_name))

    return df


def construct(df):
    stack = RiverStack()
    for index, row in df.iterrows():
    #for index, row in list(df.iterrows())[:20]:
        river = row['river_main_name']
        dest = row['river_dest']

        # start point
        if len(stack) == 0:
            stack.push(dest)
            stack.push(river)
        else:
            assert dest in stack, "'{}' not in {}".format(dest, stack)
            while dest != stack[-1]:
                print stack
                stack.pop()
            stack.push(river)

        print index[1], len(stack), stack


def main():
    fname = sys.argv[1]
    df = pd.read_csv(fname, sep=';')
    df = prepare(df)

    if __debug__:
        global _df
        _df = df

    construct(df)

if __name__ == "__main__":
    main()
