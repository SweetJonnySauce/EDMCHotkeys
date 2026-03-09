# EDMCHotkeys
[![Github All Releases](https://img.shields.io/github/downloads/SweetJonnySauce/EDMCHotkeys/total.svg)](https://github.com/SweetJonnySauce/EDMCHotkeys/releases/latest)
[![GitHub Latest Version](https://img.shields.io/github/v/release/SweetJonnySauce/EDMCHotkeys)](https://github.com/SweetJonnySauce/EDMCHotkeys/releases/latest)
[![Build Status][build-badge]][build-url]
[![VirusTotal](https://img.shields.io/badge/VirusTotal-clean-brightgreen.svg)](https://www.virustotal.com/gui/file-analysis/MzkzYTM1ODM2MDYzMWQwODMwOTI3N2NhZmUwOTE4YWE6MTc3MzAyNzg2Nw==)

[build-badge]: https://github.com/SweetJonnySauce/EDMCHotkeys/actions/workflows/ci.yml/badge.svg?branch=main
[build-url]: https://github.com/SweetJonnySauce/EDMCHotkeys/actions/workflows/ci.yml

Global hotkeys plugin for EDMarketConnector with Windows, Linux X11, and Linux Wayland backends.

## Installation

### Windows
- Download the current release
- Extract the EDMCHokeys folder into your EDMC plugins directory

### Linux X11
- Download the current release
- Extract the EDMCHokeys folder into your EDMC plugins directory
- Note: Release ships with [`python-xlib`](https://github.com/python-xlib/python-xlib) and [`six`](https://github.com/benjaminp/six) pre-installed (not part of the EDMCHotkey virus scan)

### Linux Wayland
The Linux Wayland version integrates with `keyd`. 
- Install [`keyd`](https://github.com/rvaiya/keyd) per the instructions found on the `keyd` Github repo. `keyd` needs to be running on your system in order for the EDMCHotkeys Linux Wayland version to work. Verify the service is active with `systemctl is-active keyd`
- Download the current release
- Extract the EDMCHokeys folder into your EDMC plugins directory
- Follow additional steps found on the EDMCHotkey settings preference pane (EDMC > File > Settings) to set up the integration

## Upgrade
Follow these steps in order to preserve your Hotkey bindings across versions.
1) Shut down EDMC
2) Rename the `EDMCHotkeys` plugin folder to `EDMCHotkeys.disabled`
3) Copy the `EDMCHotkeys` folder into the EDMC Plugins folder
4) Copy your `bindings.json` file from `EDMCHotkeys.disabled` folder to the upgraded `EDMCHotkeys` folder
5) Start EDMC

## Usage
1) Open up EDMC Settings (File > Settings) and navigate to the EDMCHotkeys tab
2) Assign a hotkey to a plugin action
    - **Hotkey:** Keypress the hotkey you want to assign (don't actually type in "LCtrl", etc.)
    - **Plugin:** Select available plugins from the dropdown. Plugins have to register with EDMCHotkeys to show up on this list.
    - **Action:** Select available actions for the chosen plugins from the dropdown. Plugins have to register actions with EDMCHotkeys to show up on this list.
    - **Payload**: Refer to the registered plugin documenation for what to put here (most likely, this will be blank).
    - **Enabled:** Yes, the hotkey will be intercepted. No, the hotkeywill be ignored.
    - **Remove:** Remove the hotkey.
3) For Linux Wayand users, you will need to export Hotkeys configurations to `keyd` whenever they are created, updated, or removed. Follow the instructions found on the EDMCHotkey settings preference pane (EDMC > File > Settings) to export the Hotkeys configurations.

<img width="774" height="154" alt="image" src="https://github.com/user-attachments/assets/96f507f3-d4b8-4d5e-ab9c-50e4788bb434" />

## Usage notes
- Hotkeys need to be globally unique. You will need to make sure the hotkey you assign does not conflict with other app key combos. i.e. Elite Dangerous Options>Controls
- If you don't see a plugin in the dropdown box, that's most likely because they haven't implemented EDMCHotkeys. There's nothing I can do to help with that.
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
