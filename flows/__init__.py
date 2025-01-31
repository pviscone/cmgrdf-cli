import pygraphviz as PG
import os
import copy
from CMGRDF import Flow

class Tree:
    def __init__(self):
        self.segments={}
        self.leaves=set()
        self.heads=set()

    def add(self, name, obj, parent=None):
        if not isinstance(obj, list):
            obj = [obj]

        if isinstance(parent, list|set|tuple):
            for p in parent:
                if "{leaf}" in name:
                    segment_name = name.format(leaf=p)
                else:
                    segment_name = f"{name}{p}"
                self.add(segment_name, obj, parent=p)
            return

        assert name not in self.segments.keys()
        segment = Segment(name, obj)
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

    def add_to_all(self, name, obj):
        leaves = copy.deepcopy(self.leaves)
        for leaf in leaves:
            if "{leaf}" in name:
                segment_name = name.format(leaf=leaf)
            else:
                segment_name = f"{name}{leaf}"
            self.add(segment_name, obj, parent = leaf)

    def to_lists(self):
        res=[]
        for leaf in self.leaves:
            res.append(self.get_chain(self.segments[leaf], []))
        return res

    def to_dict(self, obj=True, concatenate = True):
        res={}
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

    def graphviz(self, outfile):
        A = PG.AGraph(directed=True, strict=True, overlap=False, splines='ortho')
        for _, segment in self.segments.items():
            if not segment.isLeaf:
                for child in segment.children:
                    A.add_edge(Flow(segment.name, segment.obj).__str__().replace("\033[1m", "").replace("\033[0m", ""),
                               Flow(self.segments[child].name, self.segments[child].obj).__str__().replace("\033[1m", "").replace("\033[0m", ""))
        A.layout(prog='dot', args="-Nshape=box -Gfontsize=15 -Nfontsize=15 -Efontsize=15")
        A.draw(f'{outfile}.pdf')
        os.system(f"pdftocairo {outfile}.pdf -png -r 200 {outfile}")
        os.system(f"mv {outfile}-1.png {outfile}.png")
        #os.system(f"termvisage {outfile}.png")


class Segment:
    def __init__(self, name, x):
        self.name = name
        self.obj = x
        self.children=set()
        self.parent = None
    def __repr__(self):
        return f"{self.name}: {self.obj}"
