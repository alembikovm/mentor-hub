import pytest

from app.roadmap_parser import RoadmapParseError, parse_roadmap

MD = """# Frontend Roadmap
Everything a junior frontend dev needs.

## HTML & CSS
Basics of markup.
- Semantics
  - Forms
    Labels, inputs, validation.
  - Tables
- Flexbox

## JavaScript
### Closures
### Promises
- async/await
"""


def titles(nodes):
    return [n.title for n in nodes]


def test_markdown_tree():
    r = parse_roadmap(MD)
    assert r.title == "Frontend Roadmap"
    assert r.description == "Everything a junior frontend dev needs."
    assert titles(r.children) == ["HTML & CSS", "JavaScript"]

    html = r.children[0]
    assert html.description == "Basics of markup."
    assert titles(html.children) == ["Semantics", "Flexbox"]
    assert titles(html.children[0].children) == ["Forms", "Tables"]
    assert html.children[0].children[0].description == "Labels, inputs, validation."

    js = r.children[1]
    assert titles(js.children) == ["Closures", "Promises"]
    assert titles(js.children[1].children) == ["async/await"]
    assert r.count() == 9


def test_plain_list_without_headings():
    r = parse_roadmap("- A\n  - A1\n- B\n", fallback_title="X")
    assert r.title == "X"
    assert titles(r.children) == ["A", "B"]
    assert titles(r.children[0].children) == ["A1"]


def test_json():
    r = parse_roadmap('{"title": "T", "children": [{"title": "A", "children": ["A1"]}]}')
    assert r.title == "T"
    assert r.children[0].children[0].title == "A1"


@pytest.mark.parametrize("src", ["", "# Only title\n", '{"title": "x"}', '[{"nope": 1}]'])
def test_errors(src):
    with pytest.raises(RoadmapParseError):
        parse_roadmap(src)
