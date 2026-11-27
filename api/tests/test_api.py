"""End-to-end API flows with Clerk auth and the VLM graph stubbed out."""

import uuid

import pytest
from fastapi import Header
from fastapi.testclient import TestClient

from app import auth
from app.analysis import runner
from app.main import app


async def fake_user_id(x_test_user: str = Header()) -> str:
    return x_test_user


class FakeGraph:
    calls: list[dict] = []

    async def ainvoke(self, state):
        self.calls.append(state)
        return {
            "perception": {"is_readable": True, "content_type": "code"},
            "review": {"verdict": "correct", "score": 90, "summary": "ok"},
        }


@pytest.fixture
def client(monkeypatch):
    app.dependency_overrides[auth.current_user_id] = fake_user_id
    monkeypatch.setattr(runner, "review_graph", FakeGraph())
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def as_(user):
    return {"x-test-user": user}


def uid(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
COURSE = "# R\n## A\n- A1\n  - A1a\n  - A1b\n## B"  # leaves: A1a, A1b, B


@pytest.fixture
def world(client):
    """A mentor with two courses and a linked mentee (no access granted yet)."""
    mentor, mentee = uid("mentor"), uid("mentee")
    code = client.post("/me/onboard", json={"role": "mentor", "name": "M"}, headers=as_(mentor)).json()[
        "invite_code"
    ]
    client.post("/me/onboard", json={"role": "mentee", "name": "S"}, headers=as_(mentee))
    c1 = client.post("/roadmaps", json={"source": COURSE}, headers=as_(mentor)).json()["id"]
    c2 = client.post("/roadmaps", json={"source": "# Other\n- X"}, headers=as_(mentor)).json()["id"]
    assert client.post("/me/join", json={"invite_code": code.lower()}, headers=as_(mentee)).status_code == 200
    return {"m": as_(mentor), "s": as_(mentee), "mentee_id": mentee, "c1": c1, "c2": c2, "code": code}


def nodes_by_title(client, headers, course, node_id=None, **params):
    path = f"/roadmaps/{course}" + (f"/nodes/{node_id}" if node_id else "")
    d = client.get(path, headers=headers, params=params).json()
    return d, {c["title"]: c for c in d["children"]}


def test_course_access_is_per_course(client, world):
    m, s, sid = world["m"], world["s"], world["mentee_id"]

    # Joined, but nothing granted yet.
    assert client.get("/roadmaps", headers=s).json() == []
    assert client.get(f"/roadmaps/{world['c1']}", headers=s).status_code == 404
    assert [x["name"] for x in client.get("/me", headers=s).json()["mentors"]] == ["M"]

    assert client.put(f"/roadmaps/{world['c1']}/access/{sid}", headers=m).status_code == 204
    visible = client.get("/roadmaps", headers=s).json()
    assert [r["id"] for r in visible] == [world["c1"]]
    assert visible[0]["progress"] == {"done": 0, "total": 3, "percent": 0, "completed_at": None}
    assert client.get(f"/roadmaps/{world['c2']}", headers=s).status_code == 404

    members = client.get(f"/roadmaps/{world['c1']}/members", headers=m).json()
    assert [(x["mentee"]["id"], x["has_access"]) for x in members] == [(sid, True)]
    mentee = client.get(f"/mentees/{sid}", headers=m).json()
    assert {c["roadmap"]["id"]: c["has_access"] for c in mentee["courses"]} == {
        world["c1"]: True,
        world["c2"]: False,
    }

    # Mentees can't grant, other mentors can't grant to someone else's mentee.
    assert client.put(f"/roadmaps/{world['c2']}/access/{sid}", headers=s).status_code == 403
    other = uid("mentor")
    client.post("/me/onboard", json={"role": "mentor"}, headers=as_(other))
    other_course = client.post("/roadmaps", json={"source": "- Z"}, headers=as_(other)).json()["id"]
    assert client.put(f"/roadmaps/{other_course}/access/{sid}", headers=as_(other)).status_code == 404

    assert client.delete(f"/roadmaps/{world['c1']}/access/{sid}", headers=m).status_code == 204
    assert client.get("/roadmaps", headers=s).json() == []


def test_progress_and_completion(client, world):
    m, s, sid, c1 = world["m"], world["s"], world["mentee_id"], world["c1"]
    client.put(f"/roadmaps/{c1}/access/{sid}", headers=m)

    _, top = nodes_by_title(client, s, c1)
    a = top["A"]
    assert (a["leaves_done"], a["leaves_total"], a["done"]) == (0, 2, False)
    _, a_kids = nodes_by_title(client, s, c1, a["id"])
    _, a1_kids = nodes_by_title(client, s, c1, a_kids["A1"]["id"])

    # Mentee marks one leaf.
    r = client.put(f"/roadmaps/{c1}/nodes/{a1_kids['A1a']['id']}/done", json={"done": True}, headers=s)
    assert r.status_code == 200
    assert r.json()["roadmap"]["progress"]["done"] == 1
    _, top = nodes_by_title(client, s, c1)
    assert (top["A"]["leaves_done"], top["A"]["done"]) == (1, False)

    # Marking a parent marks its whole subtree.
    client.put(f"/roadmaps/{c1}/nodes/{a['id']}/done", json={"done": True}, headers=s)
    _, top = nodes_by_title(client, s, c1)
    assert top["A"]["done"] is True and top["B"]["done"] is False

    # Mentor sees the same progress, and must say whose progress to change.
    d, top_m = nodes_by_title(client, m, c1, mentee_id=sid)
    assert d["subject"]["id"] == sid
    assert d["roadmap"]["progress"]["percent"] == 67
    _, top_plain = nodes_by_title(client, m, c1)
    assert top_plain["A"]["done"] is None
    assert client.put(f"/roadmaps/{c1}/nodes/{a['id']}/done", json={"done": True}, headers=m).status_code == 422

    # Mentor completes the course for the mentee -> everything is done.
    r = client.put(f"/roadmaps/{c1}/done", json={"done": True, "mentee_id": sid}, headers=m)
    p = r.json()["roadmap"]["progress"]
    assert (p["percent"], p["completed_at"] is not None) == (100, True)

    # Reopening a topic un-completes the course but keeps other topics.
    client.put(f"/roadmaps/{c1}/nodes/{top['B']['id']}/done", json={"done": False}, headers=s)
    p = client.get("/roadmaps", headers=s).json()[0]["progress"]
    assert (p["done"], p["completed_at"]) == (2, None)

    members = client.get(f"/roadmaps/{c1}/members", headers=m).json()
    assert members[0]["progress"]["done"] == 2

    # Can't view progress of a mentee without access.
    assert client.get(f"/roadmaps/{world['c2']}", headers=m, params={"mentee_id": sid}).status_code == 404


def test_submission_flow(client, world):
    m, s, sid, c1 = world["m"], world["s"], world["mentee_id"], world["c1"]
    client.put(f"/roadmaps/{c1}/access/{sid}", headers=m)
    _, top = nodes_by_title(client, s, c1)
    _, a_kids = nodes_by_title(client, s, c1, top["A"]["id"])
    a1 = a_kids["A1"]

    r = client.post(
        "/submissions",
        data={"node_id": a1["id"], "note": "my solution"},
        files=[("images", ("s.png", PNG, "image/png"))],
        headers=s,
    )
    assert r.status_code == 201, r.text
    sub_id = r.json()["id"]

    sub = client.get(f"/submissions/{sub_id}", headers=m).json()
    assert sub["status"] == "done"
    assert sub["ai_review"]["verdict"] == "correct"
    assert sub["topic_path"] == ["A", "A1"]
    assert FakeGraph.calls[-1]["topic_path"] == ["A", "A1"]
    assert [x["id"] for x in client.get("/submissions", headers=m, params={"mentee_id": sid}).json()] == [sub_id]

    img_id = sub["images"][0]["id"]
    assert client.get(f"/submissions/{sub_id}/images/{img_id}", headers=m).content == PNG

    other = uid("mentor")
    client.post("/me/onboard", json={"role": "mentor"}, headers=as_(other))
    assert client.get(f"/submissions/{sub_id}", headers=as_(other)).status_code == 404

    r = client.patch(f"/submissions/{sub_id}/comment", json={"mentor_comment": "nice"}, headers=m)
    assert r.json()["mentor_comment"] == "nice"

    # Can't submit to a course without access.
    _, other_top = nodes_by_title(client, m, world["c2"])
    r = client.post(
        "/submissions",
        data={"node_id": other_top["X"]["id"]},
        files=[("images", ("s.png", PNG, "image/png"))],
        headers=s,
    )
    assert r.status_code == 404

    assert client.delete(f"/roadmaps/{c1}", headers=m).status_code == 204
    assert client.get("/submissions", headers=s).json() == []


def test_remove_mentee_revokes_access(client, world):
    m, s, sid = world["m"], world["s"], world["mentee_id"]
    client.put(f"/roadmaps/{world['c1']}/access/{sid}", headers=m)
    assert client.delete(f"/mentees/{sid}", headers=m).status_code == 204
    assert client.get("/roadmaps", headers=s).json() == []
    assert client.get("/mentees", headers=m).json() == []
    assert client.get("/me", headers=s).json()["mentors"] == []
