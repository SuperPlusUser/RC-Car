#!/bin/bash
pkill -f Socket.py # Terminate Socket.py
sleep 5            # give Socket some time to clean up...
pkill -f Socket.py # Terminate Socket.py
sleep 1
sudo shutdown now  # shutdown pi

