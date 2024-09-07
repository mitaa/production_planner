# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from ._cells import EditableCell
from ._selector import Sidebar, FilteredListSelector
from .. import core
from ..core import SummaryNode, NodeInstance, Node, Recipe

from textual.widgets import DataTable

from rich.style import Style
from rich.text import Text


class ProducerCell(EditableCell):
    name = "Building Name"
    vispath = "node_main.producer"
    setpath = "node_main.producer"
    indent = True

    @classmethod
    def Selector(cls, dst_table):
        class ProducerSelector(FilteredListSelector):
            screen_title = "Producers"
            sidebar_enabled = True
            sidebar_shown = core.CONFIG.store["select_producer"]["show_sidebar"]

            def on_mount(self) -> None:
                self.cell = ProducerCell
                self.data = core.PRODUCERS
                self.selected = dst_table.selected_node.producer
                self.query_one(DataTable).zebra_stripes = True
                super().on_mount()

            def action_toggle_sidebar(self) -> None:
                super().action_toggle_sidebar()
                core.CONFIG.store["select_producer"]["show_sidebar"] = not self.sidebar.has_class("-hidden")

            def update_sidebar(self):
                self.query_one(Sidebar).set_producer(self.package()[0].value)

            def update(self):
                def bool_to_mark(a, mark="x"):
                    return Text(mark if a else "", justify="center")
                table = self.query_one(DataTable)
                table.clear(columns=True)
                table.add_columns("Building", "Power", "Miner", "Power Gen")
                rows = []
                for p in self.data_filtered:
                    rows += [[ProducerCell(NodeInstance(Node(p, Recipe.empty()))).get_styled(),
                              Text(str(p.base_power), justify="right"),
                              bool_to_mark(p.is_miner),
                              bool_to_mark(p.is_pow_gen)]]
                table.add_rows(rows)
        return ProducerSelector

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def text_postprocess(self, text: str, style: Style) -> (str, Style):
        if self.data.node_main.is_module:
            return (text, style + Style(color="blue"))
        elif isinstance(self.data.node_main, SummaryNode):
            return (text, style + self.fmt_module_children)
        else:
            return (text, style)

    def access_guard(self):
        # We want to show this for the summary nodes
        return True

    def set(self, value):
        if super().set(value):
            self.data.node_main.producer_reset()
            if not self.data.node_main.is_module and self.data.node_children:
                self.data.node_children.clear()
