# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .. import core

import re
from typing import Optional, Self
from pathlib import Path
import json
from collections import OrderedDict

# Output Reference:
#
# {
#     "Miner": {
#         "description": "Extracts solid resources from the resource node it is built on. \r\nThe normal extraction rate is 120 resources per minute. \r\nThe extraction rate is modified depending on resource node purity. Outputs all extracted resources onto connected conveyor belts.",
#         "is_miner": true,
#         "is_pow_gen": false,
#         "max_mk": 3,
#         "base_power": 5,
#         "recipes": {
#             "Iron Ore":     [60, [], [[60, "Iron Ore"]]],
#             "Copper Ore":   [60, [], [[60, "Copper Ore"]]],
#             "Limestone":    [60, [], [[60, "Limestone"]]],
#             "Coal":         [60, [], [[60, "Coal"]]],
#             "Caterium Ore": [60, [], [[60, "Caterium Ore"]]],
#             "Raw Quartz":   [60, [], [[60, "Raw Quartz"]]],
#             "Sulfur":       [60, [], [[60, "Sulfur"]]],
#             "Bauxite":      [60, [], [[60, "Bauxite"]]],
#             "Uranium":      [60, [], [[60, "Uranium"]]],
#             "SAM Ore":      [60, [], [[60, "SAM Ore"]]]
#         }
#     },
# }
#
# FIXME: recipes need to have power added (Particle Generator, etc)...


class Docs(object):
    re_produced_in = re.compile('".*?\.(.*?)"')
    is_miner = False
    is_pow_gen = False

    def __init__(self, docs_data):
        self.docs = docs_data
        self.ClassName = docs_data["ClassName"]
        self.recipes = []

        if "mDisplayName" in docs_data:
            self.display_name = docs_data["mDisplayName"]

        if "mDescription" in docs_data:
            self.description = docs_data["mDescription"]

    def __str__(self):
        return f"<{self.__class__.__name__}: {self.ClassName}"

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.ClassName}"

    def _extract_classes(self, ctx, srch, splitter=None):
        items = []
        if not splitter:
            splitter = self.re_produced_in.findall
        raw_items = splitter(srch)
        not_in = set()
        for cls_name in raw_items:
            if cls_name not in ctx.my_index:
                not_in.add(cls_name)
                continue
            items += [ctx.my_index[cls_name]]
        return items

    @classmethod
    def parse(cls, classes) -> dict[str, Self]:
        items = {}
        natives = cls.NativeClass
        if natives is None:
            return {}

        if natives == "*":
            natives = list(classes.keys())

        if not isinstance(natives, list):
            natives = [natives]

        for native in natives:
            subclasses = classes[native]
            for subclass in subclasses:
                it = cls(subclass)
                items[it.ClassName] = it
        return items

    @classmethod
    def parse_all(_Self, classes) -> dict[Self]:
        items = {}

        for cls in _Self.__subclasses__():
            items[cls.__name__] = cls.parse(classes)
            items.update(cls.parse_all(classes))

        return items

    def make_producer(self, ctx) -> Optional[core.Producer]:
        prod = core.Producer(self.display_name,
                             is_miner=self.is_miner,
                             is_pow_gen=self.is_pow_gen,
                             max_mk=1,
                             base_power=self.base_power,
                             recipes={},
                             description=self.description)
        prod.recipes = self.recipes
        return prod


