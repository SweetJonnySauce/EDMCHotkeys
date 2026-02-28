# EDMCHotkeys

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
- Install the GNOME bridge (instructions TBD)

### Linux Wayland
- NOTE: this has not been tested yet
- Download the current release
- In theory... Extract the plugin into your EDMC plugins directory

## Usage
1) Open up EDMC Settings (File > Settings) and navigate to the EDMCHotkeys tab
2) Assign a hotkey to a plugin action
    - **Hotkey:** Keypress the hotkey you want to assign (don't actually type in "LCtrl", etc.
    - **Plugin:** Select available plugins from the dropdown. Plugins have to register with EDMCHotkeys to show up on this list.
    - **Action:** Select available actions for the chosen plugins from the dropdown. Plugins have to register actions with EDMCHotkeys to show up on this list.
    - **Payload**: Refer to the registered plugin documenation for what to put here (most likely, this will be blank).
    - **Enabled:** Yes, the hotkey will be intercepted. No, the hotkeywill be ignored.
    - **Remove:** Remove the hotkey.

<img width="774" height="154" alt="image" src="https://github.com/user-attachments/assets/96f507f3-d4b8-4d5e-ab9c-50e4788bb434" />

## Usage notes
- Hotkeys need to be globally unique. You will need to make sure the hotkey you assign does not conflict with other app key combos. i.e. Elite Dangerous Options>Controls
- If you don't see a plugin in the dropdown box, that's most likely because they haven't implemented EDMCHotkeys. There's nothing I can do to help with that.

## Support
This plugin is currently under development. So not a lot of support will be given. However, you can occassionally find me on [EDCD Discord](https://edcd.github.io/) in the `#edmc-plugins` channel.

## Blame
Yes, this plugin was developed using AI. No, it is not low effort.
