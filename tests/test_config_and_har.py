"""Tests for config and HAR utilities."""

from pathlib import Path

# Allow importing from project root
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import load_config, get_config_path, ISO_639_CODES


def test_load_config_returns_dict():
    """load_config returns a dict with expected keys."""
    cfg = load_config()
    assert isinstance(cfg, dict)
    assert "base_dir" in cfg
    assert "api_key" in cfg
    assert "whisper_options" in cfg


def test_get_config_path():
    """get_config_path returns path ending in settings.json."""
    p = get_config_path()
    assert p.name == "settings.json"
    assert "config" in str(p)


def test_iso639_codes():
    """ISO_639_CODES has common languages."""
    assert ISO_639_CODES["English"] == "eng"
    assert ISO_639_CODES["French"] == "fra"
    assert "Spanish" in ISO_639_CODES


if __name__ == "__main__":
    test_load_config_returns_dict()
    test_get_config_path()
    test_iso639_codes()
    print("All tests passed.")
