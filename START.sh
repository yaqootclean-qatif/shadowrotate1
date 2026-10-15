#!/bin/bash

cd "$(dirname "$0")"

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 not found"
    echo "Install: sudo apt install python3 python3-pip"
    exit 1
fi

echo "[OK] Python found"
echo

echo "[*] Starting server..."
nohup python3 server.py > server.log 2>&1 &
echo "Server PID: $!"

sleep 5

echo "[*] Starting bot..."
nohup python3 bot.py > bot.log 2>&1 &
echo "Bot PID: $!"

echo
echo "Both running"
echo "Logs: server.log, bot.log"