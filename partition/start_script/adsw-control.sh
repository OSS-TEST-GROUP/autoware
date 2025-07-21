#!/usr/bin/env bash


set -x


args_control=()
args_control+=("map_path:=/autoware_map")
args_control+=("vehicle_model:=sample_vehicle")
args_control+=("sensor_model:=sample_sensor_kit")
args_control+=("is_launch_autoware:=true")
args_control+=("launch_file:=adsw_control.launch.xml")
args_control+=("is_launch_simulator:=true")
args_control+=("sim_launch_file:=obigo_simulator_component.launch.xml")
args_control+=("pointcloud_container_name:=pointcloud_container_control")
args_control+=("glog_name:=glog_component_control")

ros2 launch obigo_launch planning_simulator.launch.xml ${args_control[@]}

set +x