class ParseContext:
    def __init__(self, parsed: dict[str, Docs]):
        self.parsed = parsed
        self.class_index = {}
        self.my_index = {}
        self.recipes = []

        for desc in parsed["Descriptions"].values():
            self.class_index[desc.ClassName] = desc

        self._index()

        # for cls in Docs.__subclasses__():
        #     if cls.__name__ == "Descriptions":
        #         continue

        #     for desc in parsed[cls.__name__].values():
        #         self.my_index[desc.ClassName] = desc

    def _index(self, root=Docs) -> dict:
        for cls in root.__subclasses__():
            if cls.__name__ == "Descriptions":
                continue

            for desc in self.parsed[cls.__name__].values():
                self.my_index[desc.ClassName] = desc

            self._index(root=cls)

    def make_producers(self) -> [core.Producer]:
        producers = []
        self.make_recipes()

        classes = ["ResourceExtractor",
                   "WaterPump",
                   "ResourceWellActivator",
                   "ResourceWellExtractor",
                   "Manufacturer",
                   "ManufacturerVarPower",
                   "FuelGen",
                   "NuclearGen",
                   "GeothermalGen"]

        for cls_name in classes:
            for classname, extractor in self.parsed[cls_name].items():
                prod = extractor.make_producer(self)
                if prod:
                    producers += [prod]

        return producers

    def make_recipes(self):
        for recipe in self.parsed["Recipe"].values():
            recip = recipe.make_recipe(self)
            recipe.attach_producer(self)
            self.recipes += [recip]


class Powered(Docs):
    NativeClass = None

    def __init__(self, docs_data):
        super().__init__(docs_data)
        self.base_power = float(docs_data["mPowerConsumption"])

        # TODO: add to export data
        self.power_exponent = float(docs_data["mPowerConsumptionExponent"])


class Manufacturer(Powered):
    NativeClass = "/Script/CoreUObject.Class'/Script/FactoryGame.FGBuildableManufacturer'"


class ManufacturerVarPower(Powered):
    NativeClass = "/Script/CoreUObject.Class'/Script/FactoryGame.FGBuildableManufacturerVariablePower'"

    def __init__(self, docs_data):
        super().__init__(docs_data)
        # FIXME: handle variable power consumption ?
        self.base_power = float(docs_data["mEstimatedMaximumPowerConsumption"])


class Fueled(Powered):
    is_miner = False
    is_pow_gen = True

    def __init__(self, docs_data):
        super().__init__(docs_data)
        self.docs_fuel = docs_data["mFuel"]
        self.power_production = int(float(docs_data["mPowerProduction"]))

        # TODO: add to export data
        self.production_boost_exponent = docs_data["mProductionBoostPowerConsumptionExponent"]

        self.requires_supplemental_resource = docs_data["mRequiresSupplementalResource"].lower() == "true"
        self.supplemental_load_amount = float(docs_data["mSupplementalLoadAmount"])
        self.supplemental_to_power_ratio = float(docs_data["mSupplementalToPowerRatio"])

    def make_producer(self, ctx: ParseContext) -> Optional[core.Producer]:
        self.generate_recipes(ctx)
        return super().make_producer(ctx)

    def generate_recipes(self, ctx: ParseContext):
        for fuel in self.docs_fuel:
            inputs = []
            outputs = []
            fuel_class = ctx.class_index[fuel["mFuelClass"]]
            fuel_energy = float(fuel_class.energy_value)
            burn_time = fuel_energy / self.power_production
            items_per_minute = 60 / burn_time
            items_per_minute = _convert_units(fuel_class, items_per_minute)

            inputs += [[items_per_minute, fuel_class.display_name]]
            # FIXME ?
            outputs += [[fuel_energy * items_per_minute, "Energy"]]

            if self.requires_supplemental_resource:
                supplemental_resource = fuel["mSupplementalResourceClass"]
                supplemental_resource = ctx.class_index[supplemental_resource]
                supplemental_count = (self.power_production * 60) / self.supplemental_load_amount * self.supplemental_to_power_ratio
                inputs += [[supplemental_count, supplemental_resource.display_name]]

            byproduct = fuel["mByproduct"]
            if byproduct:
                byproduct_count = float(fuel["mByproductAmount"])
                outputs += [[byproduct_count, ctx.class_index[byproduct].display_name]]

            self.recipes += [core.Recipe(fuel_class.display_name, 60, inputs, outputs, False)]


