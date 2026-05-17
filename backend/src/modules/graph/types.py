from typing import Literal

import networkx as nx

LayoutAlgorithm = Literal['forceatlas2', 'spring']

DirectedGraph = nx.DiGraph | nx.MultiDiGraph
AnyGraph = nx.Graph | nx.MultiGraph | DirectedGraph

ClusteringMethod = Literal['agc', 'louvain']
