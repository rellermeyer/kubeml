from abc import ABC, abstractmethod
from dataclasses import dataclass
from dataclasses_json import dataclass_json, Undefined, CatchAll
from typing import List, Dict, Any
import logging
import subprocess
import time


@dataclass_json
@dataclass
class TrainOptions:
    default_parallelism: int
    static_parallelism: bool
    validate_every: int
    K: int
    goal_accuracy: float


@dataclass_json
@dataclass
class TrainRequest:
    """ Request holding the settings to run an experiment
    in Kubeml"""
    model_type: str
    batch_size: int
    epochs: int
    dataset: str
    lr: float
    function_name: str
    options: TrainOptions


@dataclass_json
@dataclass
class TrainMetrics:
    validation_loss: List[float]
    accuracy: List[float]
    train_loss: List[float]
    parallelism: List[int]
    epoch_duration: List[float]


@dataclass_json
@dataclass
class History:
    id: str
    task: TrainRequest
    data: TrainMetrics


class Experiment(ABC):

    def __init__(self, title: str):
        self.title = title

    @abstractmethod
    def run(self):
        pass


class KubemlExperiment(Experiment):
    def __init__(self, title, request: TrainRequest):
        super(KubemlExperiment, self).__init__(title=title)
        self.request = request

        # Network ID is created when task is started through the CLI
        self.network_id = None

    def run(self):
        """ RUn an experiment on KubeML

        - create the train task
        - watch until it finishes
        - load the history
        - TODO save the history somewhere
        """
        self.network_id = self.run_task()
        self.wait_for_task_finished()
        history = self.get_model_history()

        print(history.to_json())

        # TODO save the history in the file related to the experiment title

    def wait_for_task_finished(self):
        while True:
            done = self.check_if_task_finished()
            if done:
                return
            time.sleep(2)

    def run_task(self) -> str:
        """ Runs a task and returns the id assigned by kubeml"""
        command = f"kubeml train  \
                    --function {self.request.function_name} \
                    --dataset {self.request.dataset} \
                    --epochs {self.request.epochs} \
                    --batch {self.request.batch_size} \
                    --lr {self.request.lr}"
        print("starting training with command", command)

        res = subprocess.run(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.check_stderr(res)

        id = res.stdout.decode()

        print("Received id", id)
        return id

    def check_if_task_finished(self) -> bool:
        """Check if the task is the the list of running tasks"""
        command = "kubeml task list --short"
        print("Checking running tasks"), command

        res = subprocess.run(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.check_stderr(res)

        # get all the tasks running
        tasks = res.stdout.decode().splitlines()

        for id in tasks:
            if id == self.network_id:
                return True
        return False

    def get_model_history(self) -> History:
        """Gets the training history for a certain model"""
        command = f"kubeml history get --network {self.network_id}"
        print("Getting model history with command", command)

        res = subprocess.run(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.check_stderr(res)

        print("got history", res.stdout.decode())

        # decode the json to the history
        h = History.from_json(res.stdout.decode())

        print(h)
        return h

    @staticmethod
    def check_stderr(res: subprocess.CompletedProcess):
        if len(res.stderr) == 0:
            return
        print("error running command", res.args, res.stderr.decode())
        exit(-1)


class TensorflowExperiment(Experiment):
    pass
