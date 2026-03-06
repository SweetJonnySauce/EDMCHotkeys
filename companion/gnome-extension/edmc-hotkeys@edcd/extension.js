import Gio from "gi://Gio";
import GLib from "gi://GLib";
import Meta from "gi://Meta";
import Shell from "gi://Shell";
import * as Main from "resource:///org/gnome/shell/ui/main.js";
import {Extension} from "resource:///org/gnome/shell/extensions/extension.js";

import {HelperBridge} from "./helper_bridge.js";

const CONFIG_DIR = "edmc-hotkeys";
const CONFIG_BASENAME = "companion-bindings.json";
const DECODER = new TextDecoder();

function _defaultConfigPath() {
    const envPath = GLib.getenv("EDMC_HOTKEYS_COMPANION_BINDINGS");
    if (envPath && envPath.trim()) {
        return envPath.trim();
    }
    const home = GLib.get_home_dir();
    return GLib.build_filenamev([home, ".config", CONFIG_DIR, CONFIG_BASENAME]);
}

class BindingRegistry {
    constructor(helperBridge) {
        this._helperBridge = helperBridge;
        this._acceleratorHandlers = new Map();
        this._signalId = 0;
    }

    start() {
        if (this._signalId !== 0) {
            return;
        }
        this._signalId = global.display.connect(
            "accelerator-activated",
            (_display, action) => this._onAccelerator(action),
        );
    }

    stop() {
        if (this._signalId !== 0) {
            global.display.disconnect(this._signalId);
            this._signalId = 0;
        }
        this.clear();
    }

    clear() {
        for (const [action, entry] of this._acceleratorHandlers.entries()) {
            try {
                global.display.ungrab_accelerator(action);
            } catch (err) {
                log(`[EDMCHotkeys-Companion] failed to ungrab '${entry.bindingId}': ${err}`);
            }
            Main.wm.allowKeybinding(entry.externalName, Shell.ActionMode.NONE);
        }
        this._acceleratorHandlers.clear();
    }

    replaceBindings(bindings) {
        this.clear();
        for (const binding of bindings) {
            this._register(binding);
        }
    }

    _register(binding) {
        const bindingId = String(binding.id || "").trim();
        const accelerator = String(binding.accelerator || "").trim();
        if (!bindingId || !accelerator || binding.enabled === false) {
            return;
        }

        let action = Meta.KeyBindingAction.NONE;
        try {
            action = global.display.grab_accelerator(accelerator, Meta.KeyBindingFlags.NONE);
        } catch (err) {
            log(`[EDMCHotkeys-Companion] failed to grab accelerator '${accelerator}': ${err}`);
            return;
        }
        if (action === Meta.KeyBindingAction.NONE) {
            log(`[EDMCHotkeys-Companion] accelerator unavailable '${accelerator}' for '${bindingId}'`);
            return;
        }
        const externalName = Meta.external_binding_name_for_action(action);
        Main.wm.allowKeybinding(externalName, Shell.ActionMode.ALL);
        this._acceleratorHandlers.set(action, {bindingId, externalName});
    }

    _onAccelerator(action) {
        const entry = this._acceleratorHandlers.get(action);
        if (!entry) {
            return;
        }
        this._helperBridge.sendActivate(entry.bindingId);
    }
}

function _readBindingsConfig(path) {
    const file = Gio.File.new_for_path(path);
    let bytes;
    try {
        const loaded = file.load_contents(null);
        bytes = loaded[1];
    } catch (err) {
        log(`[EDMCHotkeys-Companion] failed to load bindings config '${path}': ${err}`);
        return [];
    }

    let parsed;
    try {
        parsed = JSON.parse(DECODER.decode(bytes));
    } catch (err) {
        log(`[EDMCHotkeys-Companion] invalid JSON in bindings config '${path}': ${err}`);
        return [];
    }
    if (!parsed || !Array.isArray(parsed.bindings)) {
        log(`[EDMCHotkeys-Companion] bindings config missing 'bindings' array: '${path}'`);
        return [];
    }
    return parsed.bindings;
}

export default class EdmcHotkeysExtension extends Extension {
    constructor(metadata) {
        super(metadata);
        this._registry = null;
        this._configPath = _defaultConfigPath();
    }

    enable() {
        const helper = new HelperBridge({extensionPath: this.path});
        this._registry = new BindingRegistry(helper);
        this._registry.start();
        const bindings = _readBindingsConfig(this._configPath);
        this._registry.replaceBindings(bindings);
        log(`[EDMCHotkeys-Companion] enabled with ${bindings.length} configured binding(s)`);
    }

    disable() {
        if (!this._registry) {
            return;
        }
        this._registry.stop();
        this._registry = null;
        log("[EDMCHotkeys-Companion] disabled");
    }
}
