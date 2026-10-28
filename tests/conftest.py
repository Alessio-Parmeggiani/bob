import pytest


@pytest.fixture(autouse=True)
def bob_home(tmp_path, monkeypatch):
    """Keep every test's memory away from the real ~/.bob."""
    monkeypatch.setenv("BOB_HOME", str(tmp_path / "bob-home"))
