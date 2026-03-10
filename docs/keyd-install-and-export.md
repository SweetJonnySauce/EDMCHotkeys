# EDMCHotkeys + keyd Quick Setup

## 1) Install keyd (required for `wayland_keyd`)

### Option A: distro package (if available)
```bash
sudo apt update
sudo apt install -y keyd
sudo systemctl enable --now keyd
systemctl is-active keyd
```

### Option B: build from source
```bash
git clone https://github.com/rvaiya/keyd.git /tmp/keyd
cd /tmp/keyd
make
sudo make install
sudo systemctl enable --now keyd
systemctl is-active keyd
```

Expected output from `systemctl is-active keyd` is `active`.

## 2) Install EDMCHotkeys and apply keyd integration

Put the plugin in your EDMC plugins directory, then run:

```bash
cd ~/.local/share/EDMarketConnector/plugins/EDMCHotkeys
./scripts/install_keyd_integration.sh --install --apply
./scripts/verify_keyd_integration.sh
```

This does all of the following:
- Exports bindings to `keyd/runtime/keyd.generated.conf`
- Installs helper script to `/usr/local/bin/edmchotkeys_send.py`
- Installs keyd config to `/etc/keyd/edmchotkeys.conf`
- Restarts keyd

## 3) Re-export after changing hotkeys

After you change bindings in EDMCHotkeys preferences, re-run:

```bash
cd ~/.local/share/EDMarketConnector/plugins/EDMCHotkeys
./scripts/install_keyd_integration.sh --apply
```

Use `--install` only when you need to (re)install the helper script:

```bash
cd ~/.local/share/EDMarketConnector/plugins/EDMCHotkeys
./scripts/install_keyd_integration.sh --install
```

Optional preview (no files written):

```bash
python3 ./scripts/export_keyd_bindings.py --plugin-dir . --bindings ./bindings.json --dry-run
```
