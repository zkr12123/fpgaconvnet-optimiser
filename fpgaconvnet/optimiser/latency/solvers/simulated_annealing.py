import os
import numpy as np
import json
import copy
import random
import math
from dataclasses import dataclass
import wandb
import pandas as pd

from fpgaconvnet.optimiser.latency.solvers.solver import LatencySolver

LATENCY     =   0
THROUGHPUT  =   1

START_LOOP  =   1000

@dataclass
class LatencySimulatedAnnealing(LatencySolver):
    T: float = 10.0
    k: float = 10.0
    T_min: float = 0.0001
    cool: float = 0.98
    transform_iterations: int = 15
    """
    Randomly chooses a transform and hardware component to change.
    The change is accepted based on a probability-based decision function
    """

    def run_solver(self, log=True):

        # get all the layer types in the network
        layer_types = list(set([ self.net.graph.nodes[node]["type"] \
                for node in self.net.graph.nodes ]))

        # combine all the layer_types
        for layer_type in layer_types:
            self.combine(layer_type, num_nodes=-1)

        # apply min shape to all hardware nodes
        for hw_node in self.building_blocks:
            self.apply_min_shape(hw_node)

        # check the intial design is within constraints
        try:
            self.check_resources()
            self.check_building_blocks()
        except AssertionError as error:
            print("ERROR: Exceeds resource usage")
            return

        # Cooling Loop
        while self.T_min < self.T:

            # get the current cost
            cost = self.get_cost()

            # Save previous building blocks
            building_blocks = copy.deepcopy(self.building_blocks)

            # several transform iterations per cool down
            for _ in range(self.transform_iterations):

                # Apply a transform
                ## Choose a random transform
                transform = random.choice(self.transforms)

                ## Choose a random building block
                hw_node = random.choice(list(self.building_blocks.keys()))

                ## Choose a random execution node
                exec_node = random.choice(list(self.net.graph.nodes()))

                ## Apply the transform
                self.apply_transform(transform, hw_node, exec_node)

            # Check resources
            try:
                self.check_resources()
                self.check_building_blocks()
            except AssertionError:
                # revert to previous state
                self.building_blocks = building_blocks
                continue

            # Simulated annealing descision
            curr_cost = self.get_cost()
            status_cost = curr_cost
            if curr_cost < cost:
                # accept new state
                pass
            else:
                if math.exp((cost - curr_cost)/(self.k*self.T)) < random.uniform(0,1):
                    # revert to previous state
                    self.building_blocks = building_blocks
                    status_cost = cost

            # print solver status
            self.solver_status(self.T, cost=status_cost)

            # wandb logging and checkpoint
            if log:

                self.wandb_log(temperature=self.T,
                    num_blocks=len(self.building_blocks),
                    latency=status_cost,
                    **self.get_resources_util())

            # reduce temperature
            self.T *= self.cool

        if log:
            # get config and report
            config = self.config()
            report = self.report()

            # get per layer table
            per_layer_table = {
                "exec_node": [],
                "hw_node": [],
                "type": [],
                "latency": [],
                "repetitions": [],
                "iteration_space": [],
            }
            for exec_node, per_layer_report in report["per_layer"].items():
                per_layer_table["exec_node"].append(exec_node)
                per_layer_table["hw_node"].append(per_layer_report["hw_node"])
                per_layer_table["type"].append(per_layer_report["type"])
                per_layer_table["latency"].append(per_layer_report["latency"])
                per_layer_table["repetitions"].append(per_layer_report["repetitions"])
                per_layer_table["iteration_space"].append(per_layer_report["iteration_space"])

            self.wandb_log(per_layer=wandb.Table(data=pd.DataFrame(per_layer_table)))

            # save report and config
            if not os.path.exists("tmp"):
                os.makedirs("tmp")
            with open("tmp/config.json", "w") as f:
                json.dump(config, f, indent=2)
            with open("tmp/report.json", "w") as f:
                json.dump(report, f, indent=2)

            # save them as artifacts
            artifact = wandb.Artifact('outputs', type='json')
            artifact.add_file("tmp/config.json") # Adds multiple files to artifact
            artifact.add_file("tmp/report.json") # Adds multiple files to artifact
            wandb.log_artifact(artifact)
            # self.wandb_checkpoint()

        print(f"Final cost: {self.get_cost():.4f}")
        print(f"Final resources: {self.get_resources_util()}")
        print(f"Final building blocks: {list(self.building_blocks.keys())}")

        # # store dataframe of
        # # https://docs.wandb.ai/guides/data-vis/log-tables
        # table = wandb.Table(columns=[])
        # for i, partition in enumerate(self.net.partitions):
        #     table.add_data([])
        # wandb.log({"partitions": table})

        # store image
        # wandb.log({"image": wandb.Image(path_to_image)})
        # wandb.log("plot": plt)