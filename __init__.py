"""Import facade for the EDMCHotkeys plugin root package."""

try:
    from .edmc_hotkeys import PLUGIN_TAG_VERSION, PLUGIN_VERSION
except ImportError:  # pragma: no cover - fallback for direct module import mode
    from edmc_hotkeys import PLUGIN_TAG_VERSION, PLUGIN_VERSION  # type: ignore

try:
    from .load import (
        Action,
        Binding,
        get_action,
        invoke_action,
        invoke_bound_action,
        list_actions,
        list_bindings,
        register_action,
    )
except ImportError:  # pragma: no cover - fallback for direct module import mode
    from load import (  # type: ignore
        Action,
        Binding,
        get_action,
        invoke_action,
        invoke_bound_action,
        list_actions,
        list_bindings,
        register_action,
    )

__version__ = PLUGIN_VERSION

__all__ = [
    "Action",
    "Binding",
    "get_action",
    "invoke_action",
    "invoke_bound_action",
    "list_actions",
    "list_bindings",
    "register_action",
]
