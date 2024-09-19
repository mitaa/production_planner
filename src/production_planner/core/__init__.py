# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .link import CONFIG, DataFile, PortableFile, ModuleFile, ModuleFile, ensure_keys
from .recipe import Ingredient, Recipe
from . import producer
from .producer import Producer, ProducerEncoder, PRODUCERS, PRODUCER_NAMES, PRODUCER_MAP, PRODUCER_ALIASES, MODULE_PRODUCER
from .module import _ModuleProducer
from .node import Purity, Node
from .nodetree import NodeInstance, SummaryNode, NodeTree
from . import marshal

import json

APP = None


# TODO: add some ~IGNORED_AMOUNT variable to CONFIG and use that instead of hardcoded 0.01
#       use this also for column highlighting ...
def smartround(value: float | int):
    truncated_value = int(value)
    if abs(value - truncated_value) < 0.01:
        return truncated_value
    else:
        return round(value, 2)


def get_path(obj, path):
    paths = path.split(".", maxsplit=1)
    primpath = paths[0]
    subpaths = paths[1:]
    if not subpaths:
        return getattr(obj, path)
    else:
        return get_path(getattr(obj, primpath), subpaths[0])


def set_path(obj, path, value):
    paths = path.split(".", maxsplit=1)
    primpath = paths[0]
    subpaths = paths[1:]
    if not subpaths:
        return setattr(obj, path, value)
    else:
        return set_path(getattr(obj, primpath), subpaths[0], value)


# TODO: reorganize files
from .. import gamedata
# TODO: allow anchoring to a selected game version and storing it in CONFIG
# TODO: add selected game version to the NodeTree and store it in the yaml files too
#       -> warning that a different version is now loaded and generate / show a diff
data_version = gamedata.get()
data_fpath = data_version.fpath

with open(data_fpath) as fp:
    data = json.load(fp)

for k, v in data.items():
    prod = Producer(k, **v)
    PRODUCERS += [prod]

PRODUCER_NAMES += [prod.name for prod in PRODUCERS]

# FIXME
all_recipes_producer = producer.all_recipes_producer()

PRODUCER_MAP.update({p.name: p for p in ([all_recipes_producer] + PRODUCERS)})
PRODUCER_MAP["Blueprint"] = PRODUCER_MAP["Module"]

for name, aliases in PRODUCER_ALIASES.items():
    if name in PRODUCER_MAP:
        for alias in aliases:
            PRODUCER_MAP[alias] = PRODUCER_MAP[name]
