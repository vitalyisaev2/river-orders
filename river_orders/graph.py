import os
import sys
import traceback
from itertools import tee, chain
from collections import namedtuple

from numpy import isnan, log2
import networkx
import graphviz


def scheidegger(ten_km_trib_amount):
    return log2(ten_km_trib_amount) + 1.0


class GraphvizNode(namedtuple("GraphvizNode",
                              ["name", "ten_km_trib_amount", "order"])):

    @staticmethod
    def from_digraph_node(DG, name):
        return GraphvizNode(name=name,
                            ten_km_trib_amount=DG.node[name]["ten_km_trib_amount"],
                            order=DG.node[name]["order"])


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
        self.DG.node[river_node_name]['order'] = scheidegger(ten_km_trib_amount)

    def _sum_small_tribs(self, river_node_name):
        node_attrs = self.DG.node[river_node_name]
        tributaries = self.DG.predecessors(river_node_name)

        if len(tributaries) == 0:
            if isnan(node_attrs["ten_km_trib_amount"]):
                ten_km_trib_amount = 1.0
            else:
                ten_km_trib_amount = node_attrs["ten_km_trib_amount"]

            self._set_node_order(river_node_name, ten_km_trib_amount)
            return ten_km_trib_amount

        else:
            ten_km_trib_recur_sum = sum(map(self._sum_small_tribs, tributaries))
            self._set_node_order(river_node_name, ten_km_trib_recur_sum)

            return ten_km_trib_recur_sum

    def order(self):
        if __debug__:
            print("\tEstimating river orders...")
        self._sum_small_tribs(self.root.indexed_name)

    def gen_confluenced(self, trib_prev, trib_next):
        next(trib_next, None)
        pair_list = reversed(list(zip(trib_prev, trib_next)))
        confluenced = []

        for t1, t2 in pair_list:

            if len(confluenced) == 0:
                last_confluence = GraphvizNode.from_digraph_node(self.DG, t1)
                income = t2
            else:
                last_confluence = confluenced[-1]
                income = t1

            if len(confluenced) == 1:
                pass

            name = t1 + "__" + t2
            ten_km_trib_amount = last_confluence.ten_km_trib_amount + \
                self.DG.node[income]["ten_km_trib_amount"]
            order = scheidegger(ten_km_trib_amount)

            # if __debug__:
            #     msg = "name={}, {}<-{}, {}+{}={}, order={}".format(
            #         name, last_confluence.name, income,
            #         last_confluence.ten_km_trib_amount, self.DG.node[income]["ten_km_trib_amount"],
            #         ten_km_trib_amount, order)
            #     print(msg)

            confluenced.append(GraphvizNode(name, ten_km_trib_amount, order))

        return confluenced

    def graph_elements(self, river_node_name, tributaries):
        trib, trib_prev, trib_next = tee(tributaries, 3)

        # Make list of `confluence nodes`
        confluenced = list(self.gen_confluenced(trib_prev, trib_next))
        confluenced.reverse()

        # Create common nodes
        mainline_node_names = chain(
            [GraphvizNode.from_digraph_node(self.DG, river_node_name)],
            confluenced)
        sideline_node_names = (GraphvizNode.from_digraph_node(self.DG, t) for t in trib)
        mnn0, mnn1, mnn2 = tee(mainline_node_names, 3)
        snn0, snn1 = tee(sideline_node_names)
        next(mnn0, None)

        mnn1_prev, mnn1_next = tee(mnn1)
        next(mnn1_next, None)
        mainline_edges = zip(mnn1_next, mnn1_prev)

        next(mnn2, None)
        sideline_edges = zip(snn1, mnn2)

        # Crete edges
        if len(confluenced) > 0:
            edges = [mainline_edges,
                     sideline_edges,
                     [
                         (
                             GraphvizNode.from_digraph_node(self.DG, tributaries[-1]),
                             confluenced[-1]
                         )
                     ]]
        else:
            edge_ends = (tributaries[0], river_node_name)
            edges = [[map(lambda x: GraphvizNode.from_digraph_node(self.DG, x),
                          edge_ends)]]

        edge_names = list(chain(*edges))

        return mnn0, snn0, edge_names

    def _render_bassin(self, river_node_name):
        # If this is a fist order river, nothing to draw
        if len(self.DG.predecessors(river_node_name)) == 0:
            return

        # Preparing list of tributaries
        try:
            tributaries = sorted(self.DG.predecessors(river_node_name),
                                 key=lambda name: self.DG.node[name]['dest_from_end'])
        except Exception:
            print("\tError while sorting {} tributaries: ".format(river_node_name))
            for tr in self.DG.predecessors(river_node_name):
                print("\t\t", tr, self.DG.node[tr])
            traceback.print_exc()
            sys.exit(1)

        mainline, sideline, edges = self.graph_elements(river_node_name, tributaries)
        for n in mainline:
            self.draw_node(n, confluenced=True)
        for s in sideline:
            self.draw_node(s, confluenced=False)
        for (t, d) in edges:
            self.dot.edge(t.name, d.name)

        for trib_name in tributaries:
            self._render_bassin(trib_name)

    def draw_node(self, node, confluenced=False):
        order = str(node.order)[:4]
        trib_amount = int(node.ten_km_trib_amount)
        if confluenced:
            xlabel = '<<FONT POINT-SIZE="10"> sum: {}\t<BR />ord: {}\t</FONT>>'
            self.dot.node(node.name, shape="point", xlabel=xlabel.format(
                          trib_amount, order))
        else:
            label = '<{}<BR /><FONT POINT-SIZE="10"> sum: {} ord: {}</FONT>>'
            self.dot.node(node.name,
                          label.format(node.name, trib_amount, order))

    def draw(self):
        if __debug__:
            print("\tChecking river network graph...")

        cycles = list(networkx.simple_cycles(self.DG))
        assert len(cycles) == 0, "Cycles: {}".format(cycles)

        if __debug__:
            print("\tRendering...")

        # Draw graph from the river of the highest order
        self.dot.node(self.root.indexed_name)
        try:
            self._render_bassin(self.root.indexed_name)
        except RuntimeError:
            # Graph cycles cause endless recursion
            traceback.format_exc()
        finally:
            # Save to file
            fname = '{}'.format(self.root.name + ".dot")
            path = os.path.join(os.path.dirname(sys.argv[0]), "pictures", fname)
            if __debug__:
                print("\tSaving to {}...".format(path))
            self.dot.render(path)
