# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from ..core import (
    get_path,
    set_path,
    SummaryNode,
)
from dataclasses import dataclass

from rich.text import Text
from rich.style import Style
from rich.color import Color


@dataclass
class Bounds:
    lower: int = 0
    upper: int = 999


@dataclass
class SetCellValue:
    column: None
    value: None


@dataclass
class CellValue:
    value: float = 0
    text = None
    clamped: bool = False


class Cell:
    name = ""
    default = ""
    default_na = ""
    read_only = True
    style_balance = False
    style_summary = False
    Selector = None
    is_numeric_editable = False
    bounds = Bounds(0, 999)
    vispath = None
    setpath = None
    indent = False
    # TODO: implement
    leaves = False
    justify = "left"
    fmt_summary = Style(bold=True)
    fmt_module_children = Style(color=Color.from_rgb(150, 150, 150))
    fmt_balance_minus = Style(color="red")
    fmt_balance_plus = Style(color="green")
    num_sign_is_pos = True

    def __init__(self, data, read_only=None):
        self.data = data
        self.setpath = self.setpath or self.vispath
        self.read_only = read_only if read_only is not None else self.read_only

    @classmethod
    def from_node(cls, data):
        cell = cls(data)
        return (cell, cell.get_styled())

    def get(self) -> CellValue:
        if self.access_guard():
            return CellValue(get_path(self.data, self.vispath))
        else:
            return CellValue(self.default_na)

    def get_num(self):
        return self.get().value

    def get_styled(self):
        cell = self.get()
        value = cell.value
        txt = str(cell.text or cell.value)
        style = Style()

        if self.style_summary:
            style += self.fmt_summary

        if self.style_balance:
            if isinstance(value, str):
                value = float(value.strip("= "))
            if value < 0:
                style += self.fmt_balance_minus
            elif value > 0:
                style += self.fmt_balance_plus
                txt = "+" + txt

        if cell.clamped:
            txt = f"= {txt}"

        if self.indent:
            txt = self.data.indent_str + txt
        if self.data.from_module and not self.data.node_main.is_module:
            style += self.fmt_module_children

        txt, style = self.text_postprocess(txt, style)

        return Text(txt, style=style, justify=self.justify)

    def text_postprocess(self, text: str, style: Style) -> (str, Style):
        return (text, style)

    def set(self, value) -> bool:
        if not self.access_guard() or value is None:
            return False
        if self.read_only:  # FIXME: warn, rather than error
            raise TypeError("Cell is Read-Only !")

        set_path(self.data, self.setpath or self.vispath, value)
        return True

    def set_num(self, value):
        return self.set(value)

    def edit_push_numeral(self, num: str, write_mode) -> bool:
        if not self.is_numeric_editable:
            return
        prev = str(self.get_num()).strip("+- ").split(".")[0]
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

        if not self.num_sign_is_pos:
            prev *= -1

        self.set_num(prev)
        self.data.node_main.update()
        return write_mode

    def edit_offset(self, offset):
        if not self.is_numeric_editable:
            return
        prev = str(self.get_num()).strip("+- ").split(".")[0]
        prev = int(prev) + offset
        if not (self.bounds.lower <= prev <= self.bounds.upper):
            prev = max(min(prev, self.bounds.upper), self.bounds.lower)
        self.set_num(prev)
        self.data.node_main.update()

    def edit_delete(self) -> bool:
        if not self.is_numeric_editable:
            return
        self.set_num(self.bounds.lower)
        self.data.node_main.update()
        return False

    def edit_backspace(self) -> bool:
        if not self.is_numeric_editable:
            return
        prev = str(self.get_num())
        new = prev[:-1].split(".")[0]
        if len(new) == 0:
            new = self.bounds.lower
        self.set_num(int(new))
        self.data.node_main.update()
        return True

    def access_guard(self) -> bool:
        """Checks if the node has information relevant to the cell. (e.g. A constructor has no MK value)"""
        return True


class EmptyCell(Cell):
    read_only = True

    def __init__(self, *args, **kwargs):
        super().__init__(None, **kwargs)

    def get(self) -> CellValue:
        return CellValue("")


class EditableCell(Cell):
    read_only = False
    selector = None

    def access_guard(self):
        return not isinstance(self.data.node_main, SummaryNode)


class NumericEditaleCell(EditableCell):
    default = 0
    default_na = ""
    is_numeric_editable = True
