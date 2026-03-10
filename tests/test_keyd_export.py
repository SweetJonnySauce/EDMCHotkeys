from __future__ import annotations

import json
import logging
from pathlib import Path

from edmc_hotkeys.bindings import BindingRecord, BindingsDocument
from edmc_hotkeys.keyd_export import STATE_SCHEMA_VERSION, export_keyd_bindings
from edmc_hotkeys.runtime_config import RuntimeConfig


def _document_with_rows(rows: list[BindingRecord]) -> BindingsDocument:
    return BindingsDocument(
        version=3,
        active_profile="Default",
        profiles={"Default": rows},
    )


def _config() -> RuntimeConfig:
    return RuntimeConfig(
        backend_mode="wayland_keyd",
        keyd_generated_path="keyd/runtime/keyd.generated.conf",
        keyd_state_path="keyd/runtime/export_state.json",
        keyd_socket_path="keyd/runtime/keyd.sock",
        keyd_token_file="keyd/runtime/sender.token",
        keyd_apply_target_path="/etc/keyd/edmchotkeys.conf",
        keyd_command_template=(
            "python3 {plugin_dir}/scripts/keyd_send.py --socket {socket_path} "
            "--binding-id {binding_id} --token-file {token_file}"
        ),
    )


def test_export_keyd_bindings_conflict_is_first_wins(tmp_path: Path, caplog) -> None:
    config = _config()
    document = _document_with_rows(
        [
            BindingRecord(
                id="b1",
                plugin="p",
                modifiers=("ctrl_l",),
                key="a",
                action_id="action.one",
                enabled=True,
            ),
            BindingRecord(
                id="b2",
                plugin="p",
                modifiers=("ctrl_l",),
                key="a",
                action_id="action.two",
                enabled=True,
            ),
        ]
    )
    with caplog.at_level(logging.WARNING):
        summary = export_keyd_bindings(
            document=document,
            plugin_dir=tmp_path,
            config=config,
            logger=logging.getLogger("test.keyd_export"),
        )
    assert summary.exported_bindings == 1
    assert summary.skipped_conflicts == 1
    assert "keyd export conflict (first-wins)" in caplog.text


def test_export_keyd_bindings_logs_invalid_binding_warning(tmp_path: Path, caplog) -> None:
    config = _config()
    document = _document_with_rows(
        [
            BindingRecord(
                id="b1",
                plugin="p",
                modifiers=("ctrl_l",),
                key="notakey",
                action_id="action.invalid",
                enabled=True,
            )
        ]
    )
    with caplog.at_level(logging.WARNING):
        summary = export_keyd_bindings(
            document=document,
            plugin_dir=tmp_path,
            config=config,
            logger=logging.getLogger("test.keyd_export"),
        )
    assert summary.skipped_invalid == 1
    assert summary.exported_bindings == 0
    assert "keyd export skipped invalid binding" in caplog.text
    assert "canonical_hotkey_text returned None" in caplog.text


def test_export_keyd_bindings_skips_rewrite_when_hash_unchanged(tmp_path: Path) -> None:
    config = _config()
    document = _document_with_rows(
        [
            BindingRecord(
                id="b1",
                plugin="p",
                modifiers=("ctrl_l",),
                key="a",
                action_id="action.one",
                enabled=True,
            )
        ]
    )
    logger = logging.getLogger("test.keyd_export")
    first = export_keyd_bindings(document=document, plugin_dir=tmp_path, config=config, logger=logger)
    second = export_keyd_bindings(document=document, plugin_dir=tmp_path, config=config, logger=logger)
    assert first.wrote_generated_file is True
    assert first.reload_required is True
    assert second.wrote_generated_file is False
    assert second.reload_required is False


def test_export_keyd_bindings_rebuilds_state_on_major_schema_mismatch(tmp_path: Path, caplog) -> None:
    config = _config()
    state_path = tmp_path / config.keyd_state_path
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "state_schema_version": "2.0.0",
                "active_profile": "Default",
                "bindings_hash": "old",
            }
        ),
        encoding="utf-8",
    )
    document = _document_with_rows(
        [
            BindingRecord(
                id="b1",
                plugin="p",
                modifiers=("ctrl_l",),
                key="a",
                action_id="action.one",
                enabled=True,
            )
        ]
    )
    with caplog.at_level(logging.WARNING):
        export_keyd_bindings(
            document=document,
            plugin_dir=tmp_path,
            config=config,
            logger=logging.getLogger("test.keyd_export"),
        )
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert payload["state_schema_version"] == STATE_SCHEMA_VERSION
    assert "schema major mismatch" in caplog.text


def test_export_keyd_bindings_uses_compact_fallback_when_command_too_long(tmp_path: Path, caplog) -> None:
    config = _config()
    config = RuntimeConfig(
        backend_mode=config.backend_mode,
        keyd_generated_path=config.keyd_generated_path,
        keyd_state_path=config.keyd_state_path,
        keyd_socket_path=config.keyd_socket_path,
        keyd_token_file=config.keyd_token_file,
        keyd_apply_target_path=config.keyd_apply_target_path,
        keyd_command_template=(
            "python3 {plugin_dir}/scripts/keyd_send.py --socket {socket_path} "
            "--binding-id {binding_id} --token-file {token_file} --sender-id "
            + ("x" * 260)
        ),
    )
    document = _document_with_rows(
        [
            BindingRecord(
                id="binding_12345678",
                plugin="p",
                modifiers=("ctrl_l",),
                key="a",
                action_id="action.one",
                enabled=True,
            )
        ]
    )
    with caplog.at_level(logging.WARNING):
        summary = export_keyd_bindings(
            document=document,
            plugin_dir=tmp_path,
            config=config,
            logger=logging.getLogger("test.keyd_export"),
        )
    rendered = summary.generated_path.read_text(encoding="utf-8")
    assert summary.exported_bindings == 1
    assert "--token-file" not in rendered
    assert "using compact command fallback" in caplog.text


