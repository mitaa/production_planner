# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from . import core
from .core import CONFIG, get_path, set_path, Purity, NodeInstance, SummaryNode
from . import screens

import os
from dataclasses import dataclass

from textual.widgets import DataTable
from textual.coordinate import Coordinate

from rich.text import Text
from rich.style import Style


@dataclass
class Bounds:
    lower: int = 0
    upper: int = 999


class Cell:
    name = ""
    default = ""
    default_na = ""
    read_only = True
    style_balance = False
    style_summary = False
    selector = None
    is_numeric_editable = False
    bounds = Bounds(0, 999)
    vispath = None
    setpath = None
    justify = "left"

    def __init__(self, data, read_only=None):
        self.data = data
        self.setpath = self.setpath or self.vispath
        self.read_only = read_only if read_only is not None else self.read_only

    @classmethod
    def from_node(cls, data):
        cell = cls(data)
        return (cell, cell.get_styled())

    def get(self):
        if self.access_guard():
            return get_path(self.data, self.vispath)
        else:
            return self.default_na

    def get_num(self):
        return self.get()

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
        return Text(txt, style=style, justify=self.justify)

    def set(self, value):
        if not self.access_guard() or value is None:
            return
        if self.read_only:  # FIXME: warn, rather than error
            raise TypeError("Cell is Read-Only !")

        return set_path(self.data, self.setpath or self.vispath, value)

    def set_num(self, value):
        return self.set(value)

    def edit_postproc(self, instance: NodeInstance):
        pass

    def edit_push_numeral(self, num: str, write_mode) -> bool:
        if not self.is_numeric_editable:
            return
        prev = str(self.get_num())
        ccount_min = len(str(self.bounds.lower))
        ccount_max = len(str(self.bounds.upper))

        if (ccount_min == ccount_max == 1):
            prev = num
            write_mode = False
        elif not write_mode:
            prev = num
            write_mode = True
        else:
            prev += num
            write_mode = True

        prev = int(prev)
        if not (self.bounds.lower <= prev <= self.bounds.upper):
            prev = max(min(prev, self.bounds.upper), self.bounds.lower)
            write_mode = False

        self.set_num(prev)
        self.data.update()
        return write_mode

    def edit_delete(self) -> bool:
        if not self.is_numeric_editable:
            return
        self.set_num(self.bounds.lower)
        self.data.update()
        return False

    def edit_backspace(self) -> bool:
        if not self.is_numeric_editable:
            return
        prev = str(self.get_num())
        new = prev[:-1]
        if len(new) == 0:
            new = self.bounds.lower
        self.set_num(int(new))
        self.data.update()
        return True

    def access_guard(self) -> bool:
        """Checks if the node has information relevant to the cell. (e.g. A constructor has no MK value)"""
        return True


class EmptyCell(Cell):
    read_only = True

    def __init__(self, *args, **kwargs):
        super().__init__(None, **kwargs)

    def get(self):
        return ""


class EditableCell(Cell):
    read_only = False
    selector = None

    def access_guard(self):
        return not isinstance(self.data, SummaryNode)


class ProducerCell(EditableCell):
    name = "Building Name"
    vispath = "producer.name"
    setpath = "producer"

    def __init__(self, *args, **kwargs):
        # FIXME: avoiding circular import ..
        self.selector = screens.SelectProducer
        super().__init__(*args, **kwargs)

    def edit_postproc(self, instance):
        self.data.producer_reset()


class RecipeCell(EditableCell):
    name = "Recipe"
    vispath = "recipe.name"
    setpath = "recipe"

    def __init__(self, *args, **kwargs):
        # FIXME: avoiding circular import ..
        self.selector = screens.SelectRecipe
        super().__init__(*args, **kwargs)

    def edit_postproc(self, instance):
        if self.data.is_module:
            instance.set_module(self.data.recipe.name)
            curname = os.path.splitext(CONFIG["last_file"])[0]
            core.APP.data.reload_modules([instance], module_stack=[curname])


class NumericEditaleCell(EditableCell):
    default = 0
    default_na = ""
    is_numeric_editable = True


class CountCell(NumericEditaleCell):
    name = "QTY"
    vispath = "count"
    justify = "right"


class MkCell(NumericEditaleCell):
    name = "Mk"
    vispath = "mk"
    bounds = Bounds(1, 3)

    def access_guard(self):
        return self.data.producer.is_miner and super().access_guard()


class PurityCell(NumericEditaleCell):
    name = "Purity"
    vispath = "purity.name"
    setpath = "purity"
    bounds = Bounds(1, 3)
    purity_map = list(reversed(Purity.__members__))

    def __init__(self, *args, **kwargs):
        # FIXME: avoiding circular import ..
        self.selector = screens.SelectPurity
        super().__init__(*args, **kwargs)

    def get_num(self):
        value = self.purity_map.index(self.data.purity.name) + 1
        return self.purity_map.index(self.data.purity.name) + 1

    def set_num(self, value):
        value = min(max(1, value), 3)
        self.set(Purity[self.purity_map[value - 1]])

    def access_guard(self):
        return self.data.producer.is_miner and super().access_guard()


class ClockRateCell(NumericEditaleCell):
    name = "Clockrate"
    vispath = "clock_rate"
    bounds = Bounds(0, 250)

    def access_guard(self):
        return not self.data.producer.is_module and super().access_guard()


class PowerCell(Cell):
    name = "Power"
    vispath = "energy"
    read_only = True
    justify = "right"


class IngredientCell(Cell):
    name = ""
    default_na = 0
    read_only = True
    style_balance = True
    justify = "right"

    def access_guard(self):
        return self.vispath in self.data.ingredients

    def get(self):
        if self.access_guard():
            return self.data.ingredients[self.vispath]
        else:
            return self.default_na


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
        else:
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
