#! -*- coding: utf8 -*-
import re
from itertools import tee, chain
import pprint
import collections
import traceback
from distutils.util import strtobool

from numpy import isnan, log2
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

    def __init__(self, _name,
                 length=0, dest_from_end=0, ten_km_trib_amount=0.0, index=None,
                 **kwargs):

        self.names = list(filter(lambda x: len(x) > 0,
                                 [n.strip() for n in self._split_pattern.split(_name)]))
        self.multiname = True if len(self.names) > 1 else False
        self.length = length
        self.dest_from_end = dest_from_end
        self.ten_km_trib_amount = ten_km_trib_amount

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

    def __init__(self, root):
        self.root = root
        self.dot = graphviz.Digraph()
        self.DG = networkx.DiGraph()

    def add_node(self):
        # TODO: the fact that we cannot use river as a node
        # is very annoying. Need to modify hashing
        self.DG.add_node(self.last_river.indexed_name,
                         length=self.last_river.length,
                         dest_from_end=self.last_river.dest_from_end,
                         ten_km_trib_amount=self.last_river.ten_km_trib_amount)
        if len(self) > 1:
            self.DG.add_edge(self.last_river.indexed_name,
                             self.next_order_river.indexed_name)

    def _set_node_order(self, river_node_name, ten_km_trib_amount):
        self.DG.node[river_node_name]['ten_km_trib_amount'] = ten_km_trib_amount
        self.DG.node[river_node_name]['order'] = log2(ten_km_trib_amount) + 1.0

    def _sum_small_tribs(self, river_node_name):
        node_attrs = self.DG.node[river_node_name]
        tributaries = self.DG.predecessors(river_node_name)

        if len(tributaries) == 0:
            if isnan(node_attrs["ten_km_trib_amount"]):
                ten_km_trib_amount = 1.0
            else:
                ten_km_trib_amount = node_attrs["ten_km_trib_amount"]

            #print("{}: ten_km_trib_amount {}".format(river_node_name, ten_km_trib_amount))
            self._set_node_order(river_node_name, ten_km_trib_amount)
            return ten_km_trib_amount

        else:
            ten_km_trib_recur_sum = sum(map(self._sum_small_tribs, tributaries))
            #print("{}: ten_km_trib_recur_sum {}".format(river_node_name, ten_km_trib_recur_sum))
            self._set_node_order(river_node_name, ten_km_trib_recur_sum)

            return ten_km_trib_recur_sum


    def order(self):
        if __debug__:
            print("Estimating river orders...")
        self._sum_small_tribs(self.root.indexed_name)

    @staticmethod
    def graph_elements(river_node_name, tributaries):
        trib, trib_prev, trib_next = tee(tributaries, 3)

        # Make list of `confluence nodes`
        next(trib_next, None)
        confluenced = [t1 + " - " + t2
                       for (t1, t2) in zip(trib_prev, trib_next)]

        # Create nodes
        mainline_node_names, mn1, mn2 = tee(chain([river_node_name], confluenced), 3)
        sideline_node_names, sn1 = tee(t for t in trib)
        next(mainline_node_names, None)

        # Create pairwise edges on the main line
        mn1_prev, mn1_next = tee(mn1)
        next(mn1_next, None)
        mainline_edges = zip(mn1_next, mn1_prev)

        # Create edges on the side lines
        next(mn2, None)
        sideline_edges = zip(sn1, mn2)

        # "Last/single tributary bug"
        if len(confluenced) > 0:
            edges = [mainline_edges, sideline_edges, [(tributaries[-1], confluenced[-1])]]
        else:
            edges = [[(tributaries[0], river_node_name)]]
        edge_names = chain(*edges)

        return mainline_node_names, sideline_node_names, edge_names

    def _render_bassin(self, river_node_name):
        # If this is a fist order river, nothing to draw
        # print(river_node, self.DG.predecessors(river_node))
        if len(self.DG.predecessors(river_node_name)) == 0:
            return

        # Preparing list of tributaries
        tributaries = sorted(self.DG.predecessors(river_node_name),
                             key=lambda name: self.DG.node[name]['dest_from_end'])

        mainline, sideline, edges = self.graph_elements(river_node_name, tributaries)
        for node_name in mainline:
            self.dot.node(node_name, shape="point")
        for node_name in sideline:
            self.dot.node(node_name)
        for (trib, dest) in edges:
            self.dot.edge(trib, dest)

        for trib_name in tributaries:
            self._render_bassin(trib_name)

    def draw(self):
        if __debug__:
            print("Checking river network graph...")

        cycles = list(networkx.simple_cycles(self.DG))
        assert len(cycles) == 0, "Cycles: {}".format(cycles)

        print("Trying to render '{}' river bassin...".format(self.root.name))

        # Draw graph from the river of the highest order
        self.dot.node(self.root.indexed_name)
        try:
            self._render_bassin(self.root.indexed_name)
        except RuntimeError:
            # Graph cycles cause endless recursion
            traceback.format_exc()
        finally:
            # Save to file
            self.dot.render('{}'.format(self.root.name))


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
            self.river_names = list(chain(*(r.names for r in self.rivers)))
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
        print("\nAdding tributary '{river}' for dest '{dest}'".format(**locals()))
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
            rs.order()
            rs.draw()
            break
