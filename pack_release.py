# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
from pathlib import Path
import pip
from zipfile import ZipFile, ZIP_DEFLATED
from dataclasses import dataclass
from typing import Optional


INSTALL_BAT = """
pip install --find-links ./dependencies {}
pause
"""


@dataclass
class PackFile:
    source_path: Path
    _destination: Optional[Path] = None

    @property
    def destination(self) -> Path:
        return self._destination or Path(self.source_path.name)


def package(root: Path, whl_path: Path, pack_files: [PackFile]):
    fpath_zip = whl_path.with_suffix(whl_path.suffix + ".zip")
    package_root = Path(whl_path.with_suffix("").name)

    with ZipFile(fpath_zip, "w", compression=ZIP_DEFLATED) as package:
        with open(whl_path, "rb") as fp:
            package.writestr(str(package_root / whl_path.name),
                             fp.read())

        for pack_file in pack_files:
            with open(pack_file.source_path, "rb") as fp:
                package.writestr(str(package_root / pack_file.destination),
                                 fp.read())

        package.writestr(str(package_root / "install.bat"),
                         INSTALL_BAT.format(whl_path.name))
    print(f"Package written to `{fpath_zip}`")


def whl_files(root):
    for entry in os.scandir(root):
        if entry.is_file() and os.path.splitext(entry.path)[1] == ".whl":
            yield Path(entry.path)


def main():
    root = Path(__file__).parent

    for whl in whl_files(root):
        os.remove(whl)

    pip.main(["wheel", str(root)])

    wheels = list(whl_files(root))
    for whl in wheels:
        if whl.name.startswith("production_planner"):
            wheels.remove(whl)

            pack_files = [
                PackFile(root / "run.bat"),
                PackFile(root / "README.md"),
                PackFile(root / "LICENSE")
            ]
            pack_files += [PackFile(whl, Path("dependencies") / whl.name) for whl in wheels]

            package(root, whl, pack_files)
            break


if __name__ == "__main__":
    main()
