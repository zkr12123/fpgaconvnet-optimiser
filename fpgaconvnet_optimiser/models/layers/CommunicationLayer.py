import torch
import math
import numpy as np
import pydot

from fpgaconvnet_optimiser.models.modules import Communication
from fpgaconvnet_optimiser.models.modules import Fork
from fpgaconvnet_optimiser.models.modules import Glue
from fpgaconvnet_optimiser.models.layers import Layer

class CommunicationLayer(Layer):
    def __init__(
            self,
            dim,
            filters,
            groups          =1,
            coarse_in       =1,
            coarse_out      =1,
            data_width      =16,
            send_nreceive   =True,
            pair_id         =0,
        ):
        Layer.__init__(self,dim,coarse_in,coarse_out,data_width)

        # update flags
        self.flags['channel_dependant'] = True
        self.flags['transformable']     = True

        dim_out = [
            self.filters,
            self.rows_out(),
            self.cols_out()
        ]
        # init modules
        self.modules = {
            "fork"           : Fork(dim_out,1,coarse_out),
            "comm"  : Communication(dim_out,coarse_out,send_nreceive),
            "glue"           : Glue(dim_out,filters,coarse_in,coarse_out)
        }
        self.update()
        #self.load_coef()

        # switching activity
        self.sa     = sa
        self.sa_out = sa_out

    def rows_out(self):
        return int(math.floor((self.rows_in()-self.k_size+2*self.pad)/self.stride)+1)

    def cols_out(self):
        return int(math.floor((self.cols_in()-self.k_size+2*self.pad)/self.stride)+1)

    def channels_out(self):
        return self.filters

    def rate_in(self,index):
        return abs(self.balance_module_rates(self.rates_graph())[0,0])

    def rate_out(self,index):
        return abs(self.balance_module_rates(self.rates_graph())[4,5])

    ## LAYER INFO ##
    def layer_info(self,parameters,batch_size=1):
        parameters.batch_size   = batch_size
        parameters.buffer_depth = self.buffer_depth
        parameters.rows_in      = self.rows_in()
        parameters.cols_in      = self.cols_in()
        parameters.channels_in  = self.channels_in()
        parameters.rows_out     = self.rows_out()
        parameters.cols_out     = self.cols_out()
        parameters.channels_out = self.channels_out()
        parameters.coarse_in    = self.coarse_in
        parameters.coarse_out   = self.coarse_out
        parameters.fine         = self.fine
        parameters.filters      = self.filters
        parameters.kernel_size  = self.k_size
        parameters.stride       = self.stride
        parameters.groups       = self.groups
        parameters.pad          = self.pad
        parameters.pad_top      = self.pad_top
        parameters.pad_right    = self.pad_right
        parameters.pad_bottom   = self.pad_bottom
        parameters.pad_left     = self.pad_left

    ## UPDATE MODULES ##
    def update(self): 
        # sliding window
        self.modules['comm'].rows     = self.rows_in()
        self.modules['comm'].cols     = self.cols_in()
        self.modules['comm'].channels = int(self.channels/self.coarse_in)
        # fork
        self.modules['fork'].rows     = self.rows_out()
        self.modules['fork'].cols     = self.cols_out()
        self.modules['fork'].channels = int(self.channels/self.coarse_in)
        self.modules['fork'].coarse   = self.coarse_out
        # glue
        self.modules['glue'].rows       = self.rows_out()
        self.modules['glue'].cols       = self.cols_out()
        self.modules['glue'].filters    = self.filters
        self.modules['glue'].coarse_in  = self.coarse_in
        self.modules['glue'].coarse_out = self.coarse_out


    ### RATES ### 
    def rates_graph(self):
        rates_graph = np.zeros( shape=(3,4) , dtype=float )
    
        rates_graph[0,0] = self.modules['comm'].rate_in()
        rates_graph[0,1] = self.modules['comm'].rate_out()
        # fork
        rates_graph[1,1] = self.modules['fork'].rate_in()
        rates_graph[1,2] = self.modules['fork'].rate_out()
        # conv
        rates_graph[2,2] = self.modules['glue'].rate_in()
        rates_graph[2,3] = self.modules['glue'].rate_out()
        return rates_graph

    def get_coarse_in_feasible(self,wr_factor=1):
        return self.get_factors(int(self.channels_in()/(self.groups*wr_factor)))

    def get_coarse_out_feasible(self,wr_factor=1):
        return self.get_factors(int(self.channels_out()/(self.groups*wr_factor)))

    def get_fine_feasible(self):
        #return self.get_factors(int(self.k_size*self.k_size))
        return [ 1, self.k_size, self.k_size*self.k_size ]

    def get_weights_reloading_feasible(self):
        return self.get_factors(int(self.filters/(self.groups*self.coarse_out)))

    def get_parameters_size(self):
        weights_size = self.channels * int( self.filters / self.groups ) * self.k_size * self.k_size
        bias_size = 0
        return {
            "weights"   : weights_size,
            "bias"      : bias_size
        }

    def resource(self):

        comm_rsc      = self.modules['comm'].rsc()
        fork_rsc    = self.modules['fork'].rsc()
        glue_rsc    = self.modules['glue'].rsc()

        if self.coarse_out == 1:
            fork_rsc    = {"LUT" : 0,"BRAM" : 0,"DSP" : 0,"FF" : 0}
        if self.coarse_in == 1:
            glue_rsc    = {"LUT" : 0,"BRAM" : 0,"DSP" : 0,"FF" : 0}

        # weight usage
        # Total
        return {
            "LUT"  :  comm_rsc['LUT']*self.coarse_in +
                      fork_rsc['LUT']*self.coarse_in +
                      glue_rsc['LUT'],
            "FF"   :  comm_rsc['FF']*self.coarse_in +
                      fork_rsc['FF']*self.coarse_in +
                      glue_rsc['FF'],
            "BRAM" :  comm_rsc['BRAM']*self.coarse_in +
                      fork_rsc['BRAM']*self.coarse_in +
                      glue_rsc['BRAM'],
            "DSP"  :  comm_rsc['DSP']*self.coarse_in +
                      fork_rsc['DSP']*self.coarse_in +
                      glue_rsc['DSP']
        }

    def visualise(self,name):
        cluster = pydot.Cluster(name,label=name)

        for i in range(self.coarse_in):
            cluster.add_node(pydot.Node( "_".join([name,"comm",str(i)]), label="comm" ))

        for i in range(self.coarse_in):
            cluster.add_node(pydot.Node( "_".join([name,"fork",str(i)]), label="fork" ))
            cluster.add_edge(pydot.Edge( "_".join([name,"comm",str(i)]) , "_".join([name,"fork",str(i)]) ))

        for i in range(self.coarse_in):
            for j in range(self.coarse_out):
                cluster.add_node(pydot.Node( "_".join([name,"conv",str(i),str(j)]), label="conv" ))
                cluster.add_edge(pydot.Edge( "_".join([name,"fork",str(i)]) , "_".join([name,"conv",str(i),str(j)]) ))

        for i in range(self.coarse_in):
            for j in range(self.coarse_out):
                cluster.add_node(pydot.Node( "_".join([name,"glue",str(j)]), label="+" ))
                cluster.add_node(pydot.Node( "_".join([name,"accum",str(i),str(j)]), label="accum" ))
                cluster.add_edge(pydot.Edge( "_".join([name,"conv" ,str(i),str(j)]), "_".join([name,"accum",str(i),str(j)]) ))
                cluster.add_edge(pydot.Edge( "_".join([name,"accum",str(i),str(j)]), "_".join([name,"glue",str(j)]) ))

        # get nodes in and out
        nodes_in  = [ "_".join([name,"comm",str(i)]) for i in range(self.coarse_in) ]
        nodes_out = [ "_".join([name,"glue",str(i)]) for i in range(self.coarse_out) ]

        return cluster, nodes_in, nodes_out