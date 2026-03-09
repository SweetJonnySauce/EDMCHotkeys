from __future__ import annotations

import pytest

from edmc_hotkeys.semver import SemVerError, add_v_prefix, is_valid_semver, parse_semver, strip_v_prefix


def test_parse_semver_accepts_stable_and_prerelease_values() -> None:
    stable = parse_semver("1.2.3")
    prerelease = parse_semver("1.2.3-alpha.1+build.9")

    assert stable.core == "1.2.3"
    assert not stable.is_prerelease
    assert prerelease.prerelease == ("alpha", "1")
    assert prerelease.build == ("build", "9")
    assert prerelease.is_prerelease


def test_parse_semver_supports_v_prefixed_tags_when_enabled() -> None:
    parsed = parse_semver("v1.2.3-beta-1", allow_v_prefix=True, require_v_prefix=True)
    assert parsed.to_string(v_prefix=True) == "v1.2.3-beta-1"
    assert parsed.to_string(v_prefix=False) == "1.2.3-beta-1"


def test_parse_semver_rejects_invalid_identifiers() -> None:
    with pytest.raises(SemVerError):
        parse_semver("1.2.3-01")

    with pytest.raises(SemVerError):
        parse_semver("v1.2.3", allow_v_prefix=False)


def test_prefix_helpers_round_trip() -> None:
    assert strip_v_prefix("v2.3.4-alpha.1") == "2.3.4-alpha.1"
    assert add_v_prefix("2.3.4-alpha.1") == "v2.3.4-alpha.1"


def test_is_valid_semver_variants() -> None:
    assert is_valid_semver("v0.5.0-alpha-1", allow_v_prefix=True, require_v_prefix=True)
    assert not is_valid_semver("0.5.0-alpha-1", allow_v_prefix=True, require_v_prefix=True)
