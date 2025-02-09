#! /bin/env python
# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from . import core
from .core import (
    CONFIG,
    DataFile,
    NodeTree,
    Node,
    Recipe,
    ensure_keys
)
from .datatable import PlannerTable

import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import (
    Optional,
    Tuple,
)

from textual import log

import yaml
import json_store


# TODO: support multiple views into the same file (shared `staging` data, all pointing to the same NodeTree instance)


@dataclass
class DataChunk:
    target: Optional[DataFile] = None
    checksum: int = hash(None)
    # TODO: actually populate and use mtime
    mtime: int = 0
    _data: Optional[NodeTree] = None
    sink: None = None

    @property
    def data(self) -> NodeTree:
        return self._data

    @data.setter
    def data(self, value):
        self._data = value
        self.checksum = hash(value)

    def reset(self) -> None:
        pass

    def save(self, data=None) -> Tuple[DataFile] | bool | None:
        """
        Returns
        * True  if successful
        * False if target is None
        * None  if an error occurs
        """
        pass

    def load(self) -> bool | None:
        """
        Returns
        * True  if successful
        * False if target doesn't exist
        * None  if an error occurs
        """
        pass


class Sink:
    Chunk = DataChunk
    tystr = "sink"

    def __init__(self, table: PlannerTable = None, staging_root: Path | None = None, table_iid: str = "", *args, **kwargs):
        if staging_root:
            staging_target = staging_root / f"{table_iid}.yaml"

            config_target = staging_target.with_suffix(staging_target.suffix + ".sink")
            self.config = json_store.open(config_target, json_kw={ "indent": 4 })
            ensure_keys(self.config, {
                "target": None,
            })
        else:
            staging_target = None
            self.config = { "target": None }

        self.staging_root = staging_root
        self.iid_sink = table_iid

        self.staging = self.Chunk(DataFile.get(staging_target) if staging_target else staging_target, sink=self)
        sink_target = DataFile.get(self.config["target"]) if self.config["target"] else None
        self.sink = self.Chunk(sink_target, sink=self)

        self.app = core.APP
        self.table = table if table else PlannerTable(sink=self, header_control=True)
        self.table.sink = self

    @property
    def is_table_shown(self) -> bool:
        return self.app.is_table_shown(self.table)

    @property
    def title(self):
        title = f"*{self.name}" if self.is_dirty else self.name
        return title

    @property
    def subpath(self) -> Path:
        if self.sink.target:
            return self.sink.target.subpath
        else:
            return "<unnamed>.yaml"

    @property
    def name(self) -> str:
        return os.path.splitext(self.subpath)[0]

    @property
    def is_dirty(self) -> bool:
        # TODO: hook into filesystem and watch for external changes to sink
        # NOTE: `self.staging.data` and `self.table` always point to the same table instance !
        # NOTE: `self.sink.data` should never be mutated - only used for copying and comparing
        self.staging.checksum = hash(self.staging.data)
        return self.staging.checksum != self.sink.checksum

    def load(self, subpath=None) -> Optional[DataFile]:
        def parse_error(target):
            self.app.notify(f"Could not parse {self.tystr}: `{target.subpath}`\n{target.root}", severity="error", timeout=10)

        def not_exist_error(target):
            self.app.notify(f"Target does not exist: `{target.subpath}`\n{target.root}", severity="error", timeout=10)

        if subpath:
            sinkfile = DataFile.get(subpath)
            if sinkfile.fullpath.is_file():
                self.sink.target = sinkfile
            else:
                not_exist_error(self.sink.target)
                return

        if subpath:
            maybe_apply_staging = False
        else:
            maybe_apply_staging = staging_result = self.staging.load()
            if staging_result is False:
                # Note: The behaviour we want from non-existant files is different between `sink` and `staging`
                #    - sink:    preserve `None` value
                #    ` staging: create empty NodeTree and link to PlannerTable
                #
                # This allows `is_dirty` to keep doing its work correctly.
                self.staging.data = NodeTree.from_nodes([])

        if maybe_apply_staging is None:
            parse_error(self.staging.target)

        sink_result = self.sink.load()
        if sink_result is None:
            parse_error(self.sink.target)
        elif sink_result is False and self.sink.target:
            ...

        if sink_result:
            if maybe_apply_staging is True:
                # TODO: pop up a modal to confirm overwrite of `staging`
                if self.sink.mtime > self.staging.mtime and self.sink.data:
                    self.staging.data = parse_yaml(yaml.dump(self.sink.data))
            else:
                self.staging.data = parse_yaml(yaml.dump(self.sink.data))

        self.table.apply_data(self.staging.data)
        if not subpath:
            # Can happen if the `.staging` folder / sink is new
            if not self.sink.target:
                return None
            sinkfile = self.sink.target
        return sinkfile

    def load_yaml(self, data: str):
        self.staging.data = parse_yaml(data)
        self.staging.checksum = hash(self.staging.data)
        self.table.apply_data(self.staging.data)

    def staging_commit(self) -> Optional[DataFile]:
        # Preserve `None` sentinel value as is (gets shown as <untitled>)
        self.config["target"] = str(self.sink.target.linkpath) if self.sink.target else self.sink.target
        self.config.sync()
        return self.staging.save()

    def sink_commit(self, subpath=None) -> Optional[Tuple[DataFile]]:
        if subpath:
            self.sink.target = DataFile.get(subpath)

        # implicitly sets `sink.data = staging.data`
        result = self.sink.save(self.staging.data)
        if result:
            self.config["target"] = str(self.sink.target.linkpath)
        else:
            return

        # implicitly serializes and deserializes `sink.data` and assigns it to `staging.data`
        # necessary to keep `staging.data is not sink.data` true
        self.staging.reset(self.sink)
        self.table.apply_data(self.staging.data)
        return result


