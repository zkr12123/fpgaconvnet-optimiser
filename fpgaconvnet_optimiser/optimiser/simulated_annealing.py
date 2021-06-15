import sys
import numpy as np
import json
import copy
import random
import math

from fpgaconvnet_optimiser.optimiser.optimiser import Optimiser

LATENCY   =0
THROUGHPUT=1

START_LOOP=1000

class SimulatedAnnealing(Optimiser):
    """
Randomly chooses a transform and hardware component to change. The change is accepted based on a probability-based decision function
    """
    
    def __init__(self,name,network_path,T=10.0,k=0.001,T_min=0.0001,cool=0.97,iterations=10):

        # Initialise Network
        Optimiser.__init__(self,name,network_path)

        # Simulate Annealing Variables
        self.T          = T
        self.k          = k
        self.T_min      = T_min
        self.cool       = cool
        self.iterations = iterations

    def optimiser_status(self):
        # objective
        objectives = ['latency','throughput']
        objective  = objectives[self.objective]
        # cost 
        cost = self.get_cost()
        # Resources
        resources = [ partition.get_resource_usage() for partition in self.partitions ]
        BRAM = max([ resource['BRAM'] for resource in resources ])
        DSP  = max([ resource['DSP']  for resource in resources ])
        LUT  = max([ resource['LUT']  for resource in resources ])
        FF   = max([ resource['FF']   for resource in resources ])
        sys.stdout.write("\033[K")
        print("TEMP:\t {temp:0.4}, COST:\t {cost:0.4},{test:0.4} ({objective}), RESOURCE:\t {BRAM}\t{DSP}\t{LUT}\t{FF}\t(BRAM|DSP|LUT|FF)".format(
            temp=self.T,cost=cost,test=self.get_throughput(),objective=objective,BRAM=int(BRAM),DSP=int(DSP),LUT=int(LUT),FF=int(FF)),end='\n')#,end='\r')

    def run_optimiser(self, log=True):
       
        # update all partitions
        self.update_partitions()
        self.update_partition_index()
        # Setup
        cost = self.get_cost()       

        start = False

        try: 
            self.check_resources()
            self.check_constraints()
            start = True
        except AssertionError as error:
            print("ERROR: Exceeds resource usage (trying to find valid starting point)")
        
        # Attempt to find a good starting point
        if not start:
            for i in range(START_LOOP):
                transform = random.choice(self.transforms)
                self.apply_transform(transform)
                self.update_partitions()

                try:
                    #self.validate_network()
                    self.check_resources()
                    self.check_constraints()
                    break
                except AssertionError as error:
                    pass

        try: 
            self.check_resources()
            self.check_constraints()
        except AssertionError as error:
            print("ERROR: Exceeds resource usage")
            return
         
        # Cooling Loop
        while self.T_min < self.T:
            
            # update partitions
            self.update_partitions()

            # get the current cost
            cost = self.get_cost()
            
            # Save previous iteration
            partitions = copy.deepcopy(self.partitions)
            groups = copy.deepcopy(self.groups)

            # several iterations per cool down
            for _ in range(self.iterations):

                # update partitions
                self.update_partitions()

                # remove all auxiliary layers
                for i in range(len(self.partitions)):
                    self.partitions[i].remove_squeeze()

                # Apply a transform
                ## Choose a random transform
                transform = random.choice(self.transforms)

                ## Choose a random partition
                partition_index = random.randint(0,len(self.partitions)-1)
 
                ## Choose a random node in partition
                node = random.choice(list(self.partitions[partition_index].graph))
                
                ## Apply the transform
                self.apply_transform(transform, partition_index, node)
            
                ## Update partitions
                self.update_partitions()
                #print("Mid run partitions:",len(self.partitions))
                #print("Mid run groups    :",self.groups)

            # Check resources
            try: 
                self.validate_network()
                self.check_constraints()
            except AssertionError:
                # revert to previous state
                #print("ERROR: Exceeds resource usage")
                self.groups = groups
                self.partitions = partitions
                continue

            # Simulated annealing descision
            if math.exp(min(0,(cost - self.get_cost())/(self.k*self.T))) < random.uniform(0,1):
                # revert to previous state

                self.groups = groups
                self.partitions = partitions

            # update cost
            if self.DEBUG:
                self.optimiser_status()
            # reduce temperature
            self.T *= self.cool

        self.get_multi_fpga_throughput()
        self.get_max_interval()
        print("Latency:{}, Reconfiguration time: {}".format(self.get_latency(),(math.ceil(len(self.partitions)/len(self.cluster))-1)*self.platform["reconf_time"]))
        #print(self.groups)
        for i,partition in enumerate(self.partitions):
            print("Partition {} has communication interval in:{},out:{},through:{}, bandwidth in:{}, out:{}".format(i, 
                                                                                                                    partition.get_comm_interval_in(partition.get_id()!=len(self.partitions)-1 and partition.get_id()!=0),
                                                                                                                    partition.get_comm_interval_out(partition.get_id()!=len(self.partitions)-1 and partition.get_id()!=0),
                                                                                                                    partition.get_interval(),
                                                                                                                    partition.get_bandwidth_in(self.platform["freq"]),
                                                                                                                    partition.get_bandwidth_out(self.platform["freq"])))
        print(len(self.partitions))
