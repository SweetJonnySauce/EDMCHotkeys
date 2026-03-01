# EDMCHotkeys - PREVIEW VERSION

Global hotkeys plugin for EDMarketConnector with Windows, Linux X11, and Linux Wayland backends.

## Installation

### Windows
- Download the current release
- Extract the plugin into your EDMC plugins directory

### Linux X11
- Download the current release
- Extract the plugin into your EDMC plugins directory

### Linux Wayland with GNOME
- Download the current release
- Extract the plugin into your EDMC plugins directory
- Follow GNOME bridge setup in:
  - [linux-user-setup.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/linux-user-setup.md)
  - [COMPANION_SETUP.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/COMPANION_SETUP.md)

### Linux Wayland
- NOTE: this has not been tested yet
- Download the current release
- Extract the plugin into your EDMC plugins directory
- Follow setup and verification steps in [linux-user-setup.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/linux-user-setup.md)

## Usage
1) Open up EDMC Settings (File > Settings) and navigate to the EDMCHotkeys tab
2) Assign a hotkey to a plugin action
    - **Hotkey:** Keypress the hotkey you want to assign (don't actually type in "LCtrl", etc.)
    - **Plugin:** Select available plugins from the dropdown. Plugins have to register with EDMCHotkeys to show up on this list.
    - **Action:** Select available actions for the chosen plugins from the dropdown. Plugins have to register actions with EDMCHotkeys to show up on this list.
    - **Payload**: Refer to the registered plugin documenation for what to put here (most likely, this will be blank).
    - **Enabled:** Yes, the hotkey will be intercepted. No, the hotkeywill be ignored.
    - **Remove:** Remove the hotkey.

<img width="774" height="154" alt="image" src="https://github.com/user-attachments/assets/96f507f3-d4b8-4d5e-ab9c-50e4788bb434" />

## Usage notes
- Hotkeys need to be globally unique. You will need to make sure the hotkey you assign does not conflict with other app key combos. i.e. Elite Dangerous Options>Controls
- If you don't see a plugin in the dropdown box, that's most likely because they haven't implemented EDMCHotkeys. There's nothing I can do to help with that.
- The Wayland version does not support side specific modifiers (i.e. LShift / RShift)
- [EDMCModernOverlay](https://github.com/SweetJonnySauce/EDMCModernOverlay) users need release [0.8.0 Alpha #1](https://github.com/SweetJonnySauce/EDMCModernOverlay/releases/tag/0.8.0-alpha-1) or greater.

## Plugin Developer API
Start here if you are integrating another plugin with `EDMCHotkeys`:
- Quick start: [plugin-developer-quickstart.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/plugin-developer-quickstart.md)
- Practical integration guide: [register-action-with-edmchotkeys.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/register-action-with-edmchotkeys.md)
- Canonical API reference: [plugin-developer-api-reference.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/plugin-developer-api-reference.md)
- Troubleshooting: [plugin-developer-api-troubleshooting.md](https://github.com/SweetJonnySauce/EDMCHotkeys/blob/main/docs/plugin-developer-api-troubleshooting.md)

## Support
This plugin is currently under development. So not a lot of support will be given beyond what is needed to get this plugin released into the wild. You can occassionally find me on [EDCD Discord](https://edcd.github.io/) in the `#edmc-plugins` channel.

## Blame
Yes, this plugin was developed using AI. No, it is not low effort.
