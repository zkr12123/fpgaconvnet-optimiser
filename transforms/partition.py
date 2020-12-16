from tools.layer_enum import LAYER_TYPE
from transforms.helper import get_all_layers
from itertools import combinations, chain
import random
import tools.graphs as graphs
import tools.matrix as matrix 
import copy
import math

def check_parallel_block(self,partition_index):
    # check the input and output nodes
    input_node  = graphs.get_input_nodes(self.partitions[partition_index]['graph'])[0]
    output_node = graphs.get_output_nodes(self.partitions[partition_index]['graph'])[0]
    # check if not a parallel block
    if not ((self.partitions[partition_index]['graph'].nodes[input_node]['type'] == LAYER_TYPE.Split) and \
            (self.partitions[partition_index]['graph'].nodes[output_node]['type'] == LAYER_TYPE.Concat)):
        return False 
    # check the number of split and concat nodes
    n_split  = len(get_all_layers(self.partitions[partition_index]['graph'],LAYER_TYPE.Split))
    n_concat = len(get_all_layers(self.partitions[partition_index]['graph'],LAYER_TYPE.Concat))
    # break if there's too many parallel blocks
    if (n_split > 1) or (n_concat > 1):
        return False
    # is a standalone parallel block
    return True

def get_all_horizontal_splits(self,partition_index):
    # function to iterate over graph
    def _iterate_graph(edge_list,input_node,in_parallel_block):
        # check if end
        if self.partitions[partition_index]['graph'].out_degree(input_node) == 0:
            return edge_list
        # next node
        next_node = graphs.get_next_nodes(self.partitions[partition_index]['graph'],input_node)[0]
        # check if exiting parallel block
        if self.partitions[partition_index]['graph'].in_degree(input_node) > 1: 
            in_parallel_block = False
        # check if entering parallel block
        if self.partitions[partition_index]['graph'].out_degree(input_node) > 1: 
            return _iterate_graph(edge_list,next_node,True) 
        # skip node - concat partition
        if self.partitions[partition_index]['graph'].in_degree(next_node) > 1: 
            return _iterate_graph(edge_list,next_node,in_parallel_block) 
        # append to partition list
        if not in_parallel_block:
            edge_list.append((input_node,next_node))
        return _iterate_graph(edge_list,next_node,in_parallel_block) 
    # iterate over graph from start node
    input_node = graphs.get_input_nodes(self.partitions[partition_index]['graph'])[0]
    return _iterate_graph([],input_node,False) # TODO: assuming only one input

def get_all_vertical_splits(self,partition_index): # TODO: improve to get all possible combinations
    # check if parallel block
    if not self.check_parallel_block(partition_index):
        return None
    vertical_splits = []
    input_node = graphs.get_input_nodes(self.partitions[partition_index]['graph'])[0]
    split_nodes = graphs.get_next_nodes(self.partitions[partition_index]['graph'],input_node)
    subsets = [v for a in range(len(split_nodes)) for v in combinations(split_nodes, a)]
    for i in range(1,math.ceil(len(subsets)/2)):
        vertical_splits.append([list(chain(subsets[i])), [e for e in split_nodes if e not in subsets[i]]])
    return vertical_splits

