# -*- coding:utf-8 -*-

from core import get_path, set_path

from rich.text import Text


class Cell:
    read_only = False
    style_balance = False
    style_summary = False

    def __init__(self, node, path=None, read_only=None):
        self.node = node
        if path is not None:
            self.path = path
        if read_only is not None:
            self.read_only = read_only

    def get(self):
        return get_path(self.node, self.path)

    @classmethod
    def from_node(cls, node):
        cell = cls(node)
        return (cell, cell.get_styled())

    def get_styled(self):
        value = self.get()
        txt = str(value)
        style = ""
        if self.style_summary:
            style += "bold "

        if self.style_balance:
            style += "white"
            if value < 0:
                style += " on red"
            elif value > 0:
                style += " on green"
                txt = "+" + txt
        return Text(txt, style=style)

    def set(self, value):
        if self.read_only: # FIXME: warn, rather than error
            raise TypeError("Cell is Read-Only !")
        return set_path(self.node, self.path, value)


class ProducerCell(Cell):
    path = ".producer.name"

class RecipeCell(Cell):
    path = ".recipe.name"

class CountCell(Cell):
    path = ".count"

class MkCell(Cell):
    path = ".mk"

class PurityCell(Cell):
    path = ".purity.name"

class ClockRateCell(Cell):
    path = ".clock_rate"

class PowerCell(Cell):
    path = ".energy"
    read_only = True

class NumberCell(Cell):
    read_only = True
    style_balance = True
