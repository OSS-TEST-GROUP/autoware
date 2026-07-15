#!/usr/bin/env bash


set -x


args_control=()
args_control+=("map_path:=/autoware_map")
args_control+=("vehicle_model:=sample_vehicle")
args_control+=("sensor_model:=sample_sensor_kit")

ros2 launch obigo_launch sample_adsw_control_run.launch.xml ${args_control[@]}

set +x
