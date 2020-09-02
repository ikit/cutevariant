import sqlite3

FILTER_DATA = {"AND": [{"field": "chr", "operator": ">", "value": 4}]}

from .widgets import FilterModel


def test_model(qtbot, qtmodeltester):
    conn = sqlite3.connect("examples/test.db")

    model = FilterModel(conn)
    model.load(FILTER_DATA)
    qtmodeltester.check(model)
