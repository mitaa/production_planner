# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from ._cells import SetCellValue
from ..core import Producer

from textual import on
from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import DataTable, Header, Footer, Input, Static
from textual.coordinate import Coordinate
from textual import events


class StringifyFilter:
    def __init__(self, search: str = ""):
        self._search = search

    @property
    def search(self):
        return self._search

    @search.setter
    def search(self, value: str):
        self._search = value
        self.words = value.split()

    def filter_item(self, item) -> bool:
        return all(word in str(item).lower() for word in self.words)


class Title(Static):
    pass


class Description(Static):
    pass


class Sidebar(Container):
    def compose(self) -> ComposeResult:
        yield Title("")
        yield Description("")

    def set_producer(self, producer: Producer):
        if self.has_class("-hidden"):
            return

        title = self.query_one(Title)
        description = self.query_one(Description)

        title.update(producer.name)
        # FIXME: superscript 3 (e.g. cubic metres) aren't rendered correctly
        description.update(producer.description)


class FilteredListSelector(Screen):
    CSS_PATH = "FilteredListSelector.tcss"
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+b", "toggle_sidebar", "Sidebar"),
    ]
    cell = None
    data = []
    data_sorted = []
    data_filtered = []
    data_filter = StringifyFilter()
    selected = None
    sidebar_enabled = False

    def on_mount(self) -> None:
        self.query_one(DataTable).cursor_type = "row"
        self.filt_input = self.query_one(Input)
        self.table = self.query_one(DataTable)
        self.sort()
        self.set_filt(None)
        self.query_one(DataTable).focus()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(Input(placeholder="<text filter>"))
        yield DataTable()
        yield Footer()
        yield Sidebar(classes=("" if self.sidebar_enabled else "-hidden"))

    def action_toggle_sidebar(self) -> None:
        if not self.sidebar_enabled:
            return

        sidebar = self.query_one(Sidebar)
        if sidebar.has_class("-hidden"):
            sidebar.remove_class("-hidden")
            self.update_sidebar()
        else:
            sidebar.add_class("-hidden")

    def update_sidebar(self):
        pass

    def on_data_table_row_highlighted(self):
        self.update_sidebar()

    def sort(self):
        self.data_sorted = self.data

    @property
    def header(self):
        return self.query_one(Header)

    def action_cancel(self):
        self.app.sub_title = ""
        self.dismiss([])

    @on(Input.Submitted)
    def input_submitted(self, event: Input.Submitted):
        self.on_data_table_row_selected()

    def package(self) -> [SetCellValue]:
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row
        return [SetCellValue(self.cell, self.data_filtered[row])]

    def on_data_table_row_selected(self):
        if self.data_filtered:
            self.dismiss(self.package())
        else:
            self.dismiss([])

    @on(Input.Changed)
    def set_filt(self, event: Input.Changed) -> None:
        if event is None:
            self.data_filter.search = self.query_one(Input).value
        else:
            self.data_filter.search = event.value

        self.data_filtered = list(filter(self.data_filter.filter_item, self.data_sorted))
        self.update()
        self.select()

    def select(self):
        it_data = iter(self.data)
        table = self.query_one(DataTable)

        row_selected = None
        for row_number, filt_item in enumerate(self.data_filtered):
            for item in it_data:
                if item == self.selected:
                    row_selected = row_number
                    table.cursor_coordinate = Coordinate(row_selected or 0, 0)
                    return
                elif item == filt_item:
                    break

    def on_key(self, event: events.Key) -> None:
        if len(self.app.screen_stack) > 2:
            return

        match event.key:
            case "ctrl+up":
                self.filt_input.focus()
            case "up" | "down" if self.filt_input.has_focus:
                self.table.focus()
            case _ if len(event.key) == 1 and not self.filt_input.has_focus and event.key.isprintable():
                inp = self.query_one(Input)
                inp.focus()
                inp.value += event.key
