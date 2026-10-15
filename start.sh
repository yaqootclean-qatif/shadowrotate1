#!/bin/bash

echo "================================"
echo "  ShadowRotate - Railway"
echo "================================"

echo "[*] Starting server..."
python server.py &
echo "Server PID: $!"

sleep 5

echo "[*] Starting bot..."
python bot.py &
echo "Bot PID: $!"

echo "Both running"
echo "Waiting for bot..."

wait