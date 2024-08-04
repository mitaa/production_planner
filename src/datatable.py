# -*- coding:utf-8 -*-

import core
from core import get_path, set_path, Purity, NodeInstance
from dataclasses import dataclass

from textual.widgets import DataTable
from textual.coordinate import Coordinate

from rich.text import Text
from rich.style import Style


class Cell:
    name = ""
    # TODO: delete / This can't be accessed later because Cells are ephemeral
    read_only = False
    style_balance = False
    style_summary = False

    def __init__(self, data, path=None, read_only=None):
        self.data = data
        if path is not None:
            self.path = path
        self.read_only = read_only

    @classmethod
    def from_node(cls, data):
        cell = cls(data)
        return (cell, cell.get_styled())

    def get(self):
        return get_path(self.data, self.path)

    def get_styled(self):
        value = self.get()
        txt = str(value)
        style = ""
        if self.style_summary:
            style += "bold "

        if self.style_balance:
            style += ""
            if value < 0:
                style += "red"
            elif value > 0:
                style += "green"
                txt = "+" + txt
        return Text(txt, style=style)

    def set(self, value):
        if self.read_only:  # FIXME: warn, rather than error
            raise TypeError("Cell is Read-Only !")
        return set_path(self.data, self.path, value)


class EmptyCell(Cell):
    read_only = True

    def __init__(self, **kwargs):
        super().__init__(None, **kwargs)

    def get(self):
        return ""


class ProducerCell(Cell):
    name = "Building Name"
    path = "producer.name"


class RecipeCell(Cell):
    name = "Recipe"
    path = "recipe.name"


class CountCell(Cell):
    name = "QTY"
    path = "count"


class MkCell(Cell):
    name = "Mk"
    path = "mk"

    def get(self):
        return self.data.mk if self.data.producer.is_miner else ""


class PurityCell(Cell):
    name = "Purity"
    path = "purity.name"

    def get(self):
        return self.data.purity.name if self.data.purity != Purity.NA else ""


class ClockRateCell(Cell):
    name = "Clockrate"
    path = "clock_rate"

    def get(self):
        return "" if self.data.producer.is_module else self.data.clock_rate


class PowerCell(Cell):
    name = "Power"
    path = "energy"
    read_only = True


class IngredientCell(Cell):
    name = ""
    read_only = True
    style_balance = True

    def get(self):
        return self.data.ingredients[self.path] if self.path in self.data.ingredients else 0


class SummaryCell(IngredientCell):
    name = ""
    read_only = True
    style_summary = True


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
        # FIXME: make highlighting based on cell texts already present in DataTable
        if len(self.cols_to_highlight) > column_index and self.cols_to_highlight[column_index] or row_index in self.rows_to_highlight:
            base_style += self.get_component_rich_style("datatable--hover" if row_index>0 else "datatable--header-hover")

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
    def __init__(self,
                 selection: Selection = Selection(),
                 reselection:  Reselection = Reselection()):
        self.selection = selection
        self.reselection = reselection
        self.row = core.APP.table.cursor_coordinate.row + selection.offset
        self.col = core.APP.table.cursor_coordinate.column
        self.instance = core.APP.data.get_node(self.row) if core.APP.data else None

    def __enter__(self):
        return self.instance

    def __exit__(self, exc_type, exc_value, traceback):
        no_exc = (exc_type, exc_value, traceback) == (None, None, None)
        if no_exc:
            self.reselect()

    def reselect(self):
        if self.instance and self.reselection.do and not self.reselection.done:
            row = self.row
            if self.reselection.at_node:
                row = (self.reselection.node or self.instance).row_idx
            core.APP.table.cursor_coordinate = Coordinate(row + self.reselection.offset, self.col)
            self.reselection.done = True
