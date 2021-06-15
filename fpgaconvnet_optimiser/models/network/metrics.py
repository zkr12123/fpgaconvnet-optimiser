from sys import platform
import fpgaconvnet_optimiser.tools.graphs as graphs
import math

def get_multi_fpga_throughput(self):
         # return the frames per second
        interval = 0
        for partition in self.partitions:
            if interval < partition.get_interval():
                interval = partition.get_interval()
        print("Throughput based on max interval= {}",1/interval*self.platform["freq"]*1000000)
        #no_weight_reloading = False
        no_weight_reloading = True
        if len(self.cluster)>=len(self.partitions):
            no_weight_reloading = True
            for partition in self.partitions:
                if partition.wr_factor > 1:
                    no_weight_reloading = False
        print("No weight reloading {}".format(no_weight_reloading))
        return 1/interval*self.platform["freq"]*1000000

def get_cluster_latency(self,cluster,freq):
    #print(len(cluster))
    max_interval=0
    latency=0
    batch_size  = int(self.batch_size)
    for i,partition in enumerate(cluster):
        interval = partition.get_interval()
        if partition.get_id() < len(self.partitions)-1 and len(cluster)>1: # Find communication intervals
            two_way_communication = partition.get_id()!=len(self.partitions)-1 and partition.get_id()!=0
            comm_interval_out = partition.get_comm_interval_out(comm_in=two_way_communication)
            next_comm_interval_in = self.partitions[self.get_next_partition(partition.get_id())].get_comm_interval_in(comm_out=two_way_communication)
            max_interval = max(max_interval,interval,comm_interval_out,next_comm_interval_in) 
        else:
            max_interval = max(max_interval,interval)
        # get pipeline depth of partition
        input_node = graphs.get_input_nodes(partition.graph)[0]
        pipeline_depth = partition.get_pipeline_depth(input_node) # TODO: find max of all input nodes
        # return the latency (in seconds)
        wr_factor   = partition.wr_factor
        size_wr     = partition.size_wr
        latency += (pipeline_depth*wr_factor + (wr_factor-1)*(size_wr+batch_size*interval))/(freq*1000000)
    latency += max_interval*batch_size/(freq*1000000)
    
    return latency

def get_latency(self):
        latency = 0
        # iterate over partitions:
        for partition in self.partitions:
            # accumulate latency for each partition
            latency += partition.get_latency(self.platform["freq"])
        # return the total latency as well as reconfiguration time
        if (len(self.partitions)>1):
            latency+=len(self.partitions)*self.platform["reconf_time"]
        return latency 

def get_single_sample_latency(self):
        latency = 0
        # iterate over partitions:
        for partition in self.partitions:
            # accumulate latency for each partition
            if partition.get_id()<len(self.partitions)-1:
                latency += partition.get_latency(self.platform["freq"])
            else:
                interval=partition.get_interval()
                batch_size= self.batch_size
                frequency =self.platform["freq"]
                # get pipeline depth of partition
                input_node = graphs.get_input_nodes(partition.graph)[0]
                pipeline_depth = partition.get_pipeline_depth(input_node) # TODO: find max of all input nodes
                # return the latency (in seconds)
                wr_factor   = partition.wr_factor
                size_wr     = partition.size_wr
                latency += (pipeline_depth*wr_factor + (wr_factor-1)*(size_wr+batch_size*interval))/(frequency*1000000)

        # return the total latency as well as reconfiguration time
        return latency + (len(self.partitions)-1)*self.platform["reconf_time"]

def get_cluster_grouping_batch_latency(self):
    latency = 0
    # iterate over partitions:
    if len(self.cluster)<len(self.partitions):
        for i in range(math.ceil(len(self.partitions)/len(self.cluster))):
            # accumulate latency for each partition
            cluster = self.partitions[i*len(self.cluster):min((i+1)*len(self.cluster),len(self.partitions))]
            latency += self.get_cluster_latency(cluster,self.platform["freq"])
    else:
        latency = max([partition.get_latency(self.platform["freq"])+(partition.get_comm_interval_out(1)+ partition.get_comm_interval_in(1))/(self.platform["freq"]*1000000) for partition in self.partitions])
    # return the total latency as well as reconfiguration time
    return latency + (math.ceil(len(self.partitions)/len(self.cluster))-1)*self.platform["reconf_time"]

