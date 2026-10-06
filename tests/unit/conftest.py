import pytest

from private_assistent.config import get_settings


@pytest.fixture(autouse=True)
def isolated_runtime_home(tmp_path, monkeypatch):
    monkeypatch.setenv("PRIVATE_ASSISTENT_WORKING_DIR", str(tmp_path / "working-dir"))
    monkeypatch.delenv("PRIVATE_ASSISTENT_CONFIG_PATH", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


