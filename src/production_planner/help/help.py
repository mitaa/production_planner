#! /bin/env python
# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from ..datatable import PlannerTable

import os
from pathlib import Path
import shutil
import tempfile

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, ScrollableContainer
from textual.widgets import Header, Footer, Static, Input

from rich.markdown import Markdown


# TODO: insert `(it won't be shown at the next startup)` when automatically opened at the first startup
BASIC_CONTROLS = r"""
# BASIC CONTROLS

## Keys
To exit this help screen press `<Esc>`{}.

Note the hotkeys shown at the bottom of the terminal:
- ^: indicates the `<Ctrl>` key
- ↑ ↓ → ←: indicate the `cursor keys`

This app is keyboard controlled, but mouse input is also partially possible.

## Help Navigation

You can jump to sections of this help screen through the buttons on the left, using the mouse.

## Focus

Initially the scrollbar is focused and you can scroll the screen up and down using the `cursor` or `<Page-Up>` and `<Page-Down>` keys:
* You can also scroll using the `mouse wheel` or by `dragging` on the scrollbar to the right.
* Use `<Tab>` and `<Shift+Tab>` to cycle focus between different controls.

Scroll down to the next section and *press `<Tab>`* to *switch focus* to the production-planner table below.
"""

TABLE_CONTROLS_UPPER = r"""
# TABLE CONTROLS
"""

TABLE_CONTROLS_LOWER = r"""
Use the `arrow keys` to move the cursor (when the table has focus).

Press `<+>` to add a new row.

When the cursor is on the columns `QTY`, `Mk`, `Purity`, or `Clockrate`:

- you can type in your desired values using the number keys
- press `<Del>` to reset the value
- press `<Backspace>` to remove the last digit

When the cursor is on the columns `Building`, `Recipe`, or `Purity`:

- you can press `<Enter>` or `left-click` to select a new producer, recipe, or purity
"""

SUMMARY_UPPER = r"""
# SUMMARY ROWS
"""

SUMMARY_LOWER = r"""
The top row beneath the header shows a summary of all rows beneath it.

It calculates a simple naive balance by summing up all values for each column.

Values equaling zero are shown as blanks.
"""


HIGHLIGHTING_UPPER = r"""
# HIGHLIGHTING
"""

HIGHLIGHTING_LOWER = r"""
For example, when moving the cursor to the row with the `Miner` the `Iron Ore` column is highlighted blue:
- this signifies that the balance of that column is zero
- positive balances are highlighted in a green shade
- negative balances are highlighted in a red shade
- this highlighting applies to all "ingredient" columns of the row the cursor is currently on
"""


POWER_UPPER = """
# POWER COLUMNS
"""

POWER_LOWER = """
Power-draw and power-generation are shown in separate columns: `-Power` and `+Power`
"""

MODULES_UPPER = """
# MODULES
"""

MODULES_LOWER = """
Use the pseudo-producer `module` to embed another file into this one.

The `expand` and `collapse` hotkeys currently only apply to module rows.
"""


summary_table_fpath = Path(__file__).parent / Path(r"__data_folder__/iron_plate.yaml")
table_controls_fpath = Path(__file__).parent / Path(r"__data_folder__/empty.yaml")
power_table_fpath = Path(__file__).parent / Path(r"__data_folder__/iron_plate2.yaml")
modules_table_fpaths = [
    Path(__file__).parent / Path(r"__data_folder__/wire-cable_factory.yaml"),
    Path(__file__).parent / Path(r"__data_folder__/m_cable_wire.yaml"),
]


class TextContent(Static):
    ...


class QuickAccess(Container):
    ...


class LocationLink(Static):
    def __init__(self, label: str, reveal: str) -> None:
        super().__init__(label)
        self.reveal = reveal

    def on_click(self) -> None:
        self.app.query_one(self.reveal).scroll_visible(top=True, duration=0.5)


class Body(ScrollableContainer):
    ...


class Section(Container):
    pass


def sandboxed_table(id=id, load_paths=[]):
    if not load_paths:
        return
    elif not isinstance(load_paths, list):
        load_paths = [load_paths]

    dpath_sandboxed = Path(tempfile.mkdtemp(prefix="production_planner_help_data_folder")) / id
    os.makedirs(dpath_sandboxed)

    fpaths_sandboxed = []
    for load_path in load_paths:
        fpaths_sandboxed += [dpath_sandboxed / load_path.name]
        shutil.copy2(load_path, fpaths_sandboxed[-1])

    return PlannerTable(id=id, load_path=fpaths_sandboxed[0])


class HelpScreen(Screen):
    BINDINGS = [
        ("escape", "close", "Close"),
    ]

    CSS_PATH = "help.tcss"

    def __init__(self, startup_help=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.startup_help = startup_help

    def compose(self) -> ComposeResult:
        basic_controls = BASIC_CONTROLS.format(" (won't be shown at the next startup)" if self.startup_help else "")

        yield Header()
        yield Body(
            QuickAccess(
                LocationLink("Basic Controls", ".location-controls"),
                LocationLink("Table Controls", ".location-controls"),
                LocationLink("Summary Rows", ".location-summary"),
                LocationLink("Highlighting", ".location-highlighting"),
                LocationLink("Power Columnns", ".location-power"),
                # LocationLink("Modules", ".location-modules"),
            ),
            Section(
                TextContent(Markdown(basic_controls)),
                classes="location-controls"
            ),
            Section(
                TextContent(Markdown(TABLE_CONTROLS_UPPER)),
                sandboxed_table(id="help_plannertable", load_paths=table_controls_fpath),
                TextContent(Markdown(TABLE_CONTROLS_LOWER)),
                classes="location-table-controls"
            ),
            Section(
                TextContent(Markdown(SUMMARY_UPPER)),
                sandboxed_table(id="help_plannertable", load_paths=summary_table_fpath),
                TextContent(Markdown(SUMMARY_LOWER)),
                classes="location-summary"
            ),
            Section(
                TextContent(Markdown(HIGHLIGHTING_UPPER)),
                sandboxed_table(id="help_plannertable", load_paths=summary_table_fpath),
                TextContent(Markdown(HIGHLIGHTING_LOWER)),
                classes="location-highlighting"
            ),
            Section(
                TextContent(Markdown(POWER_UPPER)),
                sandboxed_table(id="help_plannertable", load_paths=power_table_fpath),
                TextContent(Markdown(POWER_LOWER)),
                classes="location-power"
            ),
            # TODO: need actual sandboxing to have a separate module listing not referring to `CONFIG.dpath_data`
            #
            # Section(
            #     TextContent(Markdown(MODULES_UPPER)),
            #     sandboxed_table(id="modules_table", load_paths=modules_table_fpaths),
            #     TextContent(Markdown(MODULES_LOWER)),
            #     classes="location-modules"
            # ),
        )
        yield Footer()

    def on_mount(self) -> None:
        pass

    def action_close(self):
        self.dismiss([])
