import onnx
import onnxruntime
import onnx.utils
import onnx.numpy_helper
from onnx import version_converter
import onnxoptimizer as optimizer
from onnx.tools import update_model_dims

def add_value_info_for_constants(model : onnx.ModelProto):
    """
    Currently onnx.shape_inference doesn't use the shape of initializers, so add
    that info explicitly as ValueInfoProtos.
    Mutates the model.
    Args:
        model: The ModelProto to update.
    """
    # All (top-level) constants will have ValueInfos before IRv4 as they are all inputs
    if model.ir_version < 4:
        return

    def add_const_value_infos_to_graph(graph : onnx.GraphProto):
        inputs = {i.name for i in graph.input}
        existing_info = {vi.name: vi for vi in graph.value_info}
        for init in graph.initializer:
            # Check it really is a constant, not an input
            if init.name in inputs:
                continue

            # The details we want to add
            elem_type = init.data_type
            shape = init.dims

            # Get existing or create new value info for this constant
            vi = existing_info.get(init.name)
            if vi is None:
                vi = graph.value_info.add()
                vi.name = init.name

            # Even though it would be weird, we will not overwrite info even if it doesn't match
            tt = vi.type.tensor_type
            if tt.elem_type == onnx.TensorProto.UNDEFINED:
                tt.elem_type = elem_type
            if not tt.HasField("shape"):
                # Ensure we set an empty list if the const is scalar (zero dims)
                tt.shape.dim.extend([])
                for dim in shape:
                    tt.shape.dim.add().dim_value = dim

        # Handle subgraphs
        for node in graph.node:
            for attr in node.attribute:
                # Ref attrs refer to other attrs, so we don't need to do anything
                if attr.ref_attr_name != "":
                    continue

                if attr.type == onnx.AttributeProto.GRAPH:
                    add_const_value_infos_to_graph(attr.g)
                if attr.type == onnx.AttributeProto.GRAPHS:
                    for g in attr.graphs:
                        add_const_value_infos_to_graph(g)


    return add_const_value_infos_to_graph(model.graph)

def add_input_from_initializer(model : onnx.ModelProto):
    """
    Currently onnx.shape_inference doesn't use the shape of initializers, so add
    that info explicitly as ValueInfoProtos.
    Mutates the model.
    Args:
        model: The ModelProto to update.
    """
    # All (top-level) constants will have ValueInfos before IRv4 as they are all inputs
    if model.ir_version < 4:
        return

    def add_const_value_infos_to_graph(graph : onnx.GraphProto):
        inputs = {i.name for i in graph.input}
        existing_info = {vi.name: vi for vi in graph.input}
        for init in graph.initializer:
            # Check it really is a constant, not an input
            if init.name in inputs:
                continue

            # The details we want to add
            elem_type = init.data_type
            shape = init.dims

            # Get existing or create new value info for this constant
            vi = existing_info.get(init.name)
            if vi is None:
                vi = graph.input.add()
                vi.name = init.name

            # Even though it would be weird, we will not overwrite info even if it doesn't match
            tt = vi.type.tensor_type
            if tt.elem_type == onnx.TensorProto.UNDEFINED:
                tt.elem_type = elem_type
            if not tt.HasField("shape"):
                # Ensure we set an empty list if the const is scalar (zero dims)
                tt.shape.dim.extend([])
                for dim in shape:
                    tt.shape.dim.add().dim_value = dim

        # Handle subgraphs
        for node in graph.node:
            for attr in node.attribute:
                # Ref attrs refer to other attrs, so we don't need to do anything
                if attr.ref_attr_name != "":
                    continue

                if attr.type == onnx.AttributeProto.GRAPH:
                    add_const_value_infos_to_graph(attr.g)
                if attr.type == onnx.AttributeProto.GRAPHS:
                    for g in attr.graphs:
                        add_const_value_infos_to_graph(g)


    return add_const_value_infos_to_graph(model.graph)

def load(filepath):
    model = onnx.load(filepath)
    onnx.checker.check_model(model)
    add_input_from_initializer(model) #Seems to be necessary for conv layers from pytorch (at least)
    model = onnx.shape_inference.infer_shapes(model)
    model = onnx.utils.polish_model(model)
    passes = ["extract_constant_to_initializer", "eliminate_unused_initializer","fuse_bn_into_conv"]
    model = optimizer.optimize(model, passes=passes)

    return model

