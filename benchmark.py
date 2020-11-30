"""
Manages job objects for the benchmark given a config to work from
"""
# https://stackoverflow.com/questions/33533148/how-do-i-type-hint-a-method-with-the-type-of-the-enclosing-class
from __future__ import annotations

import os
import json
from random import Random
from itertools import chain, product
from typing import (
    Dict, Optional, Iterable, List, Literal, Callable, Any, Mapping, Set
)

from slurmjobmanager import SlurmEnvironment
from slurmjobmanager.job import Job

from bench_config import default_config, BenchmarkConfig
from jobs import SingleAlgorithmJob, BaselineJob, SelectorJob, TPOTJob

cdir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
runner_dir = os.path.join(cdir, 'runners')
single_algorithm_runner = os.path.join(runner_dir, 'single_algorithm_runner.py')
baseline_runner = os.path.join(runner_dir, 'baseline_runner.py')
selector_runner = os.path.join(runner_dir, 'selector_runner.py')

class Benchmark:
    """ #TODO """

    filter_types = Literal['ready', 'failed', 'blocked', 'pending', 'running',
                           'complete', 'in_progress']
    job_filters : Dict[filter_types, Callable[[Job], bool]] = {
        'ready': lambda job: job.ready(),
        'failed': lambda job: job.failed(),
        'blocked': lambda job: job.blocked(),
        'pending': lambda job: job.pending(),
        'running': lambda job: job.running(),
        'complete': lambda job: job.complete(),
        'in_progress': lambda job: job.in_progress(),
    }

    def __init__(
        self,
        config: Optional[BenchmarkConfig] = None
    ) -> None:
        if config is None:
            config = default_config

        self.env = SlurmEnvironment(config['username'])
        self.config = config
        self.folders : Dict[str, str] = {
            'root': os.path.abspath(os.path.join(config['dir'], config['id']))
        }

    @staticmethod
    def from_json(config_path: str) -> Benchmark:
        """
        Create a Benchmark from a path to a json config file

        Params
        ======
        config_path: str
            path to the json config file

        Returns
        =======
        Benchmark
            A benchmark object based on the config parsed
        """
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
            return Benchmark(config)

    def create(self) -> None:
        """ Create the folders required for the benchmark """
        # TODO not sure if the user should have to make the initial dir or not
        if not os.path.exists(self.config['dir']):
            os.mkdir(self.config['dir'])

        if not os.path.exists(self.folders['root']):
            os.mkdir(self.folders['root'])

        for job in self.jobs():
            job.create()

    def run_remaining(self) -> None:
        """ Run the remaining jobs """
        raise NotImplementedError

    def jobs(
        self,
        filter_by : Optional[Benchmark.filter_types] = None
    ) -> Iterable[TPOTJob]:
        """
        Params
        =======
        filter_by : Optional[Literal['complete', 'failed', 'blocked', 'ready',
                                     'pending', 'running', 'in_progress']]
            A filter to apply to the list before returning it
        Returns
        =======
        List[TPOTJob]
            returns a list of jobs based on the config used to create the
            benchmark
        """
        job_iter = chain(
            self.algorithm_jobs(), self.selector_jobs(), self.baseline_jobs()
        )

        # Use the filter if correct
        if filter_by:
            job_filter = Benchmark.job_filters[filter_by]
            return list(filter(job_filter, job_iter))

        return list(job_iter)

    def algorithm_jobs(self) -> List[SingleAlgorithmJob]:
        """
        Returns
        =======
        List[SingleAlgorithmJob]
            returns a list of SingleAlgorithmJobs based on the config
            used to create the benchmark
        """
        config = self.config
        root = self.folders['root']

        seeds = config['seeds']
        times = config['times_in_mins']
        tasks = config['openml_tasks']
        splits = config['data_splits']
        algorithms = config['algorithms']

        return [
            SingleAlgorithmJob(self.env, seed, times, task, root, split, algo,
                               single_algorithm_runner)
            for seed, task, split, algo
            in product(seeds, tasks, splits, algorithms)
        ]

    def baseline_jobs(self) -> List[BaselineJob]:
        """
        Returns
        =======
        List[BaselineJob]
            returns a list of BaselineJob based on the config
            used to create the benchmark
        """
        config = self.config
        root = self.folders['root']

        seeds = config['seeds']
        times = config['times_in_mins']
        tasks = config['openml_tasks']
        splits = config['data_splits']

        # Scale up times to enable fair compute resource comparisons
        # and reduce to unique times
        scale = config['baselines']['scale']

        baseline_times : Set[int] = set()
        for i in range(1, scale+1):
            # pylint: disable=cell-var-from-loop
            scaled_times = set(map(lambda x: x * i, times))
            baseline_times = baseline_times.union(scaled_times)

        return [
            BaselineJob(self.env, seed, list(baseline_times), task, root, split,
                        baseline_runner)
            for seed, task, split
            in product(seeds, tasks, splits)
        ]

    def selector_jobs(self) -> List[SelectorJob]:
        """
        Returns
        =======
        List[SelectorJob]
            returns a list of SingleAlgorithmJobs based on the config
            used to create the benchmark
        """
        functions = {
            'all' : self.selector_jobs_all,
            'top_n': self.selector_jobs_n_top,
            'n_most_coverage': self.selector_jobs_n_most_coverage,
            'n_random_selection': self.selector_jobs_n_random,
            'n_least_overlapping': self.selector_jobs_n_least_overlapping,
        }

        jobs = []
        for selector_config in self.config['selectors']:
            selector_type = selector_config['type']
            get_selector = functions[selector_type]
            jobs += get_selector(selector_config)

        return jobs

    def selector_jobs_all(
        self,
        selector_config: Mapping[str, Any]
    ) -> List[SelectorJob]:
        config = self.config
        root = self.folders['root']

        seeds = config['seeds']
        times = config['times_in_mins']
        tasks = config['openml_tasks']
        splits = config['data_splits']
        algorithms = config['algorithms']

        selector_name = selector_config['name']

        jobs = []
        for seed, task, split in product(seeds, tasks, splits):
            # Create the algorithms the selector will use the results of
            algorithm_jobs = [
                SingleAlgorithmJob(self.env, seed, times, task, root, split,
                                   algo, single_algorithm_runner)
                for algo in algorithms
            ]

            selector_job =  SelectorJob(self.env, seed, times, task, root,
                                        split, selector_runner, selector_name,
                                        algorithm_jobs)
            jobs.append(selector_job)

        return jobs

    def selector_jobs_n_top(
        self,
        selector_config: Mapping[str, Any],
    ) -> List[SelectorJob]:
        # TODO
        return []

    def selector_jobs_n_least_overlapping(
        self,
        selector_config: Mapping[str, Any],
    ) -> List[SelectorJob]:
        # TODO
        return []

    def selector_jobs_n_most_coverage(
        self,
        selector_config: Mapping[str, Any],
    ) -> List[SelectorJob]:
        # TODO
        return []

    def selector_jobs_n_random(
        self,
        selector_config: Mapping[str, Any],
    ) -> List[SelectorJob]:
        config = self.config
        root = self.folders['root']

        seeds = config['seeds']
        times = config['times_in_mins']
        tasks = config['openml_tasks']
        splits = config['data_splits']
        algorithms = config['algorithms']

        n_algorithms = selector_config['n']
        selection_seeds = selector_config['selection_seeds']
        selector_names = [
            f'{selector_config["name"]}_{selection_seed}'
            for selection_seed in selection_seeds
        ]

        jobs = []
        for selection_seed, name in zip(selection_seeds, selector_names):
            rand = Random(selection_seed * n_algorithms)
            random_algorithms : List[str] = \
                rand.sample(algorithms, n_algorithms)

            for seed, task, split in product(seeds, tasks, splits):
                # Create the algorithms the selector will use the results of
                algorithm_jobs = [
                    SingleAlgorithmJob(self.env, seed, times, task, root, split,
                                       algo, single_algorithm_runner)
                    for algo in random_algorithms
                ]
                selector_job =  SelectorJob(self.env, seed, times, task, root,
                                            split, selector_runner,
                                            name, algorithm_jobs)
                jobs.append(selector_job)

        return jobs
