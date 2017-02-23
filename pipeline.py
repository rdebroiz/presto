import logging
from pprint import pformat
import path
import networkx as nx

from node import Root


class PipelineError(Exception):
    pass


class PipelineCyclicError(PipelineError):
    pass


class Pipeline():
    _root = Root()
    _graph = nx.DiGraph()
    _nodes = None

    def __init__(self, yaml_documents):
        # init with root
        self._nodes = {self._root.name: self._root}
        self._graph.add_node(self._root.name)
        # build graph
        self._build_nodes_from_documents(yaml_documents)
        self._build_edges()
        if self._cycle_detection():
            raise PipelineCyclicError()  # TODO what would be relevant here?
        # refine graph
        self._thin()

    def _build_nodes_from_documents(self, documents):
        from node import Node
        from yaml_io import YamlIO
        from evaluator import Evaluator
        from data_model import DataModel
        evltr = Evaluator()
        for doc in documents:
            try:
                if('__FILE__' in doc):
                    filename = path.Path(evltr.evaluate(doc['__FILE__']))
                    if(not filename.isabs()):
                        filename = DataModel.document_path / filename
                    d = YamlIO.load_all_yaml(filename)
                    self._build_nodes_from_documents(d)
                else:
                    try:
                        node = Node(doc, self._graph.nodes())
                    except:
                        logging.critical("Unable to build node from: %s",
                                         pformat(doc))
                        raise
                    self._graph.add_node(node.name)
                    self._nodes[node.name] = node
            except TypeError:
                logging.critical("A '__FILE__' entry is probably missing in "
                                 "the given pipe.yaml file' \n"
                                 "(the file shouldn't end with '---')")
                raise

    def _build_edges(self):
        for node in self._nodes:
            for parent in self._nodes[node].parents:
                self._graph.add_edge(parent, node)

    def _cycle_detection(self):
        have_cycle = False
        for cycle in nx.simple_cycles(self._graph):
            have_cycle = True
            logging.error("Cycle found: "
                          "%s", pformat(cycle))
        return have_cycle

    def _thin(self):
        """
        Remove all edges between one node and one of his parents
        if this parent is already one of the ancestors of any other of his
        parents.

        example:

                 A
                 *
               /   \
              o     o
            B *o----* C
             /      /
            o      /
           D *    /
              \  /
               oo
               *
               E

               becomes

              A *
                |
                o
              C *
             /  |
            /   |
           o    |
        B *     |
           \    |
            o   |
           D *  |
              \ |
               oo
              E *

        """
        for n in self._graph.nodes():
            for cur_p in self._graph.predecessors(n):
                for p in self._graph.predecessors(n):
                    if cur_p is p:
                        continue
                    else:
                        if cur_p in nx.ancestors(self._graph, p):
                            self._graph.remove_edge(cur_p, n)
                            break

    def walk(self, node):
        # TODO there must have a better way to do it.
        # yield node
        for n in nx.topological_sort(self._graph,
                                     nx.descendants(self._graph, node.name)):
            yield self._nodes[n]

    @property
    def root(self):
        return self._root

    @property
    def nodes(self):
        return self._nodes
