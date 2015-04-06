#! -*- coding: utf8 -*-
import re
import itertools
import pprint
import collections
from distutils.util import strtobool

import networkx
import graphviz

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

    def __init__(self, _name, length=0, dest_from_end=0, index=None, **kwargs):
        self.names = list(filter(lambda x: len(x) > 0,
                                 [n.strip() for n in self._split_pattern.split(_name)]))
        self.multiname = True if len(self.names) > 1 else False
        self.length = length
        self.dest_from_end = dest_from_end
        # self.tributaries = Tributaries()

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


class DirectedGraph(object):

    """
    Mixin class that provides a Networkx storage for river
    networks.

    Since pygraphviz doesn't work with Python3, we'll need to
    draw graph manually with graphviz.
    """

    def __init__(self, name):
        self.name = name
        self.dot = graphviz.Digraph()
        self.DG = networkx.DiGraph()

    def add_node(self):

        self.DG.add_node(self.last_river)
        self.dot.node(self.last_river.name)

        if len(self) > 1:
            self.DG.add_edge(self.last_river, self.next_order_river)
            #self.dot.edge(self.last_river.name, self.next_order_river.name)
            self.dot.edge(self.next_order_river.name, self.last_river.name)

    def draw(self):
        print("Trying to render '{}' river bassin...".format(self.name))
        self.dot.render('{}'.format(self.name))


class RiverStack(DirectedGraph):

    # FIXME: wanna have the only instance for NameSuggestion
    # for all the RiverStack instances. Is it correct?
    ns = NameSuggestion()

    def __init__(self, root):
        super().__init__(root)
        self.rivers = []

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

    @refresh_namelist
    def push(self, river):
        """
        When the river is pushed to the appropriate stack,
        it's stored in the tributary list of the next order river
        """
        self.rivers.append(river)
        self.add_node()

    @refresh_namelist
    def pop(self):
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
            # print(
            #     "\t'{}' <-> '{}'; exists in '{}': {}".format(name, dest, self.river_names, exists))
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

    def draw(self):
        for _, rs in self.roots.items():
            rs.draw()
            if __debug__:
                break
