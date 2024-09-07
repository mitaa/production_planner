# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from ._cells import NumericEditaleCell, Bounds, SetCellValue
from ..core import Purity

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Footer
from textual.coordinate import Coordinate


class PurityCell(NumericEditaleCell):
    name = "Purity"
    vispath = "node_main.purity.name"
    setpath = "node_main.purity"
    bounds = Bounds(1, 3)
    purity_map = list(reversed(Purity.__members__))

    def __init__(self, *args, **kwargs):
        # FIXME: avoiding circular import ..
        self.selector = SelectPurity
        super().__init__(*args, **kwargs)

    def get_num(self):
        return self.purity_map.index(self.data.node_main.purity.name) + 1

    def set_num(self, value):
        value = min(max(1, value), 3)
        self.set(Purity[self.purity_map[value - 1]])

    def access_guard(self):
        return self.data.node_main.producer.is_miner and super().access_guard()


class SelectPurity(Screen[Purity]):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]
    data = []

    def compose(self) -> ComposeResult:
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        def bool_to_mark(a, mark="x"):
            return mark if a else ""

        self.data = [
            Purity.IMPURE,
            Purity.NORMAL,
            Purity.PURE,
        ]
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Purity")
        table.add_rows([[p.name.title()] for p in self.data])
        try:
            row = self.data.index(self.app.selected_node.purity)
        except ValueError as e:
            row = 0
        table.cursor_coordinate = Coordinate(row, 0)

    def action_cancel(self):
        self.dismiss([])

    def on_data_table_row_selected(self):
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row
        self.dismiss([SetCellValue(PurityCell, self.data[row])])
