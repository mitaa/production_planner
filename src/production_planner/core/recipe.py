# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from dataclasses import dataclass
from typing import Self

import yaml


@dataclass
class Ingredient:
    name: str
    count: int

    def __post_init__(self):
        if self.name == "Energy":
            self.name = "+Power"
            self.count /= 60

    def __str__(self):
        return f"({self.count}x {self.name})"

    def __hash__(self):
        return hash((self.name, self.count))

    def to_json_schema(self):
        return [self.count, self.name]

    def to_dict(self):
        return { self.name: self.count }


class Recipe(yaml.YAMLObject):
    yaml_tag = u"!recipe"

    recipe_to_producer_map = {}

    def __init__(self, name, cycle_rate, inputs: [(int, str)], outputs: [(int, str)], is_alternate=False):
        self.name = name
        self.cycle_rate = cycle_rate
        self.inputs = list(Ingredient(name, count) for count, name in inputs)
        self.outputs = list(Ingredient(name, count) for count, name in outputs)
        self.is_alternate = is_alternate

    def __str__(self):
        return f"{self.name}/{self.cycle_rate} {', '.join(map(str, self.inputs))} <> {', '.join(map(str, self.outputs))}"

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return type(self) is type(other) and self.name == other.name and self.cycle_rate == other.cycle_rate and self.inputs == other.inputs and self.outputs == other.outputs

    @property
    def producer(self):
        if self in self.recipe_to_producer_map:
            return self.recipe_to_producer_map[self]
        else:
            raise ValueError(f"recipe not found in recipe_to_producer_map: {self}")

    def __hash__(self):
        return hash((self.name, self.cycle_rate, tuple(self.inputs), tuple(self.outputs)))

    @classmethod
    def empty(cls, name=""):
        return cls(name, 60, [], [])

    @classmethod
    def from_dict(cls, ingredients: {str: int}, name="", cycle_rate=60) -> Self:
        inputs = []
        outputs = []
        for ingredient, quantity in sorted(ingredients.items()):
            if quantity < 0:
                inputs += [(abs(quantity), ingredient)]
            else:
                outputs += [(quantity, ingredient)]
        return cls(name, cycle_rate, inputs, outputs)

    def to_json_schema(self):
        return {
            self.name: [self.cycle_rate, [inp.to_json_schema() for inp in self.inputs], [out.to_json_schema() for out in self.outputs], self.is_alternate]
        }
