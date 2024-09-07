# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from . import core
from .core import NodeInstance

from dataclasses import dataclass

from textual.widgets import DataTable
from textual.coordinate import Coordinate

from rich.style import Style


class PlannerTable(DataTable):
    rows_to_highlight = []
    cols_to_highlight = []

    def _render_cell(
        self,
        row_index: int,
        column_index: int,
        base_style: Style,
        width: int,
        cursor: bool = False,
        hover: bool = False):
        """Render the given cell.

        Args:
            row_index: Index of the row.
            column_index: Index of the column.
            base_style: Style to apply.
            width: Width of the cell.
            cursor: Is this cell affected by cursor highlighting?
            hover: Is this cell affected by hover cursor highlighting?

        Returns:
            A list of segments per line.
        """
        cursor_row = self.cursor_row
        if row_index == cursor_row:
            base_style += self.get_component_rich_style("datatable--hover" if row_index > 0 else "datatable--header-hover")
        elif cursor_row < len(self.highlight_cols) and row_index >= 0:
            col_info = self.highlight_cols[cursor_row]
            if len(col_info) > column_index:
                base_style += col_info[column_index]

        return super()._render_cell(row_index,
                                    column_index,
                                    base_style,
                                    width, cursor,
                                    hover)


@dataclass
class Selection:
    offset: int = 0


@dataclass
class Reselection:
    do:      bool = True
    offset:  int  = 0
    node: NodeInstance = None
    at_node: bool = True
    done:    bool = False


class SelectionContext:
    instance = None

    def __init__(self,
                 selection: Selection = None,
                 reselection:  Reselection = None):
        self.selection = selection or Selection()
        self.reselection = reselection or Reselection()
        self.row = core.APP.table.cursor_coordinate.row + self.selection.offset
        self.col = core.APP.table.cursor_coordinate.column
        self.__class__.instance = core.APP.data.get_node(self.row) if core.APP.data else None

    def __enter__(self):
        return self.instance

    def __exit__(self, exc_type, exc_value, traceback):
        no_exc = (exc_type, exc_value, traceback) == (None, None, None)
        if no_exc:
            self.reselect()

    def reselect(self):
        if self.reselection.do and not self.reselection.done:
            row = self.row
            if self.reselection.at_node and (self.reselection.node or self.instance):
                row = (self.reselection.node or self.instance).row_idx
            core.APP.table.cursor_coordinate = Coordinate(row + self.reselection.offset, self.col)
            self.reselection.done = True
