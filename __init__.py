"""Import facade for the EDMCHotkeys plugin root package."""

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
