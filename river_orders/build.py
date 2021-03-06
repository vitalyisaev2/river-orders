#! -*- coding: utf8 -*-
import re
import pprint
import logging
from itertools import chain
from collections import OrderedDict
from distutils.util import strtobool

from numpy import isnan
import pandas

from .naming import NameSuggestion
from .graph import DirectedGraph

_lost = (
    '^теряется(\s+в\s+(болот(е|ах)|пойме))?(\s+р.\s+[А-Яа-я-]+)?$',
    '^разбирается на орошение$'
)

_lake_signs = (
    r'^оз.\s+((Бол|Мал)\.\s+)?([а-яА-Я- ]+)$',
    r'^вдхр\.?\s+[А-Яа-я- .]+$',
    r'^болото,?(\s+прилегающее к р.)?\s+[А-Яа-я- .]+$',
    r'^[А-Яа-я- .]+\s+вдхр.(\s+р.\s[А-Яа-я- .]+){0,1}$',
    r'^((С|с)тарица|(С|с)тароречье)\s+(без\s+названия\s+)?((в|на)\s+пойме\s+)?(р.\s+)?[А-Яа-я- ]+$',
    r'^оз\.?\s+(без\s+названия\s+){0,1}у\s+с\.\s+([А-Я]{1}[а-яА-Я-]+)$',
    r'^[А-Яа-я-]+\s+старица$',
    r'^оз\.?\s+(без\s+названия)?\s?(у\s+с\.\s+([а-яА-Я- ]+))?(№\s?\d+)?$',
)

_sea_signs = (
    r'^[А-Яа-я-]+\s*море$',
    r'^[А-Яа-я-]+\s*залив$',
    r'^залив\s+[А-Яа-я-]+$',
    r'^[А-Яа-я-]+\s*губа$',
    r'^губа\s+[А-Яа-я-]+$',
)


class WaterObject(object):

    """
    Represents any strem hydrological object. Attempts to handle in a simple way
    complicated name situation (noname river or river that flows into nowhere)
    """
    _split_pattern = re.compile(r'[,)(]{1}')
    _lost_patterns = [re.compile(p) for p in _lost]
    _nameless_pattern = re.compile(r'без названия')
    _lake_patterns = [re.compile(p) for p in _lake_signs]
    _sea_patterns = [re.compile(s) for s in _sea_signs]

    def __init__(self, _name,
                 length=0, dest_from_end=0, ten_km_trib_amount=0.0,
                 volume=None, index=None,
                 **kwargs):

        self.names = list(filter(lambda x: len(x) > 0,
                                 [n.strip() for n in self._split_pattern.split(_name)]))
        self.multiname = True if len(self.names) > 1 else False
        self.length = length
        self.dest_from_end = dest_from_end
        self.ten_km_trib_amount = ten_km_trib_amount if not isnan(ten_km_trib_amount) else 0.0
        self.volume = volume
        self.index = index

        self.main_name = self.names[0] if self.multiname else _name
        if index and volume:
            self.indexed_name = '{} №{}'.format(self.main_name, index)
            self.names.append(self.indexed_name)
            self.volume_indexed_name = '{} {}_{}'.format(self.main_name, volume, index)
        else:
            self.indexed_name = self.volume_indexed_name = self.main_name

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
    def is_lake(self):
        return any(l.search(n) for l in self._lake_patterns for n in self.names)

    @property
    def is_sea(self):
        return any(s.search(n) for s in self._sea_patterns for n in self.names)

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
        if isinstance(other, WaterObject):
            return set(self.names).intersection(set(other.names))
        elif isinstance(other, str):
            return other in self.names
        else:
            raise Exception(
                "Cannot compare WaterObject instance to {}".format(type(other)))

    def __hash__(self):
        if self.is_lake:
            return self.main_name.__hash__()
        else:
            return self.name.__hash__()


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
            if exists:
                logging.debug("\tSuggesting '{}' instead of '{}'".format(name, dest))
                return name


