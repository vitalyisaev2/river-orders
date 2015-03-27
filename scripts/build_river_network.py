#!/usr/bin/python3
# -*- coding: utf8 -*-

import os
import sys
import re
import itertools
import traceback
import pprint
import collections
import argparse
from distutils.util import strtobool

import pandas as pd
import numpy as np

pd.set_option('display.width', 160)

if __debug__:
    _df = None

class River(object):
    _split_pattern = re.compile(r'[,)(]{1}')
    _lost_pattern = re.compile(r'теряется')

    def __init__(self, _name, index):
        self.names = list(filter(lambda x: len(x) > 0,
                        [n.strip() for n in self._split_pattern.split(_name)]))

        if _name == 'без названия':
            self.indexed_name = 'без названия №{}'.format(index)
            self.names.append(self.indexed_name)

    @property
    def name(self):
        if hasattr(self, 'indexed_name'):
            return self.indexed_name
        else:
            return self.names[0]

    @property
    def nameless(self):
        return True if 'без названия' in self.names else False

    @property
    def lost(self):
        return any(self._lost_pattern.search(n) for n in self.names)

    def __str__(self):
        if len(self.names) == 1:
            return self.name
        else:
            return self.name + " ({})".format(', '.join(self.names))

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if isinstance(other, River):
            return set(self.names).intersection(set(other.names))
        elif isinstance(other, str):
            return other in self.names
        else:
            raise Exception(
                "Cannot compare River instance to {}".format(type(other)))

    def __hash__(self):
        return self.name.__hash__()


class NameSuggestion(object):
    """
    A collection of suggestions in the form of regular expressions
    that help to handle most common typos automatically
    """
    _substrings = [
        r"^протока р. ([а-яА-Я-]+)$",
        r"^([а-яА-Я-]+)\s*№\s*\d+$",
        r"^(оз.\s+[а-яА-Я-]+)\s+\(зал.\s+[а-яА-Я-]+\)$",
        r"^(оз.\s+[а-яА-Я-]+)\s+\([а-яА-Я-]+\s+залив\)$"
    ]
    _replacements = [
        (r"\.", ". "),
        (r"протока", "Протока"),
        (r'№\s*(\d+)', r'№\1'),
    ]
    _dash_capitalise = [
        r'(?=Кок)(Кок)(.*)$',
    ]

    def __init__(self):
        self.substrings = list(
            map(re.compile, self._substrings))
        self.replacements = list(
            map(lambda x: (re.compile(x[0]), x[1]), self._replacements))
        self.dash_capitalise = list(
            map(re.compile, self._dash_capitalise))

    def suggest(self, river):
        """
        Provides the set of unique suggested names, according to the list of
        regular expressions
        """
        subs = (m.groups()[0] for name in river.names
                for m in map(lambda x: x.match(name), self.substrings) if m)
        repls = (r[0].sub(r[1], name) for name in river.names
                 for r in self.replacements)
        dcs = ("-".join(map(lambda x: x.title(), m.groups()))
                for m in (dc.match(name)
                            for name in river.names
                            for dc in self.dash_capitalise
                    ) if m)
        g = itertools.tee(itertools.chain(subs, repls, dcs))
        return set(itertools.chain(g[0], map(lambda x: x.strip(), g[1])))


class RiverStack(list):
    ns = NameSuggestion()

    def __init__(self):
        self.rivers = []

    def __str__(self):
        if hasattr(self, 'river_names'):
            return "<-".join(self.river_names)
        else:
            return "RiverStack is empty"

    def __repr__(self):
        return str(self.rivers)

    def __getitem__(self, index):
        return self.rivers[index]

    def __len__(self):
        return len(self.rivers)

    def refresh_namelist(f):
        def wrapper(self, *args):
            res = f(self, *args)
            self.river_names = list(itertools.chain(*(r.names for r in self.rivers)))
            return res
        return wrapper

    @refresh_namelist
    def push(self, item):
        return self.rivers.append(item)

    @refresh_namelist
    def pop(self):
        return self.rivers.pop()

    def __contains__(self, river):
        #No river_names is typical for nameless rivers or
        #rivers related to internal drainage areas
        if not hasattr(self, 'river_names'):
            return False
        else:
            if set(river.names).intersection(self.river_names):
                print("\t{} in {}".format(river.names, str(self)))
                return True
            else:
                #print("\t{} not in {}".format(river.names, str(self)))
                return False

    def find_similar(self, dest):
        for name in self.ns.suggest(dest):
            exists = name in self.river_names
            print("\t'{}' <-> '{}'; exists in '{}': {}".format(name, dest, self.river_names, exists))
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
        r'^оз.\s+((Бол|Мал)\.\s+){0,1}([А-Я]{1}[а-яА-Я-]+)$',
        r'^[С|c]тарица\s+р.\s+[А-Яа-я-]+$',
        r'^оз.\s+(без\s+названия\s+){0,1}у\s+с\.\s+([А-Я]{1}[а-яА-Я-]+)$',
    ]

    def __init__(self):
        self.roots = collections.OrderedDict()
        self.root_signs = list(map(re.compile, self._root_signs))

    def __len__(self):
        return len(self.roots)

    def __str__(self):
        return pprint.pformat(self.roots, indent=4)

    def add_river(self, river, dest):
        if self._valid_root(dest):
            self._add_root(river, dest)
        else:
            self._add_tributary(river, dest)

    def _valid_root(self, root):
        conditions = (
            len(self) == 0,
            any(p.match(name) for name in root.names
                    for p in self.root_signs)
        )
        return any(conditions) and not root in self.roots

    def _add_root(self, river, dest, forced=False):
        if not dest.lost or forced:
            self._create_root(dest)
            self.roots[dest].push(river)
        else:
            #self._create_root(river, push_root=(not river.nameless))
            self._create_root(river, push_root=True)

    def _add_root_manually(self, river, dest):
        warning = """
River '{}' flows into '{}' but it wasn't found in existing river systems and\
look's like not a root of new river system. Do you wish to add it as a new
root? [y/n]""".format(river, dest)
        print(warning)
        while True:
            t = None
            try:
                t = strtobool(input().lower())
            except ValueError:
                print("Use 'y' or 'n'.")
            else:
                if t:
                    self._add_root(river, dest, forced=True)
                    return True
                else:
                    return False


    def _create_root(self, root, push_root=True):
        print("Creating new root for '{}'...".format(root))
        self.roots[root] = RiverStack()
        self.active_root = root
        if push_root:
            self.roots[root].push(root)

    def _add_tributary(self, river, dest):
        print("Adding tributary '{river}' for dest '{dest}'".format(**locals()))
        self.active_root = None
        target_stack = None

        # Good situation
        for root, stack in self.roots.items():
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
                    break

        if not target_stack:
            if not self._add_root_manually(river, dest):
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

    return df


def construct(df, **kwargs):
    rs = RiverSystems()

    for index, row in df.iterrows():
        river = River(row['river_full_name'], index[1])
        dest = River(row['river_dest'], index[1])
        try:
            rs.add_river(river, dest)
        except Exception:
            print(traceback.format_exc())
            print(rs)
            #import pdb; pdb.set_trace()
            sys.exit(1)
        else:
            print(index[1], *rs.active_system)

    return rs

def parse_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("datafile", help="Csv file with initial data",
                        type=str, required=True)
    parser.add_argument("-f", "--fixture",
                        help="List of fixtures (forced river roots etc.)",
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
            fixtures=f.read().split("\n")
    else:
        fixtures = None

    if __debug__:
        global _df
        _df = df

    construct(df, fixtures=fixtures)

if __name__ == "__main__":
    main()
