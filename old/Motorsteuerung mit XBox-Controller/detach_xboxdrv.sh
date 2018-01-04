#!/bin/bash

xboxdrv -d &
sleep 2
pkill -P $$
sleep 3