class FuelGen(Fueled):
    NativeClass = "/Script/CoreUObject.Class'/Script/FactoryGame.FGBuildableGeneratorFuel'"


class NuclearGen(Fueled):
    NativeClass = "/Script/CoreUObject.Class'/Script/FactoryGame.FGBuildableGeneratorNuclear'"


class GeothermalGen(Powered):
    NativeClass = "/Script/CoreUObject.Class'/Script/FactoryGame.FGBuildableGeneratorGeoThermal'"
    is_miner = True
    is_pow_gen = True

    def make_producer(self, ctx: ParseContext) -> Optional[core.Producer]:
        self.recipes += [core.Recipe("Geothermal Power", 60, [], [[18000, "Energy"]], False)]
        return super().make_producer(ctx)


class Resourced(Powered):
    def __init__(self, docs_data):
        super().__init__(docs_data)
        self._docs_resources = docs_data["mAllowedResources"]

    def make_producer(self, ctx: ParseContext) -> Optional[core.Producer]:
        self.add_resources(ctx)
        return super().make_producer(ctx)

    def add_resources(self, ctx: ParseContext):
        def splitter(raw):
            quoteds = list(filter(lambda c: c != "(" and c != ")", raw.split('"')))
            stems = [quoted.split(".")[-1].strip("'\"") for quoted in quoteds]
            return stems

        self.resources = [r.display_name for r in self._extract_classes(ctx, self._docs_resources, splitter=splitter)]


class ResourceWellExtractor(Resourced):
    NativeClass = "/Script/CoreUObject.Class'/Script/FactoryGame.FGBuildableFrackingExtractor'"
    is_miner = True

    def add_resources(self, ctx: ParseContext):
        super().add_resources(ctx)

        for resource in self.resources:
            self.recipes += [core.Recipe(resource, 60, [], [(60, resource)], False)]


class ResourceWellActivator(Powered):
    NativeClass = "/Script/CoreUObject.Class'/Script/FactoryGame.FGBuildableFrackingActivator'"


class ResourceExtractor(Resourced):
    NativeClass = "/Script/CoreUObject.Class'/Script/FactoryGame.FGBuildableResourceExtractor'"
    is_miner = True

    def make_producer(self, ctx: ParseContext) -> Optional[core.Producer]:
        self.add_resources(ctx)
        if not self.recipes:
            return

        return super().make_producer(ctx)

    def add_resources(self, ctx: ParseContext):
        super().add_resources(ctx)

        if self.ClassName == "Build_MinerMk1_C":
            self.display_name = "Miner"
            for res in ctx.parsed["Resource"].values():
                if res.form == "RF_SOLID":
                    self.resources += [res.display_name]

        # FIXME: is there a way other than to hardcode this?
        match self.ClassName:
            case "Build_OilPump_C":
                res_count = 120
                self.max_mk = 1
            case _ if "MinerMk" in self.ClassName:
                res_count = 60
                self.max_mk = 3

        for resource in self.resources:
            self.recipes += [core.Recipe(resource, 60, [], [(res_count, resource)], False)]


class WaterPump(Resourced):
    NativeClass = "/Script/CoreUObject.Class'/Script/FactoryGame.FGBuildableWaterPump'"

    def add_resources(self, ctx: ParseContext):
        super().add_resources(ctx)
        for resource in self.resources:
            # FIXME: is there a way other than to hardcode this?
            self.recipes += [core.Recipe(resource, 60, [], [(120, resource)], False)]


class Resource(Docs):
    NativeClass = "/Script/CoreUObject.Class'/Script/FactoryGame.FGResourceDescriptor'"

    def __init__(self, docs_data):
        super().__init__(docs_data)
        self.form = docs_data["mForm"]
        self.energy_value = docs_data["mEnergyValue"]


