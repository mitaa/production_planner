# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from ..core import (
    get_path,
    set_path,
    Bounds,
    smartround,
    SummaryNode,
)
from dataclasses import dataclass

from rich.text import Text
from rich.style import Style
from rich.color import Color

from numbers import Number


@dataclass
class SetCellValue:
    column: None
    value: None


@dataclass
class CellValue:
    value: float = 0
    text: str = None
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
        txt = str(cell.text or (smartround(cell.value) if isinstance(cell.value, Number) else cell.value))
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

    def set_guard(self, fn: callable):
        if not self.access_guard():
            return False
        if self.read_only:  # FIXME: warn, rather than error
            raise TypeError("Cell is Read-Only !")

        edit_value = get_path(self.data, self.setpath or self.vispath)
        if edit_value:
            return fn(edit_value)
        else:
            return False

    def set(self, value) -> bool:
        def set(edit):
            edit.value = value
        return self.set_guard(set)

    def set_num(self, value):
        return self.set(value)

    def edit_num(self, num, fn_getter: callable, write_mode: bool):
        def edit(edit_value):
            nonlocal write_mode
            write_mode = fn_getter(edit_value)(num, write_mode)
            self.data.node_main.update()
            return write_mode

        if not self.is_numeric_editable:
            return

        return self.set_guard(edit)

    def edit_push_numeral(self, num: str, write_mode) -> bool:
        return self.edit_num(num, lambda edit: edit.edit_push_numeral, write_mode)

    def edit_sign(self, num: str, write_mode) -> bool:
        return self.edit_num(num, lambda edit: edit.edit_sign, write_mode)

    def edit_push_dot(self, num: str, write_mode) -> bool:
        return self.edit_num(num, lambda edit: edit.edit_push_dot, write_mode)

    def edit_offset(self, offset):
        return self.edit_num(offset, lambda edit: edit.edit_offset, False)

    def edit_delete(self) -> bool:
        return self.edit_num(None, lambda edit: edit.edit_delete, False)

    def edit_backspace(self) -> bool:
        return self.edit_num(None, lambda edit: edit.edit_backspace, True)

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
