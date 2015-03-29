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
import yaml

pd.set_option('display.width', 160)

if __debug__:
    _df = None

_lost = ('^теряется$', '^разбирается на орошение$')

class River(object):
    _split_pattern = re.compile(r'[,)(]{1}')
    _lost_patterns = [re.compile(p) for p in _lost]
    _nameless_pattern = re.compile(r'без названия')

    def __init__(self, _name, index=None):
        self.names = list(filter(lambda x: len(x) > 0,
                        [n.strip() for n in self._split_pattern.split(_name)]))
        self.multiname = True if len(self.names) > 1 else False

        #if self.nameless:
        #    assert(index)
        #    self.indexed_name = '{} №{}'.format(_name, index)
        #    self.names.append(self.indexed_name)
        if index:
            main_name = self.names[0] if self.multiname else _name
            self.indexed_name = '{} №{}'.format(main_name, index)
            self.names.append(self.indexed_name)

    @property
    def name(self):
        #if hasattr(self, 'indexed_name'):
        #    return self.indexed_name
        #else:
        #    return self.names[0]
        if self.nameless:
            return self.indexed_name
        else:
            return self.names[0]

    @property
    def nameless(self):
        return any(map(self._nameless_pattern.search, self.names))

    @property
    def lost(self):
        return any(p.search(n) for p in self._lost_patterns for n in self.names)

    def __str__(self):
        if self.nameless:
            return self.indexed_name
        elif not(self.multiname):
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
    _substrings = (
        r"^[Пп]{1}ротока\s+р.\s+([а-яА-Я-]+)$",
        r"^([а-яА-Я-]+)\s*№\s*\d+$",
        r"^(оз.\s+[а-яА-Я-]+)\s+\(зал.\s+[а-яА-Я-]+\)$",
        r"^(оз.\s+[а-яА-Я-]+)\s+\([а-яА-Я-]+\s+залив\)$",
        r"^кл.\s+(.*)$"
    )
    _replacements = (
        (r"\.", ". "),
        (r"протока", "Протока"),
        (r"рукав", "Рукав"),
        (r"[В|в]{1}дхр(?!\.)", "вдхр."),
        (r'№\s*(\d+)', r'№\1'),
        (r"^([А-Я]{1}[а-яА-Я-]+)$", r'Ручей \1'),
        (r"^([А-Я]{1}[а-яА-Я-]+)$", r'Ключ \1'),
    )
    _dash_capitalise = (
        r'(?=Кок)(Кок)(.*)$',
    )
    _abbreviations = (
        ('Бел.', ('Белый', 'Белая', 'Белое')),
        ('Прав.', ('Правый', 'Правая', 'Правое')),
    )

    def __init__(self):
        self.substrings = list(
            map(re.compile, self._substrings))
        self.replacements = list(
            map(lambda x: (re.compile(x[0]), x[1]), self._replacements))
        self.dash_capitalise = list(
            map(re.compile, self._dash_capitalise))
        self.abbreviations = list(
            map(lambda x: (re.compile(x[0]), x[1]), self._abbreviations))

    def suggest(self, river):
        """
        provides the set of unique suggested names, according to the list of
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
        abbrs = (r[0].sub(form, name) for name in river.names for r in self.abbreviations for form in r[1])
        #abbrs = itertools.chain((form.sub([r[0], name), r[0].sub(form, name)) for name in river.names for form in r[1] for r in self.abbreviations)
        #def _double_replacement(truncated, morphed, name):
            #return truncated.replace(morphed, name), morphed.replace(truncated, name)
        #abbrs = itertools.chain(*(_double_replacement(r[0], morphed, name) for name in river.names for r in self._abbreviations for morphed in r[1]))
        g = itertools.tee(itertools.chain(subs, repls, dcs, abbrs))
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
        r'^оз.\s+((Бол|Мал)\.\s+){0,1}([А-Я]{1}[а-яА-Я-]+)$',
        r'^вдхр\.?\s+[А-Яа-я- .]+$',
        r'^[С|c]тарица\s+р.\s+[А-Яа-я-]+$',
        r'^оз.\s+(без\s+названия\s+){0,1}у\s+с\.\s+([А-Я]{1}[а-яА-Я-]+)$',
    ]
    _root_signs.extend(_lost)

    def __init__(self, fixtures=None):
        self.roots = collections.OrderedDict()
        self.root_signs = list(map(re.compile, self._root_signs))

        if fixtures:
            self.hanging_roots = [River(r) for r in fixtures["hanging_roots"]]

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
                    for p in self.root_signs),
            root in self.hanging_roots,
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
River '{}' flows into '{}' but it wasn't found in existing river systems and \
doesn't look like a root of new river system. Do you wish to add it as a new
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
            # maybe someone want to add roots interactively rather than with
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
    rs = RiverSystems(**kwargs)

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

    construct(df, fixtures=fixtures)

if __name__ == "__main__":
    main()