class Descriptions(Docs):
    NativeClass = "*"

    def __init__(self, docs_data):
        super().__init__(docs_data)
        if "mForm" in docs_data:
            self.form = docs_data["mForm"]

        if "mEnergyValue" in docs_data:
            self.energy_value = docs_data["mEnergyValue"]


class Recipe(Docs):
    NativeClass = "/Script/CoreUObject.Class'/Script/FactoryGame.FGRecipe'"
    re_ingredients = re.compile(r"ItemClass=(\".+?\")\s*,\s*Amount=(\d+)")

    def __init__(self, docs_data):
        super().__init__(docs_data)
        self._inputs = docs_data["mIngredients"]
        self._outputs = docs_data["mProduct"]
        self.cycle_rate = int(float(docs_data["mManufactoringDuration"]))
        self.producers = []
        self._producers = docs_data["mProducedIn"]
        self.core_recipe = None

    def attach_producer(self, ctx: ParseContext):
        self.producers = self._extract_classes(ctx, self._producers)

        for prod in self.producers:
            prod.recipes += [self.core_recipe]

        return self.producers

    def make_recipe(self, ctx: ParseContext) -> core.Recipe:
        self.is_alternate_recipe = self.display_name.startswith("Alternate:")

        if self.is_alternate_recipe:
            recipe_name = self.display_name.removeprefix("Alternate: ")
        else:
            recipe_name = self.display_name

        self.core_recipe = core.Recipe(recipe_name, self.cycle_rate, self.make_inputs(ctx), self.make_outputs(ctx), self.is_alternate_recipe)
        return self.core_recipe

    @classmethod
    def make_ingredients(self, ctx: ParseContext, data) -> [core.Ingredient]:
        ingredients = []
        raw_ingredients = self.re_ingredients.findall(data)
        for raw_ingredient in raw_ingredients:
            name, count = raw_ingredient
            # FIXME: properly unescape '\'
            name = name.split(".")[-1].strip("\\\"'")
            desc = ctx.class_index[name]
            count = int(count)
            count = _convert_units(desc, count)
            ingredients += [(count, desc.display_name)]
        return ingredients

    def make_inputs(self, ctx: ParseContext):
        return self.make_ingredients(ctx, self._inputs)

    def make_outputs(self, ctx: ParseContext):
        return self.make_ingredients(ctx, self._outputs)


def _convert_units(desc: Docs, count: int | float):
    match desc.form:
        case "RF_LIQUID" | "SS_FLUID" | "RF_GAS":
            count /= 1000
    return count


CUSTOM_ORDER = [
    "Miner",
    "Water Extractor",
    "Oil Extractor",
    "Resource Well Pressurizer",
    "Resource Well Extractor",
    "Smelter",
    "Foundry",
    "Constructor",
    "Assembler",
    "Manufacturer",
    "Packager",
    "Blender",
    "Refinery",
    "Particle Accelerator",
    "Quantum Encoder",
    "Converter",
    "Biomass Burner",
    "Coal Generator",
    "Coal-Powered Generator",
    "Fuel Generator",
    "Fuel-Powered Generator",
    "Geothermal Generator",
    "Nuclear Power Plant",
]


def _custom_producer_order(producers):
    producer_map = OrderedDict()
    for prod in producers:
        producer_map[prod.name] = prod

    ordered = []

    for prod_name in CUSTOM_ORDER:
        if prod_name in producer_map:
            ordered += [producer_map[prod_name]]
            del producer_map[prod_name]
    ordered += list(producer_map.values())
    return ordered


def docs_json(fpath: Path) -> Optional[list[core.Producer]]:
    with open(fpath, "r", encoding="utf-16-le") as fp:
        raw = fp.read().lstrip("\ufeff")
        docs = json.loads(raw)

    classes = {}
    for data in docs:
        classes[data["NativeClass"]] = data["Classes"]

    ctx = ParseContext(Docs.parse_all(classes))
    producers = ctx.make_producers()
    producers = _custom_producer_order(producers)
    return producers
