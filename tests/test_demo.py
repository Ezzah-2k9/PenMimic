import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("flask")


@pytest.fixture()
def client(samples_dir, monkeypatch):
    monkeypatch.setenv("PENMIMIC_SAMPLES", str(samples_dir))
    path = Path(__file__).resolve().parents[1] / "demo" / "app.py"
    spec = importlib.util.spec_from_file_location("demo_app", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["demo_app"] = module
    spec.loader.exec_module(module)
    return module.app.test_client()


def test_page_loads(client):
    assert client.get("/").status_code == 200


def test_render_returns_png(client):
    res = client.post("/render", json={"text": "Hello", "paper": "lined"})
    assert res.status_code == 200 and res.data[:4] == b"\x89PNG"


def test_empty_text_is_rejected(client):
    assert client.post("/render", json={"text": "   "}).status_code == 400


def test_bad_colour_and_paper_are_rejected(client):
    assert client.post("/render", json={"text": "x", "ink": "red; drop"}).status_code == 400
    assert client.post("/render", json={"text": "x", "paper": "graph"}).status_code == 400