class RiverSystems(object):

    """
    Several independent river systems can be discovered while parsing the
    initial data. This class is trying to keep track of every of them.
    """

    _root_signs = []
    _root_signs.extend(_lost)
    _root_signs.extend(_lake_signs)

    def __init__(self, fixtures=None):
        self.roots = OrderedDict()
        self.root_signs = [re.compile(p) for p in self._root_signs]

        # Some large lakes and reservoirs are described like a distinct bassins
        # while in fact they are part of large river system
        hanging_roots = fixtures.get("hanging_roots", []) if fixtures else []
        self.hanging_roots = [WaterObject(r) for r in hanging_roots]

        # Some large lakes and reservoirs are described like a distinct bassins
        # while in fact they are part of large river system
        self.fake_roots = fixtures.get("fake_roots", {}) if \
            fixtures else {}

    def __len__(self):
        return len(self.roots)

    def __str__(self):
        return pprint.pformat(self.roots, indent=4)

    def add_river(self, river, dest):
        root_kind = self._estimate_root(dest)
        if not root_kind:
            self._add_tributary(river, dest)
        elif root_kind == "real":
            self._add_root(river, dest)
        elif root_kind == "fake":
            self._add_fake_root(dest)
            self._add_tributary(river, dest)

    def _estimate_root(self, root):
        # Sometimes we can get faked roots (lakes or reservoirs)
        # so we need to check the fixtures first
        fake_root_conditions = (
            root.name in self.fake_roots,
            not any(root in stack for stack in self.roots.values())
        )
        real_root_conditions = (
            len(self) == 0,
            any(p.match(name) for name in root.names for p in self.root_signs),
            root in self.hanging_roots,
        )
        if all(fake_root_conditions):
            return "fake"
        else:
            if any(real_root_conditions) and root not in self.roots and not self._river_exists(root):
                return "real"
            else:
                return False

    def _add_root(self, river, dest, forced=False):
        if not dest.lost or forced:
            self._create_root(dest)
            self.roots[dest].push(river)
        else:
            self._create_root(river)

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

    def _create_root(self, root):
        # All fences are passed: that's really new river system
        logging.debug("Creating new root for '{}'...".format(root))
        self.roots[root] = RiverStack(root)
        self.active_root = root
        self.roots[root].push(root)

    def _add_fake_root(self, root):
        logging.debug("Fake root detected: {}".format(root))
        fake_root_info = self.fake_roots[root]
        dest = WaterObject(fake_root_info["dest"])
        root.ten_km_trib_amount = fake_root_info["ten_km_trib_amount"]
        root.dest_from_end = fake_root_info["dest_from_end"]
        self._add_tributary(root, dest)

    def _add_tributary(self, river, dest):
        logging.debug("Adding tributary '{river}' for dest '{dest}'".format(**locals()))
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

    def _river_exists(self, river):
        return any(river in stack for stack in self.roots.values())

    def get_river_system_by_element(self, water_object_name):
        return next((root, stack) for root, stack in self.roots.items() if
                    len(stack.DG.node[water_object_name]) != 0)

    def render(self, water_object_name=None):
        if water_object_name:
            root, rs = self.get_river_system_by_element(water_object_name)
            if rs:
                rs.order()
                rs.draw_from_node(water_object_name)
            else:
                print("Node {} hasn't been found anywhere".format(water_object_name))
        else:
            for root, rs in self.roots.items():
                print("Rendering {} bassin".format(root))
                rs.order()
                rs.draw()

    def dump(self, session_name):
        print("Concatenating results...")
        #df = pandas.DataFrame(list(chain(rs.results for rs in self.roots.values())))

        df = pandas.concat((pandas.DataFrame(rs.results) for rs in self.roots.values() if len(rs.results) > 0))
        fname = session_name + ".result.csv"
        print("Resulting DataFrame is {}. Dumping to {}...".format(df.shape, fname))
        df.to_csv(fname, sep=";")
