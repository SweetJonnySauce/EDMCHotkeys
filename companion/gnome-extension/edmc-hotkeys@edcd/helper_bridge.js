import Gio from "gi://Gio";
import GLib from "gi://GLib";

export class HelperBridge {
    constructor(params = {}) {
        const extensionPath = String(params.extensionPath || "").trim();
        const runtimeDir = GLib.getenv("XDG_RUNTIME_DIR") || "/tmp";
        this._helperPath = params.helperPath || GLib.build_filenamev([
            extensionPath,
            "helper",
            "gnome_bridge_companion_send.py",
        ]);
        this._socketPath = params.socketPath || GLib.build_filenamev([
            runtimeDir,
            "edmc_hotkeys",
            "bridge.sock",
        ]);
        this._tokenFilePath = params.tokenFilePath || GLib.build_filenamev([
            runtimeDir,
            "edmc_hotkeys",
            "sender.token",
        ]);
        this._senderId = params.senderId || "gnome-bridge-extension";
        this._loggerPrefix = params.loggerPrefix || "[EDMC-Hotkeys-Companion]";
    }

    sendActivate(bindingId) {
        if (!bindingId || !bindingId.trim()) {
            log(`${this._loggerPrefix} ignoring empty binding id`);
            return;
        }

        const argv = [
            "python3",
            this._helperPath,
            "--socket",
            this._socketPath,
            "--token-file",
            this._tokenFilePath,
            "--sender-id",
            this._senderId,
            "--binding-id",
            bindingId,
        ];
        try {
            const proc = Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE);
            proc.wait_check_async(null, (_proc, result) => {
                try {
                    _proc.wait_check_finish(result);
                } catch (err) {
                    log(`${this._loggerPrefix} helper send failed for '${bindingId}': ${err}`);
                }
            });
        } catch (err) {
            log(`${this._loggerPrefix} failed to start helper process: ${err}`);
        }
    }
};
