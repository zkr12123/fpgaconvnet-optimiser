from fpgaconvnet.tools.layer_enum import LAYER_TYPE

from fpgaconvnet.models.layers import ConvolutionLayer, ConvolutionLayer3D
from fpgaconvnet.models.layers import PoolingLayer, PoolingLayer3D
from fpgaconvnet.models.layers import GlobalPoolingLayer, GlobalPoolingLayer3D
from fpgaconvnet.models.layers import InnerProductLayer, InnerProductLayer3D
from fpgaconvnet.models.layers import EltWiseLayer, EltWiseLayer3D
from fpgaconvnet.models.layers import ReLULayer, ReLULayer3D

def get_convolution_from_dict(param, dimensionality):
    if dimensionality == 2:
        return ConvolutionLayer(
                param["filters"],  param["rows"],
                param["cols"], param["channels"],
                groups=param["groups"],
                fine=param["fine"],
                coarse_in=param["coarse_in"],
                coarse_out=param["coarse_out"],
                coarse_group=param["coarse_group"],
                kernel_rows=param["kernel_rows"],
                kernel_cols=param["kernel_cols"],
                stride_rows=param["stride_rows"],
                stride_cols=param["stride_cols"],
                pad_left=param["pad_left"],
                pad_right=param["pad_right"],
                pad_top=param["pad_top"],
                pad_bottom=param["pad_bottom"])
    elif dimensionality == 3:
        return ConvolutionLayer3D(
                param["filters"],  param["rows"],
                param["cols"], param["depth"],
                param["channels"],
                groups=param["groups"],
                fine=param["fine"],
                coarse_in=param["coarse_in"],
                coarse_out=param["coarse_out"],
                coarse_group=param["coarse_group"],
                kernel_rows=param["kernel_rows"],
                kernel_cols=param["kernel_cols"],
                kernel_depth=param["kernel_depth"],
                stride_rows=param["stride_rows"],
                stride_cols=param["stride_cols"],
                stride_depth=param["stride_depth"],
                pad_left=param["pad_left"],
                pad_right=param["pad_right"],
                pad_top=param["pad_top"],
                pad_bottom=param["pad_bottom"],
                pad_front=param["pad_front"],
                pad_back=param["pad_back"])
    else:
        raise NotImplementedError

def get_inner_product_from_dict(param, dimensionality):
    if dimensionality == 2:
        return InnerProductLayer(
                param["filters"],  1, 1,
                param["rows"]*param["cols"]*param["channels"],
                coarse_in=param["coarse_in"],
                coarse_out=param["coarse_out"]
            )
    elif dimensionality == 3:
        return InnerProductLayer3D(
                param["filters"],  1, 1, 1,
                param["rows"]*param["cols"]*param["depth"]*param["channels"],
                coarse_in=param["coarse_in"],
                coarse_out=param["coarse_out"],
            )
    else:
        raise NotImplementedError

def get_pooling_from_dict(param, dimensionality):
    if dimensionality == 2:
        return PoolingLayer(
                param["rows"], param["cols"],
                param["channels"],
                coarse=param["coarse"],
                kernel_rows=param["kernel_rows"],
                kernel_cols=param["kernel_cols"],
                stride_rows=param["stride_rows"],
                stride_cols=param["stride_cols"],
                pad_left=param["pad_left"],
                pad_right=param["pad_right"],
                pad_top=param["pad_top"],
                pad_bottom=param["pad_bottom"])
    elif dimensionality == 3:
        return PoolingLayer3D(
                param["rows"], param["cols"],
                param["depth"],
                param["channels"],
                coarse=param["coarse"],
                kernel_rows=param["kernel_rows"],
                kernel_cols=param["kernel_cols"],
                kernel_depth=param["kernel_depth"],
                stride_rows=param["stride_rows"],
                stride_cols=param["stride_cols"],
                stride_depth=param["stride_depth"],
                pad_left=param["pad_left"],
                pad_right=param["pad_right"],
                pad_top=param["pad_top"],
                pad_bottom=param["pad_bottom"],
                pad_front=param["pad_front"],
                pad_back=param["pad_back"])
    else:
        raise NotImplementedError

def get_eltwise_from_dict(param, dimensionality):
    if dimensionality == 2:
        return EltWiseLayer(
                param["rows"],  param["cols"], param["channels"],
                ports_in=param["ports_in"],
                coarse=param["coarse"],
                op_type=param["op_type"],
                broadcast=param["broadcast"],
            )
    elif dimensionality == 3:
        return EltWiseLayer3D(
                param["rows"],  param["cols"],
                param["depth"], param["channels"],
                ports_in=param["ports_in"],
                coarse=param["coarse"],
                op_type=param["op_type"],
                broadcast=param["broadcast"],
            )
    else:
        raise NotImplementedError

def get_global_pooling_from_dict(param, dimensionality):
    if dimensionality == 2:
        return GlobalPoolingLayer(
                param["rows"],
                param["cols"],
                param["channels"],
                coarse=param["coarse"],
            )
    elif dimensionality == 3:
        return GlobalPoolingLayer3D(
                param["rows"],
                param["cols"],
                param["depth"],
                param["channels"],
                coarse=param["coarse"],
            )
    else:
        raise NotImplementedError

def get_relu_from_dict(param, dimensionality):
    if dimensionality == 2:
        return ReLULayer(
                param["rows"],
                param["cols"],
                param["channels"],
                coarse=param["coarse"],
            )
    elif dimensionality == 3:
        return ReLULayer3D(
                param["rows"],
                param["cols"],
                param["depth"],
                param["channels"],
                coarse=param["coarse"],
            )
    else:
        raise NotImplementedError

def get_hw_from_dict(layer_type, param, dimensionality):
    match layer_type:
        case LAYER_TYPE.Convolution:
            return get_convolution_from_dict(param, dimensionality)
        case LAYER_TYPE.InnerProduct:
            return get_inner_product_from_dict(param, dimensionality)
        case LAYER_TYPE.Pooling:
            return get_pooling_from_dict(param, dimensionality)
        case LAYER_TYPE.EltWise:
            return get_eltwise_from_dict(param, dimensionality)
        case LAYER_TYPE.ReLU:
            return get_relu_from_dict(param, dimensionality)
        case _:
            raise NotImplementedError(f"layer type {layer_type} not implemented")