def update_batch_size(model, batch_size): # from https://github.com/microsoft/onnxruntime/issues/1467#issuecomment-514322927
    # change input batch size
    model.graph.input[0].type.tensor_type.shape.dim[0].dim_value = batch_size
    model.graph.output[0].type.tensor_type.shape.dim[0].dim_value = batch_size
    # clear value info
    model.graph.ClearField('value_info')
    # run shape inference
    return onnx.shape_inference.infer_shapes(model)

def _format_name(name):
    return name.rstrip(":0").rstrip("_Y")

def _name(node):
    #return _format_name( node.name if node.name else node.output[0] )
    return _format_name( node.output[0] )

def get_model_node(model, name, submodels=[]):
    for node in model.graph.node:
        if _name(node) == name: # formatted match
            return node
    for sm in submodels: #look through submodels
        for subnode in sm.g.node: #g used in subgraphs for graph
            if _name(subnode) == name: # formatted match
                return subnode
    raise NameError("Node name not in graphs")

def get_model_value_info(model, name, submodels=[]):
    for node in model.graph.value_info:
        if _format_name(node.name) == name: # formatted match
            return node
    for sm in submodels: #look through submodels
        for subnode in sm.g.value_info: #g used in subgraphs for graph
            if _format_name(subnode.name) == name: # formatted match
                return subnode

def get_model_input(model, name, submodels=[]):
    for node in model.graph.input:
        if node.name == name: # exact match
            return node
    for sm in submodels: #look through submodels
        for subnode in sm.g.value_info: #g used in subgraphs for graph
            if subnode.name == name: # exact match
                return subnode

def get_model_output(model, name, submodels=[]):
    for node in model.graph.output:
        if node.name == name:
            return node
    for sm in submodels: #look through submodels
        for subnode in sm.g.output: #g used in subgraphs for graph
            if _format_name(subnode.name) == name: # formatted match
                return subnode

def get_model_initializer(model, name, submodels=[], to_tensor=True):
    for node in model.graph.initializer: #works with subgraphs
        if node.name == name: # exact match
            if to_tensor:
                return onnx.numpy_helper.to_array(node)
            else:
                return node
    for sm in submodels: #look through submodels
        for subnode in sm.g.output: #g used in subgraphs for graph
            if subnode.name == name: # exact match
                if to_tensor:
                    return onnx.numpy_helper.to_array(subnode)
                else:
                    return subnode

def _format_attr(attribute):
    attr_out = {}
    for attr in attribute:
        if attr.type == 7: # (INTS) TODO: find enumeration
            attr_out[attr.name] = [ int(i) for i in attr.ints ]
    return attr_out

def _out_dim(model, submodels, name):
    dim = [0,0,0]
    value_info = get_model_value_info(model, name, submodels)
    if value_info == None:
        #try looking through outputs - required for subgraphs
        value_info = get_model_output(model, name, submodels)
    if len(value_info.type.tensor_type.shape.dim) == 4:
        #dim[0] = int(node.type.tensor_type.shape.dim[0].dim_value) # batch size
        dim[0] = int(value_info.type.tensor_type.shape.dim[1].dim_value) # channels
        dim[1] = int(value_info.type.tensor_type.shape.dim[2].dim_value) # rows
        dim[2] = int(value_info.type.tensor_type.shape.dim[3].dim_value) # cols
        return dim
    elif len(value_info.type.tensor_type.shape.dim) == 2:
        #dim[0] = int(node.type.tensor_type.shape.dim[0].dim_value) # batch size
        dim[0] = int(value_info.type.tensor_type.shape.dim[1].dim_value) # channels
        dim[1] = 1 # rows
        dim[2] = 1 # cols
        return dim

def get_ValueInfoProto_from_node(graph, node, no_output=False):
    # return ValueInfoProto associated with the node provided
    # search the inputs,value_info,outputs
    if no_output:
        for seq in (graph.value_info, graph.input):
            for VIP in seq:
                if VIP.name == node.output[0]: #FIXME for multi outputs
                    return VIP
    else:
        for seq in (graph.value_info, graph.output, graph.input):
            for VIP in seq:
                if VIP.name == node.output[0]: #FIXME for multi outputs
                    return VIP
    raise NameError("Node value info not found in graph\n", node)
