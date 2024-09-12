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
from .io import PlannerManager

from pathlib import Path
import importlib.metadata
import traceback

from docopt import docopt

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer


__version__ = importlib.metadata.version("production_planner")


# The Fuel Generator, like all power generation buildings, behaves differently to power consumer buildings when overclocked. A generator overclocked to 250% only operates 202.4% faster[EA] (operates 250% faster[EX]).
# As the fuel consumption rate is directly proportional to generator power production, verify that demand matches the production capacity to ensure that Power Shards are used to their full potential. Fuel efficiency is unchanged, but consumption and power generation rates may be unexpectedly uneven[EA].


class Planner(App):
    CSS_PATH = "Planner.tcss"
    header = None

    def __init__(self, testrun=False, *args, **kwargs):
        # Suppresses toasts that differ based on test environment
        self._testrun = testrun
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield Header()
        yield PlannerTable()
        yield Footer()

    def is_table_shown(self, table: PlannerTable) -> bool:
        raise NotImplemented

    def on_mount(self) -> None:
        core.APP = self
        self.app.active_table = self.query_one(PlannerTable)
        self.manager = PlannerManager(self, iid_name="main")
        self.manager.load()

    def swap_active_table(self, new_table):
        self.active_table.remove()

        self.active_table = new_table
        self.mount(self.active_table, after=self.query_one(Header))
        self.active_table.sink.load()
        self.active_table.update()

    def exit(self, *args):
        # NOTE: saving here for shutdown since it will be missed by pytest if it's in the `def main()`
        self.manager.staging_commit()
        CONFIG.store.sync()
        super().exit(*args)


def main():
    arguments = docopt(__doc__, version=__version__)
    if arguments["--data-folder"]:
        CONFIG.dpath_data = Path(arguments["--data-folder"]).absolute()

    planner = Planner()
    try:
        planner.app.run()
    except BaseException:
        # TODO: maybe move the try-except into the App.{run, run_test, etc} instead
        # NOTE: saving here since `App.exit` doesn't seem to run when an Exception is encountered ...
        planner.manager.staging_commit()
        CONFIG.store.sync()
        print(traceback.format_exc())
    finally:
        ...


if __name__ == "__main__":
    main()
