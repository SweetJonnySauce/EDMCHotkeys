"""Runtime config loading for EDMCHotkeys plugin-local INI files."""

from __future__ import annotations

import configparser
from dataclasses import dataclass
import logging
import os
from pathlib import Path
from typing import Callable, Mapping, Optional


BACKEND_MODE_CONFIG_KEY = "edmc_hotkeys_backend_mode"
DEFAULT_CONFIG_PATH = "config.defaults.ini"
USER_CONFIG_PATH = "config.ini"

_DEFAULT_KEYD_COMMAND_TEMPLATE = (
    "/usr/bin/python3 /usr/local/bin/edmchotkeys_send.py --socket {socket_path} "
    "--binding-id {binding_id}"
)


@dataclass(frozen=True)
class RuntimeConfig:
    """Resolved runtime settings with source-tracked precedence."""

    backend_mode: str = "auto"
    keyd_generated_path: str = "keyd/runtime/keyd.generated.conf"
    keyd_state_path: str = "keyd/runtime/export_state.json"
    keyd_socket_path: str = "/dev/shm/edmchotkeys/keyd.sock"
    keyd_token_file: str = "/dev/shm/edmchotkeys/sender.token"
    keyd_apply_target_path: str = "/etc/keyd/edmchotkeys.conf"
    keyd_command_template: str = _DEFAULT_KEYD_COMMAND_TEMPLATE


def ensure_user_config(plugin_dir: Path, *, logger: Optional[logging.Logger] = None) -> None:
    """Create config.ini from config.defaults.ini when missing."""
    log = logger or logging.getLogger("EDMCHotkeys")
    user_path = plugin_dir / USER_CONFIG_PATH
    if user_path.exists():
        return
    defaults_path = plugin_dir / DEFAULT_CONFIG_PATH
    if defaults_path.exists():
        user_path.write_text(defaults_path.read_text(encoding="utf-8"), encoding="utf-8")
        log.info("Created %s from %s", user_path, defaults_path)
        return
    user_path.write_text(_fallback_user_config_text(), encoding="utf-8")
    log.info("Created %s from built-in defaults", user_path)


def load_runtime_config(
    *,
    plugin_dir: Path,
    environ: Optional[Mapping[str, str]] = None,
    logger: Optional[logging.Logger] = None,
    edmc_get_str: Optional[Callable[[str], str]] = None,
) -> tuple[RuntimeConfig, dict[str, str]]:
    """Resolve runtime config using precedence rules.

    Precedence:
      env > config.ini > EDMC config > config.defaults.ini > code defaults
    """
    log = logger or logging.getLogger("EDMCHotkeys")
    env = dict(os.environ if environ is None else environ)
    ensure_user_config(plugin_dir, logger=log)

    defaults_ini = _load_ini(plugin_dir / DEFAULT_CONFIG_PATH)
    user_ini = _load_ini(plugin_dir / USER_CONFIG_PATH)
    sources: dict[str, str] = {}

    values = RuntimeConfig()

    values = values.__class__(
        backend_mode=_resolve_value(
            key="backend_mode",
            env=env,
            env_key="EDMC_HOTKEYS_BACKEND_MODE",
            user_ini=user_ini,
            user_section="backend",
            user_option="mode",
            edmc_get_str=edmc_get_str,
            edmc_key=BACKEND_MODE_CONFIG_KEY,
            defaults_ini=defaults_ini,
            defaults_section="backend",
            defaults_option="mode",
            fallback=values.backend_mode,
            sources=sources,
        ),
        keyd_generated_path=_resolve_value(
            key="keyd_generated_path",
            env=env,
            env_key="EDMC_HOTKEYS_KEYD_GENERATED_PATH",
            user_ini=user_ini,
            user_section="keyd",
            user_option="generated_path",
            edmc_get_str=edmc_get_str,
            edmc_key="edmc_hotkeys_keyd_generated_path",
            defaults_ini=defaults_ini,
            defaults_section="keyd",
            defaults_option="generated_path",
            fallback=values.keyd_generated_path,
            sources=sources,
        ),
        keyd_state_path=_resolve_value(
            key="keyd_state_path",
            env=env,
            env_key="EDMC_HOTKEYS_KEYD_STATE_PATH",
            user_ini=user_ini,
            user_section="keyd",
            user_option="state_path",
            edmc_get_str=edmc_get_str,
            edmc_key="edmc_hotkeys_keyd_state_path",
            defaults_ini=defaults_ini,
            defaults_section="keyd",
            defaults_option="state_path",
            fallback=values.keyd_state_path,
            sources=sources,
        ),
        keyd_socket_path=_resolve_value(
            key="keyd_socket_path",
            env=env,
            env_key="EDMC_HOTKEYS_KEYD_SOCKET_PATH",
            user_ini=user_ini,
            user_section="keyd",
            user_option="socket_path",
            edmc_get_str=edmc_get_str,
            edmc_key="edmc_hotkeys_keyd_socket_path",
            defaults_ini=defaults_ini,
            defaults_section="keyd",
            defaults_option="socket_path",
            fallback=values.keyd_socket_path,
            sources=sources,
        ),
        keyd_token_file=_resolve_value(
            key="keyd_token_file",
            env=env,
            env_key="EDMC_HOTKEYS_KEYD_TOKEN_FILE",
            user_ini=user_ini,
            user_section="keyd",
            user_option="token_file",
            edmc_get_str=edmc_get_str,
            edmc_key="edmc_hotkeys_keyd_token_file",
            defaults_ini=defaults_ini,
            defaults_section="keyd",
            defaults_option="token_file",
            fallback=values.keyd_token_file,
            sources=sources,
        ),
        keyd_apply_target_path=_resolve_value(
            key="keyd_apply_target_path",
            env=env,
            env_key="EDMC_HOTKEYS_KEYD_APPLY_TARGET_PATH",
            user_ini=user_ini,
            user_section="keyd",
            user_option="apply_target_path",
            edmc_get_str=edmc_get_str,
            edmc_key="edmc_hotkeys_keyd_apply_target_path",
            defaults_ini=defaults_ini,
            defaults_section="keyd",
            defaults_option="apply_target_path",
            fallback=values.keyd_apply_target_path,
            sources=sources,
        ),
        keyd_command_template=_resolve_value(
            key="keyd_command_template",
            env=env,
            env_key="EDMC_HOTKEYS_KEYD_COMMAND_TEMPLATE",
            user_ini=user_ini,
            user_section="keyd",
            user_option="command_template",
            edmc_get_str=edmc_get_str,
            edmc_key="edmc_hotkeys_keyd_command_template",
            defaults_ini=defaults_ini,
            defaults_section="keyd",
            defaults_option="command_template",
            fallback=values.keyd_command_template,
            sources=sources,
        ),
    )
    return values, sources


