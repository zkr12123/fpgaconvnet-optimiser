import sys
import numpy as np
import json
import copy
import random
import math
from dataclasses import dataclass

from fpgaconvnet.optimiser.solvers import Solver

LATENCY   =0
THROUGHPUT=1

START_LOOP=1000

@dataclass
class SimulatedAnnealing(Solver):
    T: float = 10.0
    k: float = 0.001
    T_min: float = 0.0001
    cool: float = 0.97
    iterations: int = 10
    """
Randomly chooses a transform and hardware component to change. The change is accepted based on a probability-based decision function
    """

    # def __init__(self,name,network_path,T=10.0,k=0.001,T_min=0.0001,cool=0.97,iterations=10):

    #     # Initialise Network
    #     Solver.__init__(self,name,network_path)

    #     # Simulate Annealing Variables
    #     self.T          = T
    #     self.k          = k
    #     self.T_min      = T_min
    #     self.cool       = cool
    #     self.iterations = iterations

    # def solver_status(self):
    #     # objective
    #     objectives = ['latency','throughput']
    #     objective  = objectives[self.objective]
    #     # cost
    #     cost = self.get_cost()
    #     # Resources
    #     resources = [ partition.get_resource_usage() for partition in self.net.partitions ]
    #     BRAM = max([ resource['BRAM'] for resource in resources ])
    #     DSP  = max([ resource['DSP']  for resource in resources ])
    #     LUT  = max([ resource['LUT']  for resource in resources ])
    #     FF   = max([ resource['FF']   for resource in resources ])
    #     sys.stdout.write("\033[K")
    #     print("TEMP:\t {temp}, COST:\t {cost} ({objective}), RESOURCE:\t {BRAM}\t{DSP}\t{LUT}\t{FF}\t(BRAM|DSP|LUT|FF)".format(
    #         temp=self.T,cost=cost,objective=objective,BRAM=int(BRAM),DSP=int(DSP),LUT=int(LUT),FF=int(FF)),end='\n')#,end='\r')

    def run_solver(self, log=True):

        # update all partitions
        self.net.update_partitions()

        # Setup
        cost = self.get_cost()

        start = False

        try:
            self.check_resources()
            self.check_constraints()
            start = True
        except AssertionError as error:
            print("WARNING: Exceeds resource usage (trying to find valid starting point)")

        # Attempt to find a good starting point
        if not start:
            for i in range(START_LOOP):
                transform = random.choice(self.transforms)
                self.apply_transform(transform)
                self.net.update_partitions()

                try:
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
            self.net.update_partitions()

            # get the current cost
            cost = self.get_cost()

            # Save previous iteration
            net = copy.deepcopy(self.net)

            # several iterations per cool down
            for _ in range(self.iterations):

                # update partitions
                self.net.update_partitions()

                # remove all auxiliary layers
                for i in range(len(self.net.partitions)):
                    self.net.partitions[i].remove_squeeze()

                # Apply a transform
                ## Choose a random transform
                transform = random.choice(self.transforms)

                ## Choose a random partition
                partition_index = random.randint(0,len(self.net.partitions)-1)

                ## Choose a random node in partition
                node = random.choice(list(self.net.partitions[partition_index].graph))

                ## Apply the transform
                self.apply_transform(transform, partition_index, node)

                ## Update partitions
                self.net.update_partitions()

            # Check resources
            try:
                self.check_resources()
                self.check_constraints()
            except AssertionError:
                # revert to previous state
                self.net = net
                continue

            # Simulated annealing descision
            if math.exp(min(0,(cost - self.get_cost())/(self.k*self.T))) < random.uniform(0,1):
                # revert to previous state
                self.net = net

            # print solver status
            self.solver_status()

            # reduce temperature
            self.T *= self.cool