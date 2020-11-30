"""
Defines the config used for the becnchmark
"""
# https://github.com/PyCQA/pylint/issues/3876
# pylint: skip-file
from typing import TypedDict, List, Tuple, Dict, Any
from jobs import SelectorJob

class BenchmarkConfig(TypedDict):
    id: str
    dir: str
    username: str
    seeds: List[int]
    times_in_mins: List[int]
    openml_tasks: List[int]
    data_splits: List[Tuple[float, float, float]]
    algorithms: List[str]
    selectors: List[Dict[str, Any]]
    baselines: Dict[str, int]

default_config: BenchmarkConfig = {
    "id": "tpot_bench",
    "username": "eb130475",
    "dir": "./data",
    "seeds": [5],
    "openml_tasks": [3, 6, 11, 12, 14, 15, 16, 18, 22, 23],
    "times_in_mins" : [30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330, 360],
    "data_splits": [
        (0.5, 0.3, 0.2)
    ],
    "algorithms": [ "NB", "TR", "KNN", "MLP", "LR", "XGB", "SVM", "SGD" ],
    "selectors": [
            { "name": "ALL", "type": "all", },
            { "name": "TOP3", "type": "top_n", "n": 3, },
            { "name": "TOP4", "type": "top_n", "n": 4, },
            { "name": "TOP5", "type": "top_n", "n": 5, },
            { "name": "LO3", "type": "n_least_overlapping", "n": 3, },
            { "name": "LO4", "type": "n_least_overlapping", "n": 4, },
            { "name": "LO5", "type": "n_least_overlapping", "n": 5, },
            { "name": "MC3", "type": "n_most_coverage", "n": 3, },
            { "name": "MC4", "type": "n_most_coverage", "n": 4, },
            { "name": "MC5", "type": "n_most_coverage", "n": 5, },
            { "name": "RAN3", "type": "n_random_selection", "n": 3,
             "selection_seeds": [1,2,3], },
            { "name": "RAN4", "type": "n_random_selection", "n": 4,
             "selection_seeds": [1,2,3], },
            { "name": "RAN5", "type": "n_random_selection", "n": 5,
             "selection_seeds" : [1,2,3], },
    ],
    "baselines": {
        # Determines how much to increase time in minutes by for a fair
        # comparison #TODO explain better
        "scale": 8,
    }
}
