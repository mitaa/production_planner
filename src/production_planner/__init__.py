#! /bin/env python
# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Production Planner

Usage:
  production_planner
  production_planner --data-folder=<dpath>
  production_planner (-h | --help)
  production_planner --version

Options:
  -h --help             Show this screen.
  --version             Show version.
  --data-folder=<dpath> Use the specified folder-path as data-folder for this session

"""

from . import core
from .core import CONFIG

from .datatable import PlannerTable

from pathlib import Path
import importlib.metadata

from docopt import docopt

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer


__version__ = importlib.metadata.version("production_planner")


# The Fuel Generator, like all power generation buildings, behaves differently to power consumer buildings when overclocked. A generator overclocked to 250% only operates 202.4% faster[EA] (operates 250% faster[EX]).
# As the fuel consumption rate is directly proportional to generator power production, verify that demand matches the production capacity to ensure that Power Shards are used to their full potential. Fuel efficiency is unchanged, but consumption and power generation rates may be unexpectedly uneven[EA].


class Planner(App):
    CSS_PATH = "Planner.tcss"

    def compose(self) -> ComposeResult:
        yield Header()
        yield PlannerTable()
        yield Footer()

    def on_mount(self) -> None:
        core.APP = self
        self.title = CONFIG.store["last_file"]
        self.table = self.query_one(PlannerTable)
        self.table.master_table = True
        self.table.load_data(skip_on_nonexist=True)
        self.table.update()


def main():
    arguments = docopt(__doc__, version=__version__)
    if arguments["--data-folder"]:
        CONFIG.dpath_data = Path(arguments["--data-folder"]).absolute()

    planner = Planner()
    try:
        planner.run()
    finally:
        planner.table.save_data()
        CONFIG.store.sync()


if __name__ == "__main__":
    main()