def _resolve_value(
    *,
    key: str,
    env: Mapping[str, str],
    env_key: str,
    user_ini: configparser.ConfigParser,
    user_section: str,
    user_option: str,
    edmc_get_str: Optional[Callable[[str], str]],
    edmc_key: str,
    defaults_ini: configparser.ConfigParser,
    defaults_section: str,
    defaults_option: str,
    fallback: str,
    sources: dict[str, str],
) -> str:
    env_value = env.get(env_key, "").strip()
    if env_value:
        sources[key] = "env"
        return env_value

    user_value = _ini_get(user_ini, user_section, user_option)
    if user_value:
        sources[key] = USER_CONFIG_PATH
        return user_value

    edmc_value = _read_edmc_value(edmc_get_str, edmc_key)
    if edmc_value:
        sources[key] = "edmc_config"
        return edmc_value

    defaults_value = _ini_get(defaults_ini, defaults_section, defaults_option)
    if defaults_value:
        sources[key] = DEFAULT_CONFIG_PATH
        return defaults_value

    sources[key] = "code_default"
    return fallback


def _ini_get(parser: configparser.ConfigParser, section: str, option: str) -> str:
    try:
        value = parser.get(section, option, fallback="").strip()
    except Exception:
        return ""
    return value


def _read_edmc_value(getter: Optional[Callable[[str], str]], key: str) -> str:
    if getter is None:
        return ""
    try:
        return str(getter(key) or "").strip()
    except TypeError:
        try:
            # EDMC version differences may expose default parameter in get_str.
            return str(getter(key, default="") or "").strip()  # type: ignore[misc]
        except Exception:
            return ""
    except Exception:
        return ""


def _load_ini(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    if not path.exists():
        return parser
    try:
        parser.read(path, encoding="utf-8")
    except Exception:
        return configparser.ConfigParser()
    return parser


def _fallback_user_config_text() -> str:
    return (
        "[backend]\n"
        "mode = auto\n"
        "\n"
        "[keyd]\n"
        "generated_path = keyd/runtime/keyd.generated.conf\n"
        "state_path = keyd/runtime/export_state.json\n"
        "socket_path = /dev/shm/edmchotkeys/keyd.sock\n"
        "token_file = /dev/shm/edmchotkeys/sender.token\n"
        "apply_target_path = /etc/keyd/edmchotkeys.conf\n"
        "command_template = "
        "/usr/bin/python3 /usr/local/bin/edmchotkeys_send.py --socket {socket_path} "
        "--binding-id {binding_id}\n"
    )
