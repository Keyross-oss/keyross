import openpyxl
import pytest


def make_xlsx(path, rows, header=("N°", "Désignation", "Unité", "Quantité", "PU", "Montant")):
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(list(header))
    for r in rows:
        ws.append(list(r))
    wb.save(path)
    return path


@pytest.fixture
def good_doc(tmp_path):
    return make_xlsx(tmp_path / "good.xlsx", [
        ("1.1", "Terrassement", "m3", 10, 25.0, 250.0),
        ("1.2", "Remblai", "m3", 4, 12.5, 50.0),
        (None, "Sous-total lot 1", None, None, None, 300.0),
        ("2.1", "Béton de propreté", "m2", 20, 8.0, 160.0),
        (None, "Sous-total lot 2", None, None, None, 160.0),
    ])


@pytest.fixture
def bad_totals_doc(tmp_path):
    return make_xlsx(tmp_path / "bad.xlsx", [
        ("1.1", "Terrassement", "m3", 10, 25.0, 250.0),
        ("1.2", "Remblai", "m3", 4, 12.5, 50.0),
        (None, "Sous-total lot 1", None, None, None, 295.0),   # wrong: 300 expected
    ])
