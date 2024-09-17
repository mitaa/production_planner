# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""__init__.py

Usage:
  __init__.py <docs.json-path>
  __init__.py (-h | --help)

Options:
  -h --help             Show this screen.
"""

from docopt import docopt

import os
import re
import json
from pathlib import Path
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional, ClassVar


@dataclass
class GameDataFileVersion:
    fpath: Path
    major: int
    minor: int
    patch: int
    postfix: int | str
    build: int

    file_versions: ClassVar = []

    def __post_init__(self):
        self.file_versions += [self]

    def __index__(self, idx):
        return GameDataVersionFilter(self)[idx]


class GameDataVersionFilter:
    def __init__(self):
        self._version_names = ["postfix", "patch", "minor", "major"]
        self.version_sequence = []

    def __getitem__(self, idx):
        self.version_sequence = [(self._version_names.pop(), idx)]
        return self

    def get(self, pool=None, selected=None) -> [GameDataFileVersion]:
        if selected is None:
            selected = self.version_sequence[:]

        if not selected:
            return GameDataFileVersion.file_versions[:]

        selected_one = selected[0]

        if pool is None:
            pool = GameDataFileVersion.file_versions

        filtered_pool = []
        for version in pool:
            if getattr(version, selected_one[0]) == selected_one[1]:
                filtered_pool += [version]
        selected = selected[1:]
        if selected:
            filtered_pool = self.get(pool=filtered_pool, selected=selected)

        return filtered_pool

    def latest(self) -> GameDataFileVersion:
        pool = self.get()
        latest_seen = None

        for version in pool:
            if not latest_seen:
                latest_seen = version
            elif latest_seen.build < version.build:
                latest_seen = version

        return latest_seen

    @classmethod
    def get_build(self, build: int) -> Optional[GameDataFileVersion]:
        for version in GameDataFileVersion.file_versions:
            if version.build == build:
                return version


def get(major=None, minor=None, patch=None, postfix=None, build=None) -> GameDataFileVersion:
    from production_planner.core import CONFIG

    re_parse_fname = re.compile("production_buildings_v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)\.(?P<postfix>\d+)_(?P<build>\d+).json")

    dpath = os.path.split(os.path.abspath(__file__))[0]
    for entry in os.scandir(dpath):
        match = re_parse_fname.match(entry.name)
        if entry.is_file() and match:
            GameDataFileVersion(entry.path,
                                int(match.group("major")),
                                int(match.group("minor")),
                                int(match.group("patch")),
                                int(match.group("postfix")),
                                int(match.group("build")))
    if build:
        version = GameDataVersionFilter.get_build(build)
        return Path(version.fpath)
    else:
        filt = GameDataVersionFilter()
        for v in [major, minor, patch, postfix]:
            if v is None:
                break
            filt[v]
        version = filt.latest()
        return version


def main():
    import parse
    from production_planner.core import ProducerEncoder

    arguments = docopt(__doc__)
    production_buildings = OrderedDict()
    data = parse.docs_json(Path(arguments['<docs.json-path>']))
    if data:
        for prod in data:
            p = json.dumps(prod, cls=ProducerEncoder, indent=2)
            production_buildings.update(json.loads(p))
        print(json.dumps(production_buildings, cls=ProducerEncoder, indent=2))


if __name__ == "__main__":
    main()
