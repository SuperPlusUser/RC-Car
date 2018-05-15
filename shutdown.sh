#!/bin/bash
pkill -f Socket.py # Terminate Socket.py
sleep 10           # give Socket some time to clean up...
sudo shutdown now  # shutdown pi

