# -*- coding:utf-8 -*-

from core import get_path, set_path, Purity

from rich.text import Text


class Cell:
    name = ""
    read_only = False
    style_balance = False
    style_summary = False

    def __init__(self, data, path=None, read_only=None):
        self.data = data
        if path is not None:
            self.path = path
        if read_only is not None:
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
        if self.read_only: # FIXME: warn, rather than error
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

class PowerCell(Cell):
    name = "Power"
    path = "energy"
    read_only = True

class NumberCell(Cell):
    name = ""
    read_only = True
    style_balance = True

    def get(self):
        return self.data.ingredients[self.path] if self.path in self.data.ingredients else 0

class SummaryCell(NumberCell):
    name = ""
    def get(self):
        return sum(NumberCell(node, self.path).get() for node in self.data)

