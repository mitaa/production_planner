import re
import json
from dataclasses import dataclass

from collections import OrderedDict

from bs4 import BeautifulSoup


@dataclass
class Ingredient:
    name: str
    count: int

    def __post_init__(self):
        re_name = re.compile(r"\d+\.?\d*/min")
        re_words = re.compile(r"([^\w\d\s]*)", flags=re.ASCII)
        self.name = re_words.sub("", re_name.split(self.name)[0]).strip()
        self.count = int(self.count)

    @classmethod
    def from_raw(cls, data):
        pass

    def __str__(self):
        return f"({self.count}x {self.name})"

    def jsonify(self):
        return [self.count, self.name]


def parse_ingredients(data):
    re_ingredients_list = re.compile(r"(\d+)x")

    parts = re_ingredients_list.split(data)[1:]
    quantities = parts[0::2]
    resources = parts[1::2]
    ingredients = list(Ingredient(*res) for res in zip(resources, quantities))
    return ingredients


class Recipe:
    def __init__(self, data):
        # print(repr(data[2]))
        # print()
        self.name = data[0].replace("alt ", "").replace("FICSâ�•MAS", "")
        self.data = data
        self.cycle_time = data[1]

        self.inputs = parse_ingredients(data[2])
        self.outputs = parse_ingredients(data[3])

    def __str__(self):
        return f"{self.name}/{self.cycle_time} < {', '.join(map(str, self.inputs))} > {', '.join(map(str, self.outputs))}"

    def jsonify(self):
        s_inputs = json.dumps(list(i.jsonify() for i in self.inputs))
        s_outputs = json.dumps(list(i.jsonify() for i in self.outputs))
        return f'    "{self.name}": [{self.cycle_time}, {s_inputs}, {s_outputs}]'


def main():
    fpath = "test_data.html"
    fp = open(fpath, errors="replace")
    data = fp.read()
    # data = input("Enter HTML table:")
    soup = BeautifulSoup(data, "html.parser")
    print("{")
    are_we_commaing = False
    for row in soup.find_all("tr"):
        if are_we_commaing:
            print(",")
        col_data = list(c.text for c in row.find_all("td"))
        if not col_data:
            continue
        recipe = Recipe(col_data)
        print(recipe.jsonify(), end="")
        are_we_commaing = True
    else:
        print("")

    print("}")


if __name__ == "__main__":
    main()
