"""Bindings export helpers for keyd integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import itertools
import json
import logging
from pathlib import Path
import shlex
import shutil
import subprocess
from typing import Any, Mapping, Optional

from .bindings import BindingsDocument
from .hotkey import canonical_hotkey_text
from .runtime_config import RuntimeConfig

STATE_SCHEMA_VERSION = "1.0.0"
MAX_KEYD_COMMAND_LENGTH = 256

_KEY_NAME_MAP = {
    "enter": "enter",
    "esc": "esc",
    "space": "space",
    "tab": "tab",
}
_MODIFIER_LAYER_MAP = {
    "ctrl": ("control",),
    "ctrl_l": ("lctrl",),
    "ctrl_r": ("rctrl",),
    "alt": ("alt", "altgr"),
    "alt_l": ("lalt",),
    "alt_r": ("ralt",),
    "shift": ("shift",),
    "shift_l": ("lshift",),
    "shift_r": ("rshift",),
    "win": ("meta",),
    "win_l": ("lmeta",),
    "win_r": ("rmeta",),
}
_SIDE_LAYER_DEFS = {
    "lctrl": ("leftcontrol", "C"),
    "rctrl": ("rightcontrol", "C"),
    "lshift": ("leftshift", "S"),
    "rshift": ("rightshift", "S"),
    "lalt": ("leftalt", "A"),
    "ralt": ("rightalt", "G"),
    "lmeta": ("leftmeta", "M"),
    "rmeta": ("rightmeta", "M"),
}
_SIDE_LAYER_BY_MODIFIER = {
    "ctrl_l": "lctrl",
    "ctrl_r": "rctrl",
    "shift_l": "lshift",
    "shift_r": "rshift",
    "alt_l": "lalt",
    "alt_r": "ralt",
    "win_l": "lmeta",
    "win_r": "rmeta",
}
_COMPACT_COMMAND_TEMPLATE = (
    "/usr/bin/python3 /usr/local/bin/edmchotkeys_send.py --socket {socket_path} "
    "--binding-id {binding_id}"
)
_KEYD_HELPER_TARGET = "/usr/local/bin/edmchotkeys_send.py"


@dataclass(frozen=True)
class _KeydSectionTarget:
    section: str
    key: str


@dataclass(frozen=True)
class KeydExportSummary:
    profile: str
    bindings_hash: str
    wrote_generated_file: bool
    reload_required: bool
    generated_path: Path
    state_path: Path
    apply_target_path: str
    systemd_prompt_command: str
    non_systemd_prompt_command: str
    non_systemd_restart_hint: str
    skipped_invalid: int
    skipped_conflicts: int
    exported_bindings: int


def export_keyd_bindings(
    *,
    document: BindingsDocument,
    plugin_dir: Path,
    config: RuntimeConfig,
    logger: logging.Logger,
) -> KeydExportSummary:
    profile = document.active_profile
    records = list(document.profiles.get(profile, []))
    generated_path = _resolve_runtime_path(plugin_dir, config.keyd_generated_path)
    state_path = _resolve_runtime_path(plugin_dir, config.keyd_state_path)
    socket_path = _resolve_runtime_path(plugin_dir, config.keyd_socket_path)
    token_path = _resolve_runtime_path(plugin_dir, config.keyd_token_file)
    if should_use_systemd() and _is_user_home_path(socket_path):
        logger.warning(
            "keyd export socket_path is under home (%s); keyd service sandboxing may block command() delivery. "
            "Prefer /tmp/edmchotkeys/keyd.sock",
            socket_path,
        )
    if should_use_systemd() and _is_tmp_path(socket_path) and _keyd_service_uses_private_tmp():
        logger.warning(
            "keyd export socket_path is under /tmp (%s) while keyd.service has PrivateTmp enabled; "
            "keyd command() helpers may not reach the EDMC socket. Prefer /dev/shm/edmchotkeys/keyd.sock",
            socket_path,
        )

    main_lines: list[str] = []
    section_lines: dict[str, list[str]] = {}
    section_order: list[str] = []
    seen_targets: dict[str, str] = {}
    required_side_layers: set[str] = set()
    skipped_invalid = 0
    skipped_conflicts = 0
    exported_bindings = 0
    compact_fallback_logged = False

    for row in records:
        if not row.enabled:
            continue
        canonical = canonical_hotkey_text(modifiers=row.modifiers, key=row.key)
        if not canonical:
            skipped_invalid += 1
            logger.warning(
                "keyd export skipped invalid binding: profile=%s action=%s chord=%s reason=%s",
                profile,
                row.action_id,
                "<unknown>",
                "canonical_hotkey_text returned None",
            )
            continue
        targets, side_layers = _canonical_to_keyd_targets(canonical)
        if targets is None:
            skipped_invalid += 1
            logger.warning(
                "keyd export skipped invalid binding: profile=%s action=%s chord=%s reason=%s",
                profile,
                row.action_id,
                canonical,
                "unsupported keyd token mapping",
            )
            continue
        required_side_layers.update(side_layers)
        command = _render_command(
            template=config.keyd_command_template,
            plugin_dir=plugin_dir,
            socket_path=socket_path,
            token_file=token_path,
            binding_id=row.id,
        )
        guarded_command, reason, used_compact_fallback = _guard_keyd_command_length(
            command=command,
            binding_id=row.id,
            plugin_dir=plugin_dir,
            socket_path=socket_path,
            token_file=token_path,
        )
        if used_compact_fallback and not compact_fallback_logged:
            logger.warning(
                "keyd export command exceeded %d characters; using compact command fallback",
                MAX_KEYD_COMMAND_LENGTH,
            )
            compact_fallback_logged = True
        if guarded_command is None:
            skipped_invalid += 1
            logger.warning(
                "keyd export skipped invalid binding: profile=%s action=%s chord=%s reason=%s",
                profile,
                row.action_id,
                canonical,
                reason or "keyd command length limit exceeded",
            )
            continue
        for target in targets:
            target_id = _target_id(target)
            conflict_action = seen_targets.get(target_id)
            if conflict_action is not None:
                skipped_conflicts += 1
                logger.warning(
                    "keyd export conflict (first-wins): profile=%s chord=%s kept=%s skipped=%s",
                    profile,
                    _target_display(target),
                    conflict_action,
                    row.action_id,
                )
                continue
            seen_targets[target_id] = row.action_id
            line = f"{target.key} = command({guarded_command})"
            if target.section == "main":
                main_lines.append(line)
            else:
                if target.section not in section_lines:
                    section_lines[target.section] = []
                    section_order.append(target.section)
                section_lines[target.section].append(line)
            exported_bindings += 1

    generated_text = _render_keyd_file(
        main_lines=main_lines,
        section_lines=section_lines,
        section_order=section_order,
        required_side_layers=required_side_layers,
    )
    bindings_hash = hashlib.sha256(generated_text.encode("utf-8")).hexdigest()
    existing_state = _load_state(state_path=state_path, logger=logger)
    changed = existing_state is None or existing_state.get("bindings_hash") != bindings_hash
    if changed:
        generated_path.parent.mkdir(parents=True, exist_ok=True)
        generated_path.write_text(generated_text, encoding="utf-8")

    systemd_prompt = _build_systemd_prompt(
        plugin_dir=plugin_dir,
        generated_path=generated_path,
        apply_target_path=config.keyd_apply_target_path,
    )
    non_systemd_prompt = _build_non_systemd_prompt(
        plugin_dir=plugin_dir,
        generated_path=generated_path,
        apply_target_path=config.keyd_apply_target_path,
    )
    restart_hint = "Restart keyd manually using your init system (for example: sudo service keyd restart)."
    reload_required = changed

    if changed:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_payload = {
            "state_schema_version": STATE_SCHEMA_VERSION,
            "active_profile": profile,
            "bindings_hash": bindings_hash,
            "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "generated_path": config.keyd_generated_path,
            "apply_target_path": config.keyd_apply_target_path,
            "reload_required": True,
            "last_reload_prompt_command": systemd_prompt,
        }
        state_path.write_text(json.dumps(state_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    logger.info(
        "keyd export status: profile=%s exported=%d skipped_invalid=%d skipped_conflicts=%d "
        "bindings_hash=%s changed=%s generated_path=%s state_path=%s",
        profile,
        exported_bindings,
        skipped_invalid,
        skipped_conflicts,
        bindings_hash,
        changed,
        generated_path,
        state_path,
    )
    return KeydExportSummary(
        profile=profile,
        bindings_hash=bindings_hash,
        wrote_generated_file=changed,
        reload_required=reload_required,
        generated_path=generated_path,
        state_path=state_path,
        apply_target_path=config.keyd_apply_target_path,
        systemd_prompt_command=systemd_prompt,
        non_systemd_prompt_command=non_systemd_prompt,
        non_systemd_restart_hint=restart_hint,
        skipped_invalid=skipped_invalid,
        skipped_conflicts=skipped_conflicts,
        exported_bindings=exported_bindings,
    )


def render_keyd_bindings_preview(
    *,
    document: BindingsDocument,
) -> str:
    main_lines: list[str] = []
    section_lines: dict[str, list[str]] = {}
    section_order: list[str] = []
    required_side_layers: set[str] = set()
    for row in document.profiles.get(document.active_profile, []):
        if not row.enabled:
            continue
        canonical = canonical_hotkey_text(modifiers=row.modifiers, key=row.key)
        if not canonical:
            continue
        targets, side_layers = _canonical_to_keyd_targets(canonical)
        if targets is None:
            continue
        required_side_layers.update(side_layers)
        for target in targets:
            line = f"{target.key} = command(<binding {row.id}>)"
            if target.section == "main":
                main_lines.append(line)
            else:
                if target.section not in section_lines:
                    section_lines[target.section] = []
                    section_order.append(target.section)
                section_lines[target.section].append(line)
    return _render_keyd_file(
        main_lines=main_lines,
        section_lines=section_lines,
        section_order=section_order,
        required_side_layers=required_side_layers,
    )


def _resolve_runtime_path(plugin_dir: Path, configured_path: str) -> Path:
    candidate = Path(configured_path)
    if candidate.is_absolute():
        return candidate
    return plugin_dir / candidate


def _build_systemd_prompt(*, plugin_dir: Path, generated_path: Path, apply_target_path: str) -> str:
    helper_source = plugin_dir / "scripts" / "keyd_send.py"
    return (
        f"sudo install -m 0755 {helper_source} {_KEYD_HELPER_TARGET} && "
        f"sudo install -m 0644 {generated_path} {apply_target_path} && "
        "sudo systemctl restart keyd"
    )


def _build_non_systemd_prompt(*, plugin_dir: Path, generated_path: Path, apply_target_path: str) -> str:
    helper_source = plugin_dir / "scripts" / "keyd_send.py"
    return (
        f"sudo install -m 0755 {helper_source} {_KEYD_HELPER_TARGET} && "
        f"sudo install -m 0644 {generated_path} {apply_target_path}"
    )


def _render_command(
    *,
    template: str,
    plugin_dir: Path,
    socket_path: Path,
    token_file: Path,
    binding_id: str,
) -> str:
    escaped = {
        "plugin_dir": shlex.quote(str(plugin_dir)),
        "socket_path": shlex.quote(str(socket_path)),
        "token_file": shlex.quote(str(token_file)),
        "binding_id": shlex.quote(binding_id),
    }
    try:
        return template.format(**escaped)
    except Exception:
        fallback = (
            "/usr/bin/python3 /usr/local/bin/edmchotkeys_send.py --socket {socket_path} "
            "--binding-id {binding_id}"
        )
        return fallback.format(**escaped)


def _guard_keyd_command_length(
    *,
    command: str,
    binding_id: str,
    plugin_dir: Path,
    socket_path: Path,
    token_file: Path,
    ) -> tuple[Optional[str], Optional[str], bool]:
    if len(command) <= MAX_KEYD_COMMAND_LENGTH:
        return command, None, False

    compact_reason = (
        f"keyd command length {len(command)} exceeds max {MAX_KEYD_COMMAND_LENGTH}"
    )
    if _can_use_compact_tokenless_command(socket_path=socket_path, token_file=token_file):
        compact_command = _render_command(
            template=_COMPACT_COMMAND_TEMPLATE,
            plugin_dir=plugin_dir,
            socket_path=socket_path,
            token_file=token_file,
            binding_id=binding_id,
        )
        if len(compact_command) <= MAX_KEYD_COMMAND_LENGTH:
            return compact_command, None, True
        compact_reason = (
            "keyd command length exceeds limit even after compact fallback "
            f"({len(compact_command)}>{MAX_KEYD_COMMAND_LENGTH}); "
            "shorten keyd socket/token paths or command_template"
        )
    else:
        compact_reason = (
            "keyd command length exceeds limit and compact fallback is unavailable "
            "(token_file must be the default sibling of socket_path named sender.token)"
        )
    return None, compact_reason, False


def _can_use_compact_tokenless_command(*, socket_path: Path, token_file: Path) -> bool:
    return token_file == socket_path.with_name("sender.token")


def _canonical_to_keyd_targets(canonical_hotkey: str) -> tuple[Optional[list[_KeydSectionTarget]], set[str]]:
    parts = [token.strip().lower() for token in canonical_hotkey.split("+") if token.strip()]
    if not parts:
        return None, set()
    if len(parts) == 1:
        key_name = _normalize_key_name(parts[0])
        if key_name is None:
            return None, set()
        return [_KeydSectionTarget(section="main", key=key_name)], set()
    *modifiers, key = parts
    mapped_modifiers: list[tuple[str, ...]] = []
    required_side_layers: set[str] = set()
    for modifier in modifiers:
        mapped = _MODIFIER_LAYER_MAP.get(modifier)
        if mapped is None:
            return None, set()
        mapped_modifiers.append(mapped)
        side_layer = _SIDE_LAYER_BY_MODIFIER.get(modifier)
        if side_layer is not None:
            required_side_layers.add(side_layer)
    key_name = _normalize_key_name(key)
    if key_name is None:
        return None, set()
    targets: list[_KeydSectionTarget] = []
    seen: set[str] = set()
    for combo in itertools.product(*mapped_modifiers):
        section = "+".join(combo)
        target = _KeydSectionTarget(section=section, key=key_name)
        key_id = _target_id(target)
        if key_id in seen:
            continue
        seen.add(key_id)
        targets.append(target)
    return targets, required_side_layers


def _normalize_key_name(raw_key: str) -> Optional[str]:
    token = raw_key.strip().lower()
    if not token:
        return None
    if len(token) == 1 and token.isalnum():
        return token
    if token.startswith("f") and token[1:].isdigit():
        return token
    return _KEY_NAME_MAP.get(token)


def _render_keyd_file(
    *,
    main_lines: list[str],
    section_lines: Mapping[str, list[str]],
    section_order: list[str],
    required_side_layers: set[str],
) -> str:
    lines = [
        "# Generated by EDMCHotkeys. Do not edit directly.",
        "[ids]",
        "*",
        "",
        "[main]",
    ]
    for side_layer in _ordered_side_layers(required_side_layers):
        source_key, _modifier_tag = _SIDE_LAYER_DEFS[side_layer]
        lines.append(f"{source_key} = layer({side_layer})")
    lines.extend(main_lines)

    remaining_sections = dict(section_lines)
    for side_layer in _ordered_side_layers(required_side_layers):
        source_key, modifier_tag = _SIDE_LAYER_DEFS[side_layer]
        del source_key
        lines.append("")
        lines.append(f"[{side_layer}:{modifier_tag}]")
        for binding_line in remaining_sections.pop(side_layer, []):
            lines.append(binding_line)

    for section in section_order:
        bindings = remaining_sections.pop(section, None)
        if bindings is None:
            continue
        lines.append("")
        lines.append(f"[{section}]")
        lines.extend(bindings)

    for section in sorted(remaining_sections):
        lines.append("")
        lines.append(f"[{section}]")
        lines.extend(remaining_sections[section])

    return "\n".join(lines) + "\n"


def _ordered_side_layers(side_layers: set[str]) -> list[str]:
    ordered = [name for name in _SIDE_LAYER_DEFS if name in side_layers]
    return ordered


def _target_id(target: _KeydSectionTarget) -> str:
    return f"{target.section}:{target.key}"


def _target_display(target: _KeydSectionTarget) -> str:
    if target.section == "main":
        return target.key
    return f"{target.section}+{target.key}"


def _load_state(*, state_path: Path, logger: logging.Logger) -> Optional[Mapping[str, Any]]:
    if not state_path.exists():
        return None
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("keyd export state unreadable; rebuilding: %s", state_path)
        return None
    if not isinstance(payload, dict):
        logger.warning("keyd export state invalid; rebuilding: %s", state_path)
        return None
    schema_version = str(payload.get("state_schema_version", "")).strip()
    if not schema_version:
        return None
    if _major(schema_version) != _major(STATE_SCHEMA_VERSION):
        logger.warning(
            "keyd export state schema major mismatch (%s -> %s); rebuilding from bindings",
            schema_version,
            STATE_SCHEMA_VERSION,
        )
        return None
    return payload


def _major(version: str) -> int:
    try:
        return int(version.split(".", 1)[0])
    except Exception:
        return -1


def _is_user_home_path(path: Path) -> bool:
    candidate = path.resolve(strict=False)
    home = Path.home().resolve(strict=False)
    try:
        return candidate == home or home in candidate.parents
    except Exception:
        return str(candidate).startswith("/home/")


def _is_tmp_path(path: Path) -> bool:
    candidate = path.resolve(strict=False)
    try:
        return candidate == Path("/tmp") or Path("/tmp") in candidate.parents
    except Exception:
        text = str(candidate)
        return text == "/tmp" or text.startswith("/tmp/")


def _keyd_service_uses_private_tmp() -> bool:
    try:
        result = subprocess.run(
            ["systemctl", "show", "keyd", "--property=PrivateTmp", "--value"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2.0,
        )
    except Exception:
        return False
    if result.returncode != 0:
        return False
    value = (result.stdout or "").strip().lower()
    return value in {"1", "true", "yes"}


def should_use_systemd() -> bool:
    return shutil.which("systemctl") is not None
