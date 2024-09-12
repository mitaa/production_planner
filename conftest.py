# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from production_planner.core import CONFIG

import os
from pathlib import Path
import tempfile
import shutil

import pytest


@pytest.fixture(autouse=True)
def config(request):
    dpath_test = Path(os.path.dirname(request.module.__file__))
    dpath_data = Path(tempfile.mkdtemp(prefix="production_planner_data_folder")) / "data_folder"

    if "empty_data_folder" not in request.keywords:
        shutil.copytree(dpath_test / "__data_folder__", dpath_data)

    CONFIG.dpath_data = dpath_data
    return CONFIG


def pytest_addoption(parser):
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    config.addinivalue_line("markers", "empty_data_folder: mark test to start with an uninitialized environment")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
