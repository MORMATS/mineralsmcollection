from pathlib import Path

from src import settings


def test_setting_precedence_environment_over_env_file(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("ADMIN_PASSWORD_HASH=from-file\n", encoding="utf-8")
    monkeypatch.setattr(settings, "ENV_PATH", env_path)
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", "from-env")

    assert settings.get_setting("ADMIN_PASSWORD_HASH") == "from-env"


def test_setting_reads_updated_env_file(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    monkeypatch.setattr(settings, "ENV_PATH", env_path)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)

    env_path.write_text("ADMIN_PASSWORD_HASH=first\n", encoding="utf-8")
    assert settings.get_setting("ADMIN_PASSWORD_HASH") == "first"

    env_path.write_text("ADMIN_PASSWORD_HASH=second\n", encoding="utf-8")
    assert settings.get_setting("ADMIN_PASSWORD_HASH") == "second"


def test_required_setting_raises_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ENV_PATH", Path(tmp_path / ".env"))
    monkeypatch.delenv("DATABASE_URL", raising=False)

    try:
        settings.get_required_setting("DATABASE_URL")
    except RuntimeError as exc:
        assert "DATABASE_URL is required" in str(exc)
    else:
        raise AssertionError("Expected missing required setting to raise")
