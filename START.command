#!/bin/bash

cd "$(dirname "$0")"

echo "[*] Starting server..."
python3 server.py &
echo "Server PID: $!"

sleep 5

echo "[*] Starting bot..."
python3 bot.py &
echo "Bot PID: $!"

echo
echo "Running"
echo "Press Ctrl+C to stop"

wait