import pytest

from ctrlcoco import db


@pytest.fixture
def conn():
    """Database sementara di memori: bersih untuk tiap tes, hilang saat selesai."""
    c = db.connect(":memory:")
    db.init_db(c)
    yield c
    c.close()