def test_export_keyd_bindings_skips_when_command_exceeds_limit_even_after_fallback(
    tmp_path: Path, caplog
) -> None:
    config = _config()
    deep_plugin_dir = tmp_path / ("a" * 80) / ("b" * 80) / ("c" * 80)
    deep_plugin_dir.mkdir(parents=True, exist_ok=True)
    document = _document_with_rows(
        [
            BindingRecord(
                id="binding_12345678",
                plugin="p",
                modifiers=("ctrl_l",),
                key="a",
                action_id="action.one",
                enabled=True,
            )
        ]
    )
    with caplog.at_level(logging.WARNING):
        summary = export_keyd_bindings(
            document=document,
            plugin_dir=deep_plugin_dir,
            config=config,
            logger=logging.getLogger("test.keyd_export"),
        )
    assert summary.exported_bindings == 0
    assert summary.skipped_invalid == 1
    assert "keyd command length exceeds limit" in caplog.text


def test_export_keyd_bindings_writes_generic_modifiers_as_layer_combo_sections(tmp_path: Path) -> None:
    config = _config()
    document = _document_with_rows(
        [
            BindingRecord(
                id="binding_generic",
                plugin="p",
                modifiers=("ctrl", "shift"),
                key="a",
                action_id="action.one",
                enabled=True,
            )
        ]
    )
    summary = export_keyd_bindings(
        document=document,
        plugin_dir=tmp_path,
        config=config,
        logger=logging.getLogger("test.keyd_export"),
    )
    rendered = summary.generated_path.read_text(encoding="utf-8")
    assert summary.exported_bindings == 1
    assert "[ids]\n*\n\n[main]\n" in rendered
    assert "[control+shift]\n" in rendered
    assert "a = command(" in rendered


def test_export_keyd_bindings_writes_side_specific_modifiers_as_side_layers(tmp_path: Path) -> None:
    config = _config()
    document = _document_with_rows(
        [
            BindingRecord(
                id="binding_side",
                plugin="p",
                modifiers=("ctrl_l", "shift_l"),
                key="x",
                action_id="action.side",
                enabled=True,
            )
        ]
    )
    summary = export_keyd_bindings(
        document=document,
        plugin_dir=tmp_path,
        config=config,
        logger=logging.getLogger("test.keyd_export"),
    )
    rendered = summary.generated_path.read_text(encoding="utf-8")
    assert summary.exported_bindings == 1
    assert "leftcontrol = layer(lctrl)" in rendered
    assert "leftshift = layer(lshift)" in rendered
    assert "[lctrl:C]\n" in rendered
    assert "[lshift:S]\n" in rendered
    assert "[lctrl+lshift]\n" in rendered
    assert "x = command(" in rendered


def test_export_keyd_bindings_warns_when_socket_path_is_under_home(tmp_path: Path, caplog, monkeypatch) -> None:
    config = _config()
    home_socket = Path.home() / ".local" / "share" / "EDMarketConnector" / "plugins" / "EDMCHotkeys" / "keyd.sock"
    config = RuntimeConfig(
        backend_mode=config.backend_mode,
        keyd_generated_path=config.keyd_generated_path,
        keyd_state_path=config.keyd_state_path,
        keyd_socket_path=str(home_socket),
        keyd_token_file=str(home_socket.with_name("sender.token")),
        keyd_apply_target_path=config.keyd_apply_target_path,
        keyd_command_template=config.keyd_command_template,
    )
    document = _document_with_rows(
        [
            BindingRecord(
                id="b1",
                plugin="p",
                modifiers=("ctrl_l",),
                key="a",
                action_id="action.one",
                enabled=True,
            )
        ]
    )
    monkeypatch.setattr("edmc_hotkeys.keyd_export.should_use_systemd", lambda: True)
    with caplog.at_level(logging.WARNING):
        export_keyd_bindings(
            document=document,
            plugin_dir=tmp_path,
            config=config,
            logger=logging.getLogger("test.keyd_export"),
        )
    assert "socket_path is under home" in caplog.text


def test_export_keyd_bindings_warns_when_private_tmp_and_socket_under_tmp(tmp_path: Path, caplog, monkeypatch) -> None:
    config = _config()
    config = RuntimeConfig(
        backend_mode=config.backend_mode,
        keyd_generated_path=config.keyd_generated_path,
        keyd_state_path=config.keyd_state_path,
        keyd_socket_path="/tmp/edmchotkeys/keyd.sock",
        keyd_token_file="/tmp/edmchotkeys/sender.token",
        keyd_apply_target_path=config.keyd_apply_target_path,
        keyd_command_template=config.keyd_command_template,
    )
    document = _document_with_rows(
        [
            BindingRecord(
                id="b1",
                plugin="p",
                modifiers=("ctrl_l",),
                key="a",
                action_id="action.one",
                enabled=True,
            )
        ]
    )
    monkeypatch.setattr("edmc_hotkeys.keyd_export.should_use_systemd", lambda: True)
    monkeypatch.setattr("edmc_hotkeys.keyd_export._keyd_service_uses_private_tmp", lambda: True)
    with caplog.at_level(logging.WARNING):
        export_keyd_bindings(
            document=document,
            plugin_dir=tmp_path,
            config=config,
            logger=logging.getLogger("test.keyd_export"),
        )
    assert "PrivateTmp enabled" in caplog.text
