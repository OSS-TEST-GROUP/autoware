#!/usr/bin/env bash


set -x


args_plan=()
args_plan+=("map_path:=/autoware_map")
args_plan+=("vehicle_model:=sample_vehicle")
args_plan+=("sensor_model:=sample_sensor_kit")
args_plan+=("is_launch_autoware:=true")
args_plan+=("launch_file:=adsw_decision.launch.xml")
args_plan+=("pointcloud_container_name:=pointcloud_container_decision")
args_plan+=("glog_name:=glog_component_decision")


ros2 launch obigo_launch planning_simulator.launch.xml ${args_plan[@]}


set +x