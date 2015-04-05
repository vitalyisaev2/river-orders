#! -*- coding: utf8 -*-
import re
import itertools
import pprint
import collections
from distutils.util import strtobool
from operator import attrgetter

import networkx
import matplotlib.pyplot as plt

from .naming import NameSuggestion

_lost = ('^теряется$', '^разбирается на орошение$')


class River(object):

    """
    Represents any strem hydrological object. Attempts to handle in a simple way
    complicated name situation (noname river or river that flows into nowhere)
    """
    _split_pattern = re.compile(r'[,)(]{1}')
    _lost_patterns = [re.compile(p) for p in _lost]
    _nameless_pattern = re.compile(r'без названия')

    def __init__(self, _name, length, dest_from_end, index=None):
        self.names = list(filter(lambda x: len(x) > 0,
                                 [n.strip() for n in self._split_pattern.split(_name)]))
        self.multiname = True if len(self.names) > 1 else False
        self.length = length
        self.dest_from_end = dest_from_end
        self.tributaries = Tributaries()
        self.G = networkx.Graph()

        if index:
            main_name = self.names[0] if self.multiname else _name
            self.indexed_name = '{} №{}'.format(main_name, index)
            self.names.append(self.indexed_name)

    @property
    def name(self):
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

    @property
    def graph(self):
        return self.G

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

    def finalize(self):
        if len(self.tributaries) == 0:
            self.G.add_node(self.name)
        else:
            bassin = self.tributaries.sorted_graph
            for trib in bassin:
                self.G.add_edge(self, trib)


class Tributaries(object):

    def __init__(self):
        self.tribs = []

    def __add__(self, other):
        if isinstance(other, River):
            self.tribs.append(other)
        else:
            raise Exception("'{}' is instance of '{}' while River was expected".format(
                other, other.__class__.__name__))

    def __len__(self):
        return len(self.tribs)

    @property
    def sorted_graph(self):
        return map(lambda t: t.graph, sorted(self.tribs, key=attrgetter('dest_from_end')))


class RiverStack(list):

    # FIXME: wanna have the only instance for NameSuggestion
    # for all the RiverStack instances. Is it correct?
    ns = NameSuggestion()

    def __init__(self, root):
        self.rivers = []
        self.root = root
        # initialize river network graph
        self.G = networkx.Graph()
        self.G.add_node(self.root)

    def __str__(self):
        if self.rivers:
            return "<-".join(map(str, self.rivers))
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

    @property
    def last_river(self):
        return self.rivers[-1]

    @property
    def next_order_river(self):
        return self.rivers[-2]

    @property
    def graph():
        return self.G

    @refresh_namelist
    def push(self, river):
        """
        When the river is pushed to the appropriate stack,
        it's stored in the tributary list of the next order river
        """
        self.rivers.append(river)
        self.next_order_river.tributaries += self.last_river

    @refresh_namelist
    def pop(self):
        """
        When leaving the river bassin, we need to add its graph
        to the graph of the next order river
        """
        self.last_river.finalize()
        self.next_order_river.graph.add_edge(self.next_order_river, self.last_river.graph)
        self.rivers.pop()

    def __contains__(self, river):
        # No river_names is typical for nameless rivers or
        # rivers related to internal drainage areas
        if not hasattr(self, 'river_names'):
            return False
        else:
            if set(river.names).intersection(self.river_names):
                return True
            else:
                return False

    def find_similar(self, dest):
        for name in self.ns.suggest(dest):
            exists = name in self.river_names
            print(
                "\t'{}' <-> '{}'; exists in '{}': {}".format(name, dest, self.river_names, exists))
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
        else:
            self.hanging_roots = []

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
        return any(conditions) and root not in self.roots

    def _add_root(self, river, dest, forced=False):
        if not dest.lost or forced:
            self._create_root(dest)
            self.roots[dest].push(river)
        else:
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
        self.roots[root] = RiverStack(root)
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

    def draw_all(self):
        for river, river_stack in self.roots.items():
            pass



