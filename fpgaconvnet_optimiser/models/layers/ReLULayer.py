from fpgaconvnet_optimiser.models.modules import ReLU
from fpgaconvnet_optimiser.models.layers import Layer

import torch
import numpy as np
import math
import onnx
import pydot

class ReLULayer(Layer):
    def __init__(
            self,
            rows: int,
            cols: int,
            channels: int,
            coarse: int = 1,
            data_width: int = 16
        ):

        # initialise parent class
        super().__init__([rows],[cols],[channels],[coarse],[coarse],
                data_width=data_width)

        self.coarse = coarse

        # init modules
        self.modules = {
            "relu" : ReLU(self.rows_in(), self.cols_in(), self.channels_in())
        }
        self.update()

    def streams_in(self, port_index=0):
        assert(port_index < self.ports_in)
        return self.coarse

    def streams_out(self, port_index=0):
        assert(port_index < self.ports_out)
        return self.coarse

    def update_coarse_in(self, coarse_in, port_index=0):
        assert(port_index < self.ports_in)
        self.coarse = coarse_in

    def update_coarse_out(self, coarse_out, port_index=0):
        assert(port_index < self.ports_out)
        self.coarse = coarse_out

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
        parameters.coarse_in    = self.coarse
        parameters.coarse_out   = self.coarse
        parameters.coarse       = self.coarse

    ## UPDATE MODULES ##
    def update(self):
        self.modules['relu'].rows     = self.rows_in()
        self.modules['relu'].cols     = self.cols_in()
        self.modules['relu'].channels = int(self.channels_in()/self.coarse)

    def visualise(self,name):
        cluster = pydot.Cluster(name,label=name)

        for i in range(self.coarse):
            cluster.add_node(pydot.Node( "_".join([name,"relu",str(i)]), label="relu" ))

        # get nodes in and out
        nodes_in  = [ "_".join([name,"relu",str(i)]) for i in range(self.streams_in()) ]
        nodes_out = [ "_".join([name,"relu",str(i)]) for i in range(self.streams_out()) ]

        return cluster, nodes_in, nodes_out

    def functional_model(self,data,batch_size=1):

        assert data.shape[0] == self.rows_in()    , "ERROR: invalid row dimension"
        assert data.shape[1] == self.cols_in()    , "ERROR: invalid column dimension"
        assert data.shape[2] == self.channels_in(), "ERROR: invalid channel dimension"

        # instantiate relu layer
        relu_layer = torch.nn.ReLU()

        # return output featuremap
        data = np.moveaxis(data, -1, 0)
        data = np.repeat(data[np.newaxis,...], batch_size, axis=0)
        return relu_layer(torch.from_numpy(data)).detach().numpy()

