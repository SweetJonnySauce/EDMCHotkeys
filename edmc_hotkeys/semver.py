"""Semantic Versioning helpers used across runtime and release tooling."""

from __future__ import annotations

from dataclasses import dataclass
import re


class SemVerError(ValueError):
    """Raised when a semantic version string is invalid."""


_SEMVER_PATTERN = re.compile(
    r"^(?P<prefix>v)?"
    r"(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()
    build: tuple[str, ...] = ()

    @property
    def is_prerelease(self) -> bool:
        return bool(self.prerelease)

    @property
    def core(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def to_string(self, *, v_prefix: bool = False, include_build: bool = True) -> str:
        value = self.core
        if self.prerelease:
            value += "-" + ".".join(self.prerelease)
        if include_build and self.build:
            value += "+" + ".".join(self.build)
        if v_prefix:
            value = "v" + value
        return value


def parse_semver(
    value: str,
    *,
    allow_v_prefix: bool = False,
    require_v_prefix: bool = False,
) -> SemVer:
    normalized = value.strip()
    if not normalized:
        raise SemVerError("version string is empty")
    match = _SEMVER_PATTERN.fullmatch(normalized)
    if not match:
        raise SemVerError(f"invalid semantic version: {value}")

    has_v_prefix = bool(match.group("prefix"))
    if require_v_prefix and not has_v_prefix:
        raise SemVerError(f"version must include 'v' prefix: {value}")
    if has_v_prefix and not allow_v_prefix:
        raise SemVerError(f"'v' prefix is not allowed here: {value}")

    prerelease = tuple(filter(None, (match.group("prerelease") or "").split(".")))
    build = tuple(filter(None, (match.group("build") or "").split(".")))

    _validate_prerelease_identifiers(prerelease, value)

    return SemVer(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
        prerelease=prerelease,
        build=build,
    )


def is_valid_semver(
    value: str,
    *,
    allow_v_prefix: bool = False,
    require_v_prefix: bool = False,
) -> bool:
    try:
        parse_semver(value, allow_v_prefix=allow_v_prefix, require_v_prefix=require_v_prefix)
    except SemVerError:
        return False
    return True


def strip_v_prefix(value: str) -> str:
    parsed = parse_semver(value, allow_v_prefix=True)
    return parsed.to_string(v_prefix=False)


def add_v_prefix(value: str) -> str:
    parsed = parse_semver(value, allow_v_prefix=False)
    return parsed.to_string(v_prefix=True)


def _validate_prerelease_identifiers(identifiers: tuple[str, ...], original_value: str) -> None:
    for identifier in identifiers:
        if not identifier:
            raise SemVerError(f"invalid prerelease identifier in version: {original_value}")
        if identifier.isdigit() and len(identifier) > 1 and identifier.startswith("0"):
            raise SemVerError(f"numeric prerelease identifiers must not contain leading zeroes: {original_value}")
