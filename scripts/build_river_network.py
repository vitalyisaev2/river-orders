#!/usr/bin/python3
# -*- coding: utf8 -*-

import sys
import re
import itertools

import pandas as pd
import numpy as np

pd.set_option('display.width', 160)

if __debug__:
    _df = None

class RiverNotFoundInStack(Exception):
    def __init__(self, stack, river):
        self.stack = stack
        self.river = river

class RiverStack(list):
    #patterns = [
        #r'^протока р. ([а-яА-Я-]+)$',
    #]
    def __init__(self):
        self.rivers = []
        self.rs = RiverSuggestion()

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
        if dest in self.rivers:
            return True
        else:
            print("'{}' not in {}".format(dest, str(self)))
            return False

    def find_similar(self, dest):
        for name in self.rs.suggest(dest):
            exists = name in self.rivers
            print("\t'{}' <-> '{}'; exists: {}".format(dest, name, exists))
            if exists:
                return name


class RiverSuggestion(object):
    _substrings = [
        r'^протока р. ([а-яА-Я-]+)$',
    ]
    _replacements = [
        (r"\.", ". ")
    ]

    def __init__(self):
        self.substrings = list(
            map(re.compile, self._substrings))
        self.replacements = list(
            map(lambda x: (re.compile(x[0]), x[1]), self._replacements))

    def suggest(self, river):
        subs = (m.groups()[0] for m in map(lambda x: x.match(river), self.substrings) if m)
        repls = (r[0].sub(r[1], river) for r in self.replacements)
        return itertools.chain(subs, repls)


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
        river = row['river_main_name']
        dest = row['river_dest']

        # start point
        if len(stack) == 0:
            stack.push(dest)
            stack.push(river)
        else:
            if not dest in stack:
                similar = stack.find_similar(dest)
                if __debug__:
                    print("\tSuggesting '{}' instead of '{}'".format(similar, dest))
                if not similar in stack:
                    raise RiverNotFoundInStack(stack, dest)
                else:
                    dest = similar

            while dest != stack[-1]:
                #print(stack)
                stack.pop()

            stack.push(river)

        print(index[1], len(stack), stack)


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
