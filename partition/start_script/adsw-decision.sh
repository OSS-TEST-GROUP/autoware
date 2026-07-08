#!/usr/bin/env bash


set -x


args_plan=()
args_plan+=("map_path:=/autoware_map")
args_plan+=("vehicle_model:=sample_vehicle")
args_plan+=("sensor_model:=sample_sensor_kit")

ros2 launch obigo_launch sample_adsw_decision_run.launch.xml ${args_plan[@]}


set +x
