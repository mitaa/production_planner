# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from ._cells import EditableCell, SetCellValue, CellValue
from ._selector import StringifyFilter, FilteredListSelector, Sidebar
from .producer import ProducerCell
from .. import core
from .. core import ModuleFile
from ..core import CONFIG, PRODUCER_NAMES, PRODUCER_MAP, Recipe, Ingredient, all_recipes_producer, Node, NodeInstance
from ..core import MODULE_PRODUCER
from ..core import smartround

import os
from enum import Enum
import re

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets.selection_list import Selection
from textual.widgets import SelectionList, DataTable, Header, Footer, Select, Input

from rich.style import Style
from rich.text import Text

SELECT_PRODUCERS = [all_recipes_producer] + core.PRODUCERS


class RecipeFilterSetting(Enum):
    # Note: prompt == value in the SelectionList
    in_recipe_names = Selection(*["Recipe Names"] * 2, True)
    in_outputs = Selection(*["Outputs"] * 2, True)
    in_inputs  = Selection(*["Inputs"] * 2, False)
    # use_regex = Selection(*["Regex"] * 2, False)


class RecipeFilter(StringifyFilter):
    def __init__(self, search: str = "", *args, **kwargs):
        super().__init__(search, *args, **kwargs)
        self.use_regex = False
        self.search = search
        self.update_settings([m.value.prompt.plain for m in RecipeFilterSetting if m.value.initial_state])

    def update_settings(self, active_options: [str]):
        for member in RecipeFilterSetting:
            setattr(self, member.name, member.value.prompt.plain in active_options)

    @property
    def use_regex(self):
        return self._use_regex

    @use_regex.setter
    def use_regex(self, value):
        self._use_regex = value
        self.search = self.search

    @StringifyFilter.search.setter
    def search(self, value):
        self._search = value
        words = value.split()
        self.words = words
        try:
            re_search = re.compile(self.search, flags=re.IGNORECASE)
        except re.error:
            re_search = re.compile("")
            # Happens when for example value == "\\"

        def filt_regex(content: str):
            return re_search.search(content) is not None

        def filt_words(content: str):
            return all(word in content for word in words)

        self.filt = filt_regex if self.use_regex else filt_words

    def filter_item(self, item: Recipe) -> bool:
        def search_ingredients(ingredients: [Ingredient]) -> bool:
            for ingredient in ingredients:
                if self.filt(str(ingredient).lower()):
                    return True

        if self.in_recipe_names:
            if self.filt(item.name.lower()):
                return True

        if self.in_inputs:
            if search_ingredients(item.inputs):
                return True
        if self.in_outputs:
            if search_ingredients(item.outputs):
                return True