def get_all_horizontal_merges(self,partition_index):
    # partition pairs
    partition_pairs = [(),()]
    # get the next node
    output_node = graphs.get_output_nodes(self.partitions[partition_index]['graph'])[0]
    def _find_next_partition():
        if self.graph.out_degree(output_node) > 0:
            next_node = graphs.get_next_nodes(self.graph,output_node)[0] 
            # find the partition pair for the output 
            for i in range(len(self.partitions)):
                if next_node in graphs.get_input_nodes(self.partitions[i]['graph']):
                    # check that this is a complete block if it's a split
                    if self.partitions[i]['graph'].out_degree(next_node) == self.graph.out_degree(next_node):
                        partition_pairs[0] = (partition_index,i)
    
    # check that if it's a concat layer, it's complete
    if self.graph.in_degree(output_node) > 1:
        if self.partitions[partition_index]['graph'].in_degree(output_node) == self.graph.in_degree(output_node):
            _find_next_partition()
    else:
        _find_next_partition()

    # get the previous node
    input_node = graphs.get_input_nodes(self.partitions[partition_index]['graph'])[0]
    def _find_prev_partition():
        if self.graph.in_degree(input_node) > 0:
            prev_node = graphs.get_prev_nodes(self.graph,input_node)[0] 
            # find the partition pair for the input
            for i in range(len(self.partitions)):
                if prev_node in graphs.get_output_nodes(self.partitions[i]['graph']):
                    # check that this is a complete block
                    if self.partitions[i]['graph'].in_degree(prev_node) == self.graph.in_degree(prev_node):
                        partition_pairs[1] = (i,partition_index)

    # check that if it's a split layer, it's complete
    if self.graph.out_degree(input_node) > 1:
        if self.partitions[partition_index]['graph'].out_degree(input_node) == self.graph.out_degree(input_node):
            _find_prev_partition()
    else: 
        _find_prev_partition()

    return partition_pairs

def get_all_vertical_merges(self,partition_index):
    # check if parallel block
    if not self.check_parallel_block(partition_index):
        return []
    # partition pairs
    partition_pairs = []
    # get input and output node
    input_node  = graphs.get_input_nodes(self.partitions[partition_index]['graph'])[0]
    output_node = graphs.get_output_nodes(self.partitions[partition_index]['graph'])[0]
    # find partitions with the same input,output pairs
    for i in range(len(self.partitions)):
        if partition_index == i:
            continue
        if (self.partitions[i]['input_nodes'][0] == input_node) and (self.partitions[i]['output_nodes'][0] == output_node):
            partition_pairs.append((i,partition_index))
    return partition_pairs

def split_horizontal(self, partition_index, edge):
    # create a new partition
    self.partitions.insert(partition_index,copy.deepcopy(self.partitions[partition_index]))
    # split graph
    partition_graphs = graphs.split_graph_horizontal(self.partitions[partition_index]['graph'],edge)
    self.partitions[partition_index]['graph']   = partition_graphs[0]
    self.partitions[partition_index+1]['graph'] = partition_graphs[1]
    # find the wr partition
    wr_layer  = self.partitions[partition_index]['wr_layer']
    wr_factor = self.partitions[partition_index]['wr_factor']
    ## apply to correct partition
    if wr_layer in partition_graphs[0]:
        self.partitions[partition_index]['wr_layer']    = wr_layer
        self.partitions[partition_index]['wr_factor']   = wr_factor
        self.apply_max_weights_reloading(partition_index+1)
    else:
        self.partitions[partition_index]['wr_layer']    = self.get_wr_layer(partition_index)
        self.partitions[partition_index]['wr_factor']   = 1 
        self.partitions[partition_index+1]['wr_layer']  = wr_layer
        self.partitions[partition_index+1]['wr_factor'] = wr_factor

def split_vertical(self, partition_index, nodes):
    # create a new partition
    self.partitions.insert(partition_index,copy.deepcopy(self.partitions[partition_index]))
    # split the graph
    partition_graphs = graphs.split_graph_vertical(self.partitions[partition_index]['graph'],nodes)
    self.partitions[partition_index]['graph']   = partition_graphs[0]
    self.partitions[partition_index+1]['graph'] = partition_graphs[1]
    # reset weights reloading
    self.apply_max_weights_reloading(partition_index)
    self.apply_max_weights_reloading(partition_index+1)

def merge_horizontal(self,partition_index_a,partition_index_b):
    partition_index = partition_index_a
    # merge graphs
    graph = graphs.merge_graphs_horizontal(self.partitions[partition_index_a]['graph'],self.partitions[partition_index_b]['graph'])
    self.partitions[partition_index]['graph'] = graph
    # keep weights reloading of last layer
    self.partitions[partition_index]['wr_layer']  = self.partitions[partition_index_b]['wr_layer'] 
    self.partitions[partition_index]['wr_factor'] = self.partitions[partition_index_b]['wr_factor'] 
    # remove last partition
    del self.partitions[partition_index_b]

