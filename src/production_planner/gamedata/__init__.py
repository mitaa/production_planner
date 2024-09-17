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

from production_planner.core import ProducerEncoder

import parse

import json
from pathlib import Path
from collections import OrderedDict


def main():
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