class RecipeCell(EditableCell):
    name = "Recipe"
    vispath = "node_main.recipe.name"
    setpath = "node_main.recipe"
    indent = True

    @classmethod
    def Selector(cls, table):
        class RecipeSelector(FilteredListSelector):
            screen_title = "Recipes"
            data_filter = RecipeFilter()

            def on_mount(self) -> None:
                self.query_one(SelectionList).border_title = "[white]Look in:[/]"
                self.add_producer_column = False
                self.cell = RecipeCell
                if table.selected_node.is_module:
                    MODULE_PRODUCER.rescan_modules()

                self.data = table.selected_producer.recipes
                self.selected = table.selected_node.recipe
                self.query_one(DataTable).zebra_stripes = True
                super().on_mount()

            def compose(self) -> ComposeResult:
                # TODO: use the parent class's `compose` method and add the Select widget
                self.producer_listing = self._producer_listing(table.selected_producer.name)
                yield Header()
                yield Horizontal(
                    # FIXME: use actual Cell formatting for Select widget
                    Select([(producer, producer) for producer in self.producer_listing], allow_blank=False),
                    Input(placeholder="<text filter>"),
                    SelectionList(*[member.value for member in RecipeFilterSetting]),
                )
                yield DataTable()
                yield Footer()
                yield Sidebar(classes="-hidden")

            @on(SelectionList.SelectedChanged)
            def update_filter_settings(self, event: SelectionList.SelectedChanged):
                self.data_filter.update_settings(event.selection_list.selected)
                self.set_filt(None)

            def package(self) -> [SetCellValue]:
                set_recipe: [SetCellValue] = super().package()
                # Note: keep the producer in front of the recipe - otherwise the `Node.recipe_cache` will be inconsistent
                return [SetCellValue(ProducerCell, set_recipe[0].value.producer)] + set_recipe

            def _producer_listing(self, producer_name):
                producer_list = [p.name for p in SELECT_PRODUCERS]
                del producer_list[producer_list.index(producer_name)]
                producer_list.insert(0, producer_name)
                return producer_list

            @on(Select.Changed)
            def relist_recipes(self, event: Select.Changed):
                # put the selected producer at the top
                self.producer_list = self._producer_listing(event.value)
                sel = self.query_one(Select)
                with sel.prevent(Select.Changed):
                    sel.set_options((p, p) for p in self.producer_list)
                self.data = PRODUCER_MAP[event.value].recipes

                self.add_producer_column = sel.value == all_recipes_producer.name
                self.sort()

                self.set_filt(None)

            def sort(self):
                if self.add_producer_column:
                    self.data_sorted = list(sorted(self.data, key=lambda r: PRODUCER_NAMES.index(r.producer.name)))
                else:
                    self.data_sorted = self.data

            def update(self):
                def ingredient_count(attr):
                    if self.data_filtered:
                        return max(len(getattr(recipe, attr)) for recipe in self.data_filtered)
                    else:
                        return 0

                table = self.query_one(DataTable)
                table.clear(columns=True)
                max_input_count = ingredient_count("inputs")
                max_output_count = ingredient_count("outputs")
                rows = []

                columns = ["Producer"] if self.add_producer_column else []
                columns += (["Recipe Name"]
                    + [f"Out #{i}" for i in range(max_output_count)]
                    + [f"In  #{i}" for i in range(max_input_count)]
                )

                for recipe in self.data_filtered:
                    rate_mult = 60 / recipe.cycle_rate
                    row = []
                    if self.add_producer_column:
                        producer = recipe.producer
                        row += [ProducerCell(NodeInstance(Node(producer, Recipe.empty()))).get_styled() if producer else ""]
                    row += [recipe.name]
                    # FIXME: production per minute should somehow be included in `str(Ingredient)`, otherwise we can't filter for that
                    inputs  = [Text(f"({smartround(ingr.count*rate_mult): >3}/min) {ingr.count: >3}x{ingr.name}", style="red") for ingr in recipe.inputs]
                    outputs = [Text(f"({smartround(ingr.count*rate_mult): >3}/min) {ingr.count: >3}x{ingr.name}", style="green") for ingr in recipe.outputs]
                    inputs += [""] * (max_input_count - len(inputs))
                    outputs += [""] * (max_output_count - len(outputs))
                    row += outputs
                    row += inputs
                    rows += [row]

                table.add_columns(*columns)
                table.add_rows(rows)
        return RecipeSelector

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get(self) -> CellValue:
        if self.data.node_main.is_module:
            return CellValue(f"<{super().get().value}>")
        else:
            return CellValue(super().get().value)

    def text_postprocess(self, text: str, style: Style) -> (str, Style):
        if self.data.node_main.is_module:
            return (text, style + Style(color="blue"))
        else:
            return (text, style)

    def set(self, value):
        if super().set(value) and self.data.node_main.is_module:
            self.data.set_module(ModuleFile(self.data.node_main.recipe.name))
            curname = os.path.splitext(str(core.APP.focused_table.sink.sink.target.linkpath.name))[0]
            core.APP.focused_table.nodetree.reload_modules([self.data], module_stack=[curname])