def merge_vertical(self, partition_index_a, partition_index_b):
    partition_index = partition_index_a
    # merge graphs
    graph = graphs.merge_graphs_vertical(self.partitions[partition_index_a]['graph'],self.partitions[partition_index_b]['graph'])
    # update graphs
    self.partitions[partition_index]['graph'] = graph
    # remove weights reloading
    self.apply_max_weights_reloading(partition_index)
    # remove last partition
    del self.partitions[partition_index_b]

def split_horizontal_complete(self):
    # function to find a horizontal split
    def _find_horizontal_split_partition():
        for i in range(len(self.partitions)):
            if self.get_all_horizontal_splits(i):
                return i
        return None
    partition_index = _find_horizontal_split_partition()
    # keep iterating until all horizontal splits done
    while partition_index != None:
        # apply first possible split
        horizontal_splits = self.get_all_horizontal_splits(partition_index)
        self.split_horizontal(partition_index,horizontal_splits[0])
        # find next partition
        partition_index = _find_horizontal_split_partition()

def split_vertical_complete(self):
    def _find_vertical_split_partition():
        for i in range(len(self.partitions)):
            if self.get_all_vertical_splits(i):
                return i
        return None
    partition_index = _find_vertical_split_partition()
    # keep iterating until all horizontal splits done
    while partition_index != None:
        # apply first possible split
        vertical_splits = self.get_all_vertical_splits(partition_index)
        self.split_vertical(partition_index,vertical_splits[0])
        # find next partition
        partition_index = _find_vertical_split_partition()

def split_complete(self):
    self.split_horizontal_complete()
    self.split_vertical_complete()
    self.split_horizontal_complete()

def merge_horizontal_complete(self):
    def _find_horizontal_merge_partition():
        for i in range(len(self.partitions)):
            horizontal_merges = self.get_all_horizontal_merges(i)
            if horizontal_merges[0] or horizontal_merges[1]:
                return i
        return None
    # keep iterating until all horizontal splits done
    partition_index = _find_horizontal_merge_partition()
    while partition_index != None:
        # apply first possible split
        horizontal_merges = self.get_all_horizontal_merges(partition_index)
        if horizontal_merges[0]:
            self.merge_horizontal(*horizontal_merges[0])
        else:
            self.merge_horizontal(*horizontal_merges[1])
        # find next partition
        partition_index = _find_horizontal_merge_partition()

def merge_vertical_complete(self):
    def _find_vertical_merge_partition():
        for i in range(len(self.partitions)):
            if self.get_all_vertical_merges(i):
                return i
        return None
    partition_index = _find_vertical_merge_partition()
    # keep iterating until all horizontal splits done
    while partition_index != None:
        # apply first possible split
        vertical_merges = self.get_all_vertical_merges(partition_index)
        self.merge_vertical(*vertical_merges[0])
        # find next partition
        partition_index = _find_vertical_merge_partition()

def merge_complete(self):
    self.merge_horizontal_complete()
    self.merge_vertical_complete()
    self.merge_horizontal_complete()

def apply_random_partition(self, partition_index):
   # choose randomly between merge or split
    ## split partition
    transform_type = random.choice(['split','merge'])
    if transform_type == 'split':
        ## get all possible splits
        horizontal_splits = self.get_all_horizontal_splits(partition_index)
        vertical_splits   = self.get_all_vertical_splits(partition_index)
        ## split horizontally first
        if horizontal_splits:
            self.split_horizontal(partition_index,random.choice(horizontal_splits))
        ## vertically second choice
        elif vertical_splits:
            self.split_vertical(partition_index,random.choice(vertical_splits))
    ## merge partition
    if transform_type == 'merge':
        # get all possible merges
        horizontal_merges = self.get_all_horizontal_merges(partition_index)
        vertical_merges   = self.get_all_vertical_merges(partition_index)
        ## merge horizontally first
        if horizontal_merges[0]:
            self.merge_horizontal(*horizontal_merges[0])
        elif horizontal_merges[1]:
            self.merge_horizontal(*horizontal_merges[1])
        elif vertical_merges: 
            self.merge_vertical(*random.choice(vertical_merges))
            
