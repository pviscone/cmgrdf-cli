import pygraphviz as PG
import os
import copy
import re
from CMGRDF import Flow
from collections import OrderedDict

class Tree:
    def __init__(self):
        self.segments=OrderedDict({})
        self.leaves=set()
        self.heads=set()

    def add(self, name, obj, parent=None, **kwargs):
        if not isinstance(obj, list):
            obj = [obj]

        for k, v in kwargs.items():
            for i in range(len(obj)):
                if k=="samplePattern":
                    obj[i].sample = re.compile(v + "$") if v else None  # regex pattern
                else:
                    setattr(obj[i], k, v)

        if isinstance(parent, list|set|tuple):
            for p in parent:
                self.add(name, obj, parent=p, **kwargs)
            return

        if parent and "{leaf}" in name:
            segment_name = name.format(leaf=parent)
        else:
            segment_name = name

        assert segment_name not in self.segments.keys()
        segment = Segment(segment_name, obj)
        segment.parent = parent
        segment.isLeaf = True
        segment.isHead = False if parent else True
        self.leaves.add(segment.name)
        self.segments[segment.name]=segment

        if parent:
            assert parent in self.segments.keys()
            self.segments[parent].children.add(segment.name)
            if self.segments[parent].isLeaf:
                self.segments[parent].isLeaf=False
                self.leaves.remove(parent)
        else:
            self.heads.add(segment.name)

    def add_to_all(self, name, obj, **kwargs):
        leaves = copy.deepcopy(self.leaves)
        for leaf in leaves:
            if "{leaf}" in name:
                segment_name = name.format(leaf=leaf)
            else:
                segment_name = f"{name}{leaf}"
            self.add(segment_name, obj, parent = leaf, **kwargs)
            self.segments[segment_name].common_to_all = True

    def to_lists(self):
        res=[]
        for leaf in self.leaves:
            res.append(self.get_chain(self.segments[leaf], []))
        return res

    def to_dict(self, obj=True, concatenate = True):
        res=OrderedDict({})
        for leaf in self.leaves:
            res[leaf]=self.get_chain(self.segments[leaf], [])
        if obj:
            for key in res:
                res[key]=[l.obj for l in res[key]]
            if concatenate:
                for key in res:
                    res[key]=[step for segment in res[key] for step in segment]
        return res

    def get_chain(self, leaf, res):
        res.append(leaf)
        if leaf.parent:
            self.get_chain(self.segments[leaf.parent], res)
        return res[::-1]

    def graphviz(self, outfile, clean_fn = lambda x: x):
        A = PG.AGraph(directed=True, strict=True, overlap=False, splines='ortho')

        for _, segment in self.segments.items():
            if not segment.isLeaf or segment.isHead:
                node1 = Flow(segment.name, segment.obj).__str__().replace("\033[1m", "").replace("\033[0m", "")
                node1_label = clean_fn(node1)
                if segment.name not in A.nodes():
                    A.add_node(segment.name, label=node1_label)
                for child in segment.children:
                    node2 = Flow(self.segments[child].name, self.segments[child].obj).__str__().replace("\033[1m", "").replace("\033[0m", "")
                    node2_label = clean_fn(node2)
                    if self.segments[child].common_to_all and self.segments[child].name not in A.nodes():
                        A.add_node(self.segments[child].name, label=node2_label, fillcolor="#71d0ff61", style="filled")
                    elif self.segments[child].isLeaf and self.segments[child].name not in A.nodes():
                        A.add_node(self.segments[child].name, label=node2_label, fillcolor="#8fff7161", style="filled")
                    elif self.segments[child].name not in A.nodes():
                        A.add_node(self.segments[child].name, label=node2_label)
                    A.add_edge(segment.name, self.segments[child].name, color = "#0032ff" if self.segments[child].common_to_all else "black")

        if os.path.exists(f'{outfile}.dot'):
            B = PG.AGraph(f'{outfile}.dot')
            # Add nodes
            for node in B.nodes():
                if node not in A.nodes():
                    A.add_node(node, label=B.get_node(node).attr['label'], fillcolor=B.get_node(node).attr['fillcolor'], style=B.get_node(node).attr['style'])
            # Add edges
            for edge in B.edges():
                if edge not in A.edges():
                    A.add_edge(edge[0], edge[1], color=B.get_edge(edge[0], edge[1]).attr['color'])

        A.layout(prog='dot', args="-Nshape=box -Gfontsize=15 -Nfontsize=15 -Efontsize=15")
        A.draw(f'{outfile}.pdf')
        A.write(f'{outfile}.dot')
        os.system(f"(pdftocairo {outfile}.pdf -png -r 200 {outfile} & wait; mv {outfile}-1.png {outfile}.png) &")


class Segment:
    def __init__(self, name, x):
        self.name = name
        self.obj = x
        self.children=set()
        self.parent = None
        self.common_to_all = False
        self.isLeaf = False
        self.isHead = False
    def __repr__(self):
        return f"{self.name}: {self.obj}"
