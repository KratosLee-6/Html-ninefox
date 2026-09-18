from pathlib import Path

import pytest

from scripts import check_release_version


def _write_release_tree(root: Path, *, release_link: bool) -> None:
    version = "0.5.0rc1"
    (root / "htmlninefox").mkdir(exist_ok=True)
    (root / "packaging" / "linux").mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(f'version = "{version}"\n', encoding="utf-8")
    (root / "htmlninefox" / "__init__.py").write_text(
        f'__version__ = "{version}"\n', encoding="utf-8"
    )
    suffix = f" releases/tag/v{version}" if release_link else ""
    (root / "README.md").write_text(f"开发基线 `{version}`{suffix}\n", encoding="utf-8")
    (root / "README.en.md").write_text(
        f"Development baseline `{version}`{suffix}\n", encoding="utf-8"
    )
    (root / "uv.lock").write_text(
        f'name = "htmlninefox"\nversion = "{version}"\n', encoding="utf-8"
    )
    (root / "packaging" / "linux" / "install.sh").write_text(
        "__HTMLNINEFOX_VERSION__\n", encoding="utf-8"
    )


def test_development_metadata_does_not_require_unpublished_release_link(tmp_path, monkeypatch):
    _write_release_tree(tmp_path, release_link=False)
    monkeypatch.setattr(check_release_version, "ROOT", tmp_path)

    assert check_release_version.validate_release_metadata() == "0.5.0rc1"


def test_application_tag_still_requires_matching_release_link(tmp_path, monkeypatch):
    _write_release_tree(tmp_path, release_link=False)
    monkeypatch.setattr(check_release_version, "ROOT", tmp_path)

    with pytest.raises(SystemExit, match="releases/tag/v0.5.0rc1"):
        check_release_version.validate_release_metadata("v0.5.0rc1")

    _write_release_tree(tmp_path, release_link=True)
    assert check_release_version.validate_release_metadata("v0.5.0rc1") == "0.5.0rc1"
