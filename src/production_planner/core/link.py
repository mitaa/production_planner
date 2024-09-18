# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import platformdirs
import json_store


def static(fn):
    return fn()


def ensure_key(store, key, default):
    if key in store:
        actual = store[key]
        if type(actual) is dict and type(default) is dict:
            ensure_keys(actual, key_def_pairings=default)
            store[key] = actual
    else:
        store[key] = default


def ensure_keys(store, key_def_pairings={}):
    for k, v in key_def_pairings.items():
        ensure_key(store, k, v)


@static
def CONFIG():
    class ConfigStore:
        def __init__(self):
            self.dpath_data = Path(platformdirs.user_data_dir("production_planner", "mitaa"))

        @property
        def dpath_data(self):
            return self._dpath_data

        @dpath_data.setter
        def dpath_data(self, value):
            self._dpath_data = Path(value)
            os.makedirs(self.dpath_data, exist_ok=True)
            # TODO: store dpath_data in the config when requested
            self.fpath_config = self.dpath_data / ".config.json"

            # TODO: reload/reroot already open files?
            #       currently broken somehow
            # try:
            #     app = textual.active_app.get()
            #     app.notify(f"Portable data path set to: {value}", timeout=10)
            #     if APP and APP.header:
            #         APP.manager.reload_all()
            # except (LookupError, ScreenStackError):
            #     pass

        @property
        def fpath_config(self):
            return self._fpath_config

        @fpath_config.setter
        def fpath_config(self, value):
            self._fpath_config = Path(value)
            self.store = json_store.open(self.fpath_config, json_kw={ "indent": 4 })
            ensure_keys(self.store, {
                "app": {
                    "startup_help": True,
                },
                "select_producer": {
                    "show_sidebar": True,
                }
            })

    return ConfigStore()


@dataclass
class DataFile:
    subpath: Path
    _root: Path
    _fullpath: Path = None

    def __post_init__(self):
        self._fullpath = self.root / self.subpath

    @classmethod
    def get(self, path: str | Path) -> Self:
        path = Path(path)
        root = CONFIG.dpath_data
        if path.is_absolute():
            try:
                path = path.relative_to(CONFIG.dpath_data)
            except ValueError:
                root = path.parent
                return ExternalFile(Path(path.name), root)
        return PortableFile(path)

    @property
    def root(self):
        return self._root

    @root.setter
    def root(self, value):
        self._root = value
        self._fullpath = Path(value) / self.subpath.name

    @property
    def fullpath(self):
        return self._fullpath

    @property
    def linkpath(self):
        return self.fullpath

    def __bool__(self) -> bool:
        return bool(self.subpath.name)


@dataclass
class PortableFile(DataFile):
    _root: Path = None

    def __post_init__(self):
        self._root = CONFIG.dpath_data
        super().__post_init__()

    @property
    def linkpath(self):
        return self.subpath


class ExternalFile(DataFile):
    @DataFile.fullpath.setter
    def fullpath(self, value):
        self._fullpath = Path(value)
        self._root = self._fullpath.parent
        self.subpath = self._fullpath.name


class ModuleFile:
    file: DataFile

    def __init__(self, module_id: str):
        self.file = DataFile.get(os.path.splitext(module_id)[0] + ".yaml")

    @property
    def fullpath(self):
        return self.file.fullpath

    @property
    def linkpath(self):
        return self.file.linkpath

    @property
    def id(self):
        return os.path.splitext(self.linkpath)[0]
