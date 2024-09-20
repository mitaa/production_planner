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
from .help import HelpScreen
from .header import Header

from pathlib import Path
import importlib.metadata
import traceback
from typing import Iterable

from docopt import docopt

from textual.app import (
    App,
    SystemCommand,
    ComposeResult
)
from textual.screen import Screen
from textual.widgets import Footer
from textual.reactive import reactive

__version__ = importlib.metadata.version("production_planner")


# The Fuel Generator, like all power generation buildings, behaves differently to power consumer buildings when overclocked. A generator overclocked to 250% only operates 202.4% faster[EA] (operates 250% faster[EX]).
# As the fuel consumption rate is directly proportional to generator power production, verify that demand matches the production capacity to ensure that Power Shards are used to their full potential. Fuel efficiency is unchanged, but consumption and power generation rates may be unexpectedly uneven[EA].


def planner_command(title, help, callback, discover=True) -> SystemCommand:
    help = "   " + help
    return SystemCommand(title, help, callback, discover)


class Planner(App):
    CSS_PATH = "Planner.tcss"
    header = None

    BINDINGS = [
        ("h", "help", "Help")
    ]

    hidden_item_count = reactive(0)

    def __init__(self, testrun=False, *args, **kwargs):
        # Suppresses toasts that differ based on test environment
        self._testrun = testrun
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield Header(icon="Menu")
        yield PlannerTable(header_control=True)
        yield Footer()

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        for command in super().get_system_commands(screen):
            if command.title.lower() == "light mode":
                continue
            yield planner_command(*command)
        yield planner_command("Save As", "Save the currently active file with a new filename", self._save_as)
        yield planner_command("Load", "Load a new file in the currently active table", self._load)
        yield planner_command("Delete", "Delete a file from the filesystem", self._delete)
        # 3, because the command-palette is the second screen
        if len(self.screen_stack) < 3:
            yield planner_command("Dataview", "Shows the corresponding yaml source of the open file", self._dataview)

    def _save_as(self):
        if not self.focused_table:
            return
        self.call_next(self.focused_table.action_save)

    def _load(self):
        if not self.focused_table:
            return
        # NOTE: directly calling `action_load` somehow causes the Screen callback not to be invoked
        self.call_next(self.focused_table.action_load)

    def _delete(self):
        if not self.focused_table:
            return
        self.call_next(self.focused_table.action_delete)

    def _dataview(self):
        if not self.focused_table or len(self.screen_stack) > 2:
            return
        self.call_next(self.focused_table.action_dataview)

    def is_table_shown(self, table: PlannerTable) -> bool:
        raise NotImplemented

    def on_mount(self) -> None:
        core.APP = self
        self.app.focused_table = self.query_one(PlannerTable)
        self.manager = PlannerManager(self, iid_name="main")
        self.manager.load()
        if core.CONFIG.store["app"]["startup_help"]:
            core.CONFIG.store["app"]["startup_help"] = False
            self.action_help(True)

    def swap_active_table(self, new_table):
        # FIXME: fix when implementing tabbed content ...
        self.focused_table.remove()

        self.focused_table = new_table
        self.mount(self.focused_table, after=self.query_one(Header))
        self.focused_table.sink.load()
        self.focused_table.update()

    def exit(self, *args):
        # NOTE: saving here for shutdown since it will be missed by pytest if it's in the `def main()`
        self.manager.staging_commit()
        CONFIG.store.sync()
        super().exit(*args)

    def action_help(self, startup_help=False) -> None:
        table = self.focused_table

        def set_focused_table(*_):
            self.focused_table = table

        self.push_screen(HelpScreen(startup_help=startup_help), set_focused_table)

    def check_action(self, action: str, parameters: tuple[object, ...]):
        is_main_screen = len(self.app.screen_stack) == 1
        # this is always keep inherited (?) bindings like tab switching between widgets
        is_my_binding = action in [binding for (_, binding, _) in self.__class__.BINDINGS]
        return is_main_screen or (not is_my_binding)


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
