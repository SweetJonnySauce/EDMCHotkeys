"""Bindings file persistence helpers."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .bindings import BindingsDocument, default_document, document_from_dict, document_to_dict


class BindingsStore:
    """Reads and writes bindings.json documents."""

    def __init__(self, file_path: Path, *, logger: logging.Logger | None = None) -> None:
        self._file_path = file_path
        self._logger = logger or logging.getLogger("EDMCHotkeys")

    @property
    def file_path(self) -> Path:
        return self._file_path

    def load_or_create(self) -> BindingsDocument:
        if not self._file_path.exists():
            document = default_document()
            self.save(document)
            return document

        try:
            raw = json.loads(self._file_path.read_text(encoding="utf-8"))
        except Exception:
            self._logger.exception("Failed reading bindings file '%s'", self._file_path)
            return default_document()

        try:
            if not isinstance(raw, dict):
                raise ValueError("Root JSON object must be a dict")
            return document_from_dict(raw)
        except Exception:
            self._logger.exception("Bindings file '%s' is invalid; using defaults", self._file_path)
            return default_document()

    def save(self, document: BindingsDocument) -> None:
        serialized = json.dumps(document_to_dict(document), indent=2, sort_keys=False)
        self._file_path.write_text(serialized + "\n", encoding="utf-8")

