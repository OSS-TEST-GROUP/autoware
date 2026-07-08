#!/usr/bin/env bash


set -x


args_perception=()
args_perception+=("map_path:=/autoware_map")
args_perception+=("vehicle_model:=sample_vehicle")
args_perception+=("sensor_model:=sample_sensor_kit")
args_perception+=("rviz:=true")

ros2 launch obigo_launch sample_adsw_perception_run.launch.xml ${args_perception[@]}

set +x