def get_cluster_grouping_single_sample_latency(self):
    latency = 0
    frequency = self.platform["freq"]
    # Get cluster latency for first n-1 clusters
    n_clusters = math.ceil(len(self.partitions)/len(self.cluster))
    for i in range(n_clusters-1):
        # accumulate latency for each partition
        cluster = self.partitions[i*len(self.cluster):min((i+1)*len(self.cluster),len(self.partitions))]
        latency += self.get_cluster_latency(cluster,frequency)
        #print(i)
    # Get latency for last cluster
    last_cluster = self.partitions[(n_clusters-1)*len(self.cluster):len(self.partitions)]
    batch_size = self.batch_size
    max_interval = 0        
    for i,partition in enumerate(last_cluster):
            # get the interval for the partition
        interval = partition.get_interval()
        if partition.get_id() < len(self.partitions)-1:
            #print("N partitions:{},partition_id{}".format(len(self.partitions),partition.get_id()))
            two_way_communication=partition.get_id()!=len(self.partitions)-1 and partition.get_id()!=0
            comm_interval_out = partition.get_comm_interval_out(two_way_communication)
            next_comm_interval_in = self.partitions[self.get_next_partition(partition.get_id())].get_comm_interval_in(two_way_communication)
            max_interval = max(max_interval,interval,comm_interval_out,next_comm_interval_in) 
        else:
            max_interval = max(max_interval,interval)
        print("max interval:",max_interval,i,partition.get_id())
        # get pipeline depth of partition
        input_node = graphs.get_input_nodes(partition.graph)[0]
        pipeline_depth = partition.get_pipeline_depth(input_node) # TODO: find max of all input nodes
        # return the latency (in seconds)
        wr_factor   = partition.wr_factor
        size_wr     = partition.size_wr
        latency += (pipeline_depth*wr_factor + (wr_factor-1)*(size_wr+batch_size*interval))/(frequency*1000000)
    #latency += max_interval/(frequency*1000000)
    # return the total latency as well as reconfiguration time
    return latency + (math.ceil(len(self.partitions)/len(self.cluster))-1)*self.platform["reconf_time"]

def get_throughput(self):
    return float(self.batch_size)/self.get_latency()

def get_cluster_grouping_throughput(self):
    return float(self.batch_size)/self.get_cluster_grouping_batch_latency()

def get_max_interval(self):
    max_interval=0
    for i in range(math.ceil(len(self.partitions)/len(self.cluster))):
        # accumulate latency for each partition
        cluster = self.partitions[i*len(self.cluster):min((i+1)*len(self.cluster),len(self.partitions))]
        print("Cluster {} max interval :{}".format(i,self.get_cluster_interval(cluster)))
        max_interval = max(max_interval,self.get_cluster_interval(cluster))
    print("Max interval:{}".format(max_interval))

def get_cluster_interval(self,cluster):
    max_interval=0
    latency=0
    batch_size  = int(self.batch_size)
    for i,partition in enumerate(cluster):
            # get the interval for the partition
        interval = partition.get_interval()
        if (partition.get_id() < len(self.partitions) and len(cluster)>1 and partition.platform["connections_out"][0]!=partition.platform["id"]):
            
            #print("N partitions:{},partition_id{}".format(len(self.partitions),partition.get_id()))
            two_way_communication = partition.get_id()!=len(self.partitions)-1 and partition.get_id()!=0
            comm_interval_out = partition.get_comm_interval_out(two_way_communication)
            next_comm_interval_in = self.partitions[self.get_next_partition(partition.get_id())].get_comm_interval_in(two_way_communication)
            max_interval = max(max_interval,interval,comm_interval_out,next_comm_interval_in) 
        else:
            max_interval = max(max_interval,interval)
    return max_interval


def get_group_latency(self,group_index):
    latency = 0
    for position,partition_id in enumerate(self.groups[group_index]):
        partition=self.partitions[partition_id]
        latency += partition.get_latency(self.platform["freq"])
        if position == 0 and group_index>0:
            latency += partition.get_comm_interval_in(1)/(self.platform["freq"]*1000000)*self.batch_size
        if position == len(self.groups[group_index])-1 and group_index<len(self.groups)-1:
            latency += partition.get_comm_interval_out(1)/(self.platform["freq"]*1000000)*self.batch_size
    if len(self.groups[group_index])>1:
        latency += (len(self.groups[group_index]))*self.platform["reconf_time"]
    return latency

def get_fpga_grouping_latency(self):
    latency=0
    for group in self.groups:
        latency+=self.get_group_latency(group)
    return latency

def get_fpga_grouping_throughput(self):
    max_latency=0
    for group in self.groups:
        max_latency=max(max_latency,self.get_group_latency(group))
    return self.batch_size/max_latency

def get_fpga_grouping_single_sample_latency(self):
    latency=0
    for group_id in self.groups:
        if group_id<len(self.groups)-1:
            latency += self.get_group_latency(group_id)
        else:
            for partition_id in self.groups[group_id]:
                partition=self.partitions[partition_id]
                if partition_id<len(self.partitions)-1:
                    latency += partition.get_latency(self.platform["freq"])
                else:
                    interval = partition.get_interval()
                    input_node = graphs.get_input_nodes(partition.graph)[0]
                    pipeline_depth = partition.get_pipeline_depth(input_node) # TODO: find max of all input nodes
                    # return the latency (in seconds)
                    wr_factor   = partition.wr_factor
                    size_wr     = partition.size_wr
                    latency += (pipeline_depth*wr_factor + (wr_factor-1)*(size_wr+self.batch_size*interval))/(self.platform["freq"]*1000000)

    #latency += (len(self.partitions)-len(self.groups))*self.platform["reconf_time"]
    return latency