class VoidSink(Sink):
    pass


class FileChunk(DataChunk):
    def reset(self, source_chunk=None, delete_config=False) -> None:
        if self.target and self.target.fullpath.is_file():
            self.target.fullpath.unlink()

        if source_chunk:
            self.data = parse_yaml(yaml.dump(source_chunk.data))
            self.sink.table.apply_data(self.data)
        else:
            self.data = None

    def save(self, data=None) -> Tuple[DataFile] | bool | None:
        """
        Returns
        * True  if successful
        * False if target invalid or uninitialized
        * None  if an error occurs
        """
        if self.target is None:
            return False

        data = data if data else self.data
        datafile = self.target
        try:
            os.makedirs(datafile.fullpath.parent, exist_ok=True)
            with open(datafile.fullpath, "w") as fp:
                yaml.dump(data, fp)
            self.data = data
        except (FileNotFoundError, TypeError, WindowsError, OSError):
            return None
        return datafile

    def load(self) -> bool | None:
        """
        Returns
        * True  if successful
        * False if target doesn't exist
        * None  if an error occurs
        """
        if self.target and self.target.fullpath.is_file():
            with open(self.target.fullpath, "r") as fp:
                raw = fp.read()
            self.data = parse_yaml(raw)
            return True if self.data else None
        else:
            return False


class FileSink(Sink):
    Chunk = FileChunk
    tystr = "file"


class PlannerManager:
    def __init__(self, app, iid_name="main"):
        self.app = app
        self._iid_name = f"[{iid_name}]"
        self.active_sink = None

        os.makedirs(self.dpath_staging, exist_ok=True)
        self.config = json_store.open(self.fpath_config, json_kw={ "indent": 4 })
        ensure_keys(self.config, {
            "active_sink": "000.yaml",
        })

        self.sinks = []
        self.re_staging_fname = re.compile(r"^(\d{3}).yaml$")

    def load(self):
        sinks = []

        os.makedirs(self.dpath_staging, exist_ok=True)
        for entry in os.scandir(self.dpath_staging):
            if not entry.is_file():
                continue

            match = self.re_staging_fname.match(entry.name)
            if match:
                table_iid = match.group(1)
                sink = FileSink(None, self.dpath_staging, table_iid=table_iid)
                sinks += [sink]
        self.sinks = sinks

        if not self.sinks:
            self.add_sink()

        self.active_sink = self.sinks[0]
        table = self.active_sink.table
        self.app.swap_active_table(self.active_sink.table)

    def reload_all(self):
        self.load()

    def add_sink(self):
        self.sinks += [FileSink(None, self.dpath_staging, table_iid=f"{len(self.sinks):>03}")]

    def staging_commit(self):
        self.config.sync()
        for sink in self.sinks:
            sink.staging_commit()

    def reset_sink_from_path(self, subpath, keep_cache=True):
        target = DataFile.get(subpath)
        for sink in self.sinks:
            if sink.sink.target.fullpath == target.fullpath:
                sink.sink.reset()
            # FIXME: likely broken
            if not keep_cache:
                sink.staging.reset()

    @property
    def fpath_config(self) -> Path:
        return self.dpath_staging / ".config.json"

    @property
    def dpath_staging(self) -> Path:
        return self.dpath_data / ".staging" / self._iid_name

    @property
    def dpath_data(self) -> Path:
        return CONFIG.dpath_data


def parse_yaml(raw: str) -> Optional[NodeTree]:
    parsed = yaml.unsafe_load(raw)
    match parsed:
        case None:
            return NodeTree.from_nodes([])
        case NodeTree():
            tree = parsed
        case[Node(), *_]:
            tree = NodeTree.from_nodes(parsed)
        case[Recipe(), NodeTree()]:
            _, tree = parsed
        case[Recipe(), *_]:
            _, data = parsed
            tree = NodeTree.from_nodes(parsed)
        case _:
            log(f"Could not parse data: `{parsed}`", timeout=10)
            return
    assert isinstance(tree, NodeTree)
    return tree


def load_data(target: Path) -> NodeTree | None | bool:
    if target and target.is_file():
        with open(target, "r") as fp:
            raw = fp.read()
        tree = parse_yaml(raw)
        return tree if tree else None
    else:
        return False
