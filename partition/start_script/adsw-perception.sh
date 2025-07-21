#!/usr/bin/env bash


set -x


args_perception=()
args_perception+=("map_path:=/autoware_map")
args_perception+=("vehicle_model:=sample_vehicle")
args_perception+=("sensor_model:=sample_sensor_kit")
args_perception+=("is_launch_autoware:=true")
args_perception+=("launch_file:=adsw_perception.launch.xml")
args_perception+=("is_launch_simulator:=true")
args_perception+=("sim_launch_file:=perception_simulator_component.launch.xml")
args_perception+=("rviz:=true")
args_perception+=("pointcloud_container_name:=pointcloud_container_perception")
args_perception+=("glog_name:=glog_component_perception")

ros2 launch obigo_launch planning_simulator.launch.xml ${args_perception[@]}

set +x