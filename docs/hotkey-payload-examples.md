# Hotkey Payload Examples

Some hotkey actions allow for additional parameters to be passed in via a json "payload". This allows for reuse of actions and allows Plugin developers to maintain minimal code.

What needs to be passed in via the "payload" field for the plugin is defined by the plugin itself, not EDMCHotkeys. You will need to refer to the Plugin's documentation for their specifications.

However, to give you an example, EDMCHotkeys works with EDMCOverlay and you can turn specific overlays on and off by passing in the name of the plugin group(s).

See the EDMCModernOverlay instructions here: https://github.com/SweetJonnySauce/EDMCModernOverlay/wiki/Overlay-Actions
