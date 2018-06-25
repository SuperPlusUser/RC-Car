#!/bin/bash
pkill -f Socket.py # Terminate Socket.py
sleep 8            # give Socket some time to clean up...
pkill -f Socket.py # Terminate Socket.py
sleep 2
sudo shutdown now  # shutdown pi

