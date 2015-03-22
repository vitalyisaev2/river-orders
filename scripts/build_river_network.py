#!/usr/bin/python3
# -*- coding: utf8 -*-

import sys
import re
import itertools
import traceback
import pprint

import pandas as pd
import numpy as np

pd.set_option('display.width', 160)

if __debug__:
    _df = None


class NameSuggestion(object):
    _substrings = [
        r'^протока р. ([а-яА-Я-]+)$',
        r'^(оз.\s+[а-яА-Я-]+)\s+\(зал.\s+[а-яА-Я-]+\)$',
        r'^(оз.\s+[а-яА-Я-]+)\s+\([а-яА-Я-]+\s+залив\)$'
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
        """
        Provides the set of unique suggested names, according to the list with
        regular expressions
        """
        subs = (m.groups()[0] for m in map(lambda x: x.match(river), self.substrings) if m)
        repls = (r[0].sub(r[1], river) for r in self.replacements)
        gens = itertools.tee(itertools.chain(subs, repls))
        return set(itertools.chain(gens[0], map(lambda x: x.strip(), gens[1])))

class RiverStack(list):
    def __init__(self):
        self.rivers = []
        self.ns = NameSuggestion()

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
            #print("\t'{}' in {}".format(dest, str(self)))
            return True
        else:
            #print("\t'{}' not in {}".format(dest, str(self)))
            return False

    def find_similar(self, dest):
        for name in self.ns.suggest(dest):
            #print(name)
            exists = name in self.rivers
            print("\t'{}' <-> '{}'; exists in '{}': {}".format(name, dest, str(self), exists))
            if exists:
                print("\tSuggesting '{}' instead of '{}'".format(name, dest))
                return name

class RiverSystems(object):
    """
    Several independent river systems can be discovered while parsing the
    initial data. This class is trying to keep track of every of them.
    """
    _root_signs = [
        r'^теряется$',
        r'^оз.\s+([А-Я]{1}[а-яА-Я-]+)$',
    ]
    def __init__(self):
        self.roots = {}
        self.root_signs = list(map(re.compile, self._root_signs))

    def __len__(self):
        return len(self.roots)

    def __str__(self):
        return pprint.pformat(self.roots, indent=4)

    def add_river(self, river, dest):
        if len(self) == 0 or any(p.match(dest) for p in self.root_signs):
        #if len(self) == 0 or dest == 'теряется':
            self._add_root(river, dest)
        else:
            self._add_tributary(river, dest)

    def _create_root(self, root):
        print("Creating new root for '{}'...".format(root))
        self.roots[root] = RiverStack()
        self.roots[root].push(root)
        self.active_root = root

    def _add_root(self, river, dest):
        if dest != "теряется":
            self._create_root(dest)
            self.roots[dest].push(river)
        else:
            self._create_root(river)

    def _add_tributary(self, river, dest):
        self.active_root = None
        target_stack = None

        # Good situation
        for root, stack in self.roots.items():
            #print("Checking root: {}".format(root))
            if dest in stack:
                target_stack = stack
                self.active_root = root

        # Emergency situation - river was not found in any stack
        if not target_stack:
            for root, stack in self.roots.items():
                similar = stack.find_similar(dest)
                if similar:
                    dest = similar
                    target_stack = stack
                    self.active_root = root

        if not target_stack:
            raise Exception("Destination river '{}' wasn't found anywhere".format(dest))

        else:
            while dest != target_stack[-1]:
                target_stack.pop()
            target_stack.push(river)

    @property
    def active_system(self):
        return self.active_root, self.roots[self.active_root]


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
    rs = RiverSystems()

    for index, row in df.iterrows():
        river = row['river_main_name']
        dest = row['river_dest']

        try:
            rs.add_river(river, dest)
        except Exception:
            print(traceback.format_exc())
            print(rs)
            sys.exit(1)
        else:
            print(index[1], *rs.active_system)

    return rs


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
