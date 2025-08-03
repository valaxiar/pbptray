#!/bin/bash

set -e

WORKDIR="$(pwd)"
DEST_DIR="$HOME/.local/share/pbptray"
SYSTEMD_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="pbptray.service"

echo "installing pbptray"

mkdir -p "$DEST_DIR"
mkdir -p "$SYSTEMD_DIR"

echo "copying files from $WORKDIR to $DEST_DIR"
cp "$WORKDIR"/pbptray.py "$DEST_DIR"
cp -r "$WORKDIR"/images "$DEST_DIR"

read -rp "enter phone's Bluetooth address (e.g. AA:BB:CC:DD:EE:FF): " BT_ADDR
echo "$BT_ADDR" > "$DEST_DIR/bt_addr"
echo "BT address saved to $DEST_DIR/bt_addr"

cat > "$SYSTEMD_DIR/$SERVICE_FILE" <<EOF
[Unit]
Description=pbptray
After=graphical-session.target

[Service]
ExecStart=/usr/bin/python3 $DEST_DIR/pbptray.py
Restart=on-failure

[Install]
WantedBy=default.target
EOF

echo "created systemd user service at $SYSTEMD_DIR/$SERVICE_FILE"

systemctl --user daemon-reexec
systemctl --user enable --now "$SERVICE_FILE"

echo "pbptray installed and service started"
