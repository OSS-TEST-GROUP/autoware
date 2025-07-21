ARG BASE_IMAGE
ARG AUTOWARE_BASE_IMAGE
ARG AUTOWARE_BASE_CUDA_IMAGE

# hadolint ignore=DL3006
FROM $BASE_IMAGE AS rosdep-depend
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO

COPY setup-dev-env.sh ansible-galaxy-requirements.yaml amd64.env arm64.env /autoware/
COPY ansible/ /autoware/ansible/
COPY docker/scripts/cleanup_apt.sh /autoware/cleanup_apt.sh
RUN chmod +x /autoware/cleanup_apt.sh
COPY docker/scripts/resolve_rosdep_keys.sh /autoware/resolve_rosdep_keys.sh
RUN chmod +x /autoware/resolve_rosdep_keys.sh
WORKDIR /autoware

RUN rm -f /etc/apt/apt.conf.d/docker-clean \
  && echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' >/etc/apt/apt.conf.d/keep-cache
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  ./setup-dev-env.sh -y rosdep \
  && pip uninstall -y ansible ansible-core \
  && /autoware/cleanup_apt.sh

# Generate install package lists
COPY src/core /autoware/src/core
RUN rosdep update && /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
  > /rosdep-core-depend-packages.txt \
  && cat /rosdep-core-depend-packages.txt

COPY src/universe/external /autoware/src/universe/external
COPY src/universe/autoware.universe/common /autoware/src/universe/autoware.universe/common
COPY src/vehicle /autoware/src/vehicle
COPY src/param /autoware/src/param
COPY src/obigo_launch /autoware/src/obigo_launch
COPY src/universe/autoware.universe/visualization /autoware/src/universe/autoware.universe/visualization
RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
  > /rosdep-universe-common-depend-packages.txt \
  && cat /rosdep-universe-common-depend-packages.txt

FROM rosdep-depend AS rosdep-universe-perception-depend
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO

COPY src/universe/autoware.universe/perception /autoware/src/universe/autoware.universe/perception
COPY src/universe/autoware.universe/sensing/autoware_cuda_utils /autoware/src/universe/autoware.universe/sensing/autoware_cuda_utils
COPY src/universe/autoware.universe/sensing/autoware_pointcloud_preprocessor /autoware/src/universe/autoware.universe/sensing/autoware_pointcloud_preprocessor
COPY src/universe/autoware.universe/sensing/autoware_image_transport_decompressor /autoware/src/universe/autoware.universe/sensing/autoware_image_transport_decompressor
COPY src/universe/autoware.universe/sensing/autoware_pcl_extensions /autoware/src/universe/autoware.universe/sensing/autoware_pcl_extensions
COPY src/universe/autoware.universe/launch/tier4_perception_launch /autoware/src/universe/autoware.universe/launch/tier4_perception_launch
###
COPY src/universe/autoware.universe/evaluator/perception_online_evaluator /autoware/src/universe/autoware.universe/evaluator/perception_online_evaluator
COPY src/universe/autoware.universe/launch/perception_simulator_launch /autoware/src/universe/autoware.universe/launch/perception_simulator_launch
COPY src/universe/autoware.universe/simulator/dummy_perception_publisher /autoware/src/universe/autoware.universe/simulator/dummy_perception_publisher 

RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
    > /rosdep-universe-perception-depend-packages.txt \
    && cat /rosdep-universe-perception-depend-packages.txt
RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
    > /rosdep-universe-perception-exec-depend-packages.txt \
    && cat /rosdep-universe-perception-exec-depend-packages.txt


FROM rosdep-depend AS rosdep-universe-sensing-depend
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO

COPY src/universe/autoware.universe/sensing /autoware/src/universe/autoware.universe/sensing
COPY src/universe/autoware.universe/launch/tier4_sensing_launch /autoware/src/universe/autoware.universe/launch/tier4_sensing_launch
# for rviz2 and sensing
COPY src/sensor_component /autoware/src/sensor_component
COPY src/sensor_kit /autoware/src/sensor_kit
# for rviz2
COPY src/universe/autoware.universe/simulator/tier4_dummy_object_rviz_plugin /autoware/src/universe/autoware.universe/simulator/tier4_dummy_object_rviz_plugin


RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
    > /rosdep-universe-sensing-depend-packages.txt \
    && cat /rosdep-universe-sensing-depend-packages.txt
RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
    > /rosdep-universe-sensing-exec-depend-packages.txt \
    && cat /rosdep-universe-sensing-exec-depend-packages.txt


FROM rosdep-depend AS rosdep-universe-localization-depend
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO

COPY src/universe/autoware.universe/localization /autoware/src/universe/autoware.universe/localization
#Dependencies
COPY src/universe/autoware.universe/map/autoware_map_height_fitter /autoware/src/universe/autoware.universe/map/autoware_map_height_fitter
COPY src/universe/autoware.universe/launch/tier4_localization_launch /autoware/src/universe/autoware.universe/launch/tier4_localization_launch
#Dependencies of tier4_localization_launch
COPY src/universe/autoware.universe/sensing/autoware_pointcloud_preprocessor /autoware/src/universe/autoware.universe/sensing/autoware_pointcloud_preprocessor
COPY src/universe/autoware.universe/system/default_ad_api_helpers/automatic_pose_initializer /autoware/src/universe/autoware.universe/system/default_ad_api_helpers/automatic_pose_initializer
COPY src/universe/autoware.universe/sensing/autoware_pcl_extensions /autoware/src/universe/autoware.universe/sensing/autoware_pcl_extensions

RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
    > /rosdep-universe-localization-depend-packages.txt \
    && cat /rosdep-universe-localization-depend-packages.txt
RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
    > /rosdep-universe-localization-exec-depend-packages.txt \
    && cat /rosdep-universe-localization-exec-depend-packages.txt


FROM rosdep-depend AS rosdep-universe-mapping-depend
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO

COPY src/universe/autoware.universe/map /autoware/src/universe/autoware.universe/map
COPY src/universe/autoware.universe/launch/tier4_map_launch /autoware/src/universe/autoware.universe/launch/tier4_map_launch

RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
    > /rosdep-universe-mapping-depend-packages.txt \
    && cat /rosdep-universe-mapping-depend-packages.txt
RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
    > /rosdep-universe-mapping-exec-depend-packages.txt \
    && cat /rosdep-universe-mapping-exec-depend-packages.txt


FROM rosdep-depend AS rosdep-universe-planning-depend
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO

COPY src/universe/autoware.universe/planning /autoware/src/universe/autoware.universe/planning
# TODO(youtalk): Remove COPYs when https://github.com/autowarefoundation/autoware.universe/issues/8805 is resolved
COPY src/universe/autoware.universe/map/autoware_map_loader /autoware/src/universe/autoware.universe/map/autoware_map_loader
COPY src/universe/autoware.universe/map/autoware_map_projection_loader /autoware/src/universe/autoware.universe/map/autoware_map_projection_loader
#COPY src/universe/autoware.universe/sensing/autoware_pcl_extensions /autoware/src/universe/autoware.universe/sensing/autoware_pcl_extensions
COPY src/universe/autoware.universe/control/autoware_lane_departure_checker /autoware/src/universe/autoware.universe/control/autoware_lane_departure_checker
COPY src/universe/autoware.universe/launch/tier4_planning_launch /autoware/src/universe/autoware.universe/launch/tier4_planning_launch
#Dependencies of tier4_planning_launch
COPY src/universe/autoware.universe/control/autoware_external_cmd_selector /autoware/src/universe/autoware.universe/control/autoware_external_cmd_selector
COPY src/universe/autoware.universe/evaluator/autoware_planning_evaluator /autoware/src/universe/autoware.universe/evaluator/autoware_planning_evaluator
#COPY src/universe/autoware.universe/evaluator/autoware_evaluator_utils /autoware/src/universe/autoware.universe/evaluator/autoware_evaluator_utils

RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
    > /rosdep-universe-planning-depend-packages.txt \
    && cat /rosdep-universe-planning-depend-packages.txt
RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
    > /rosdep-universe-planning-exec-depend-packages.txt \
    && cat /rosdep-universe-planning-exec-depend-packages.txt

FROM rosdep-depend AS rosdep-universe-control-depend
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO

COPY src/universe/autoware.universe/control /autoware/src/universe/autoware.universe/control
COPY src/universe/autoware.universe/sensing/autoware_pointcloud_preprocessor /autoware/src/universe/autoware.universe/sensing/autoware_pointcloud_preprocessor
COPY src/universe/autoware.universe/sensing/autoware_pcl_extensions /autoware/src/universe/autoware.universe/sensing/autoware_pcl_extensions
COPY src/universe/autoware.universe/launch/tier4_control_launch /autoware/src/universe/autoware.universe/launch/tier4_control_launch
#Dependencies of tier4_control_launch
COPY src/universe/autoware.universe/evaluator/autoware_control_evaluator /autoware/src/universe/autoware.universe/evaluator/autoware_control_evaluator
COPY src/universe/autoware.universe/vehicle/autoware_external_cmd_converter /autoware/src/universe/autoware.universe/vehicle/autoware_external_cmd_converter
#COPY src/universe/autoware.universe/evaluator/autoware_evaluator_utils /autoware/src/universe/autoware.universe/evaluator/autoware_evaluator_utils
COPY src/universe/autoware.universe/vehicle/autoware_raw_vehicle_cmd_converter /autoware/src/universe/autoware.universe/vehicle/autoware_raw_vehicle_cmd_converter
COPY src/universe/autoware.universe/planning/autoware_route_handler /autoware/src/universe/autoware.universe/planning/autoware_route_handler

COPY src/universe/autoware.universe/launch/tier4_simulator_launch /autoware/src/universe/autoware.universe/launch/tier4_simulator_launch
#Dependencies of tier4_simulator_launch
COPY src/universe/autoware.universe/simulator/fault_injection /autoware/src/universe/autoware.universe/simulator/fault_injection
COPY src/universe/autoware.universe/simulator/dummy_perception_publisher /autoware/src/universe/autoware.universe/simulator/dummy_perception_publisher 
COPY src/universe/autoware.universe/simulator/simple_planning_simulator /autoware/src/universe/autoware.universe/simulator/simple_planning_simulator
COPY src/universe/autoware.universe/simulator/learning_based_vehicle_model /autoware/src/universe/autoware.universe/simulator/learning_based_vehicle_model
COPY src/universe/autoware.universe/simulator/vehicle_door_simulator /autoware/src/universe/autoware.universe/simulator/vehicle_door_simulator
#COPY src/universe/autoware.universe/evaluator/diagnostic_converter /autoware/src/universe/autoware.universe/evaluator/diagnostic_converter
#COPY src/universe/autoware.universe/perception/autoware_shape_estimation /autoware/src/universe/autoware.universe/perception/autoware_shape_estimation
#COPY src/universe/autoware.universe/perception/autoware_tensorrt_common /autoware/src/universe/autoware.universe/perception/autoware_tensorrt_common
#COPY src/universe/autoware.universe/sensing/autoware_cuda_utils /autoware/src/universe/autoware.universe/sensing/autoware_cuda_utils

COPY src/universe/autoware.universe/launch/tier4_autoware_api_launch /autoware/src/universe/autoware.universe/launch/tier4_autoware_api_launch
#Dependencies of tier4_autoware_api_launch
COPY src/universe/autoware.universe/system/autoware_default_adapi /autoware/src/universe/autoware.universe/system/autoware_default_adapi
COPY src/universe/autoware.universe/system/default_ad_api_helpers/ad_api_adaptors /autoware/src/universe/autoware.universe/system/default_ad_api_helpers/ad_api_adaptors
COPY src/universe/autoware.universe/map/autoware_map_height_fitter /autoware/src/universe/autoware.universe/map/autoware_map_height_fitter
COPY src/universe/autoware.universe/system/diagnostic_graph_utils /autoware/src/universe/autoware.universe/system/diagnostic_graph_utils

RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
    > /rosdep-universe-control-depend-packages.txt \
    && cat /rosdep-universe-control-depend-packages.txt
RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
    > /rosdep-universe-control-exec-depend-packages.txt \
    && cat /rosdep-universe-control-exec-depend-packages.txt

FROM rosdep-depend AS rosdep-universe-vehicle-depend
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO

COPY src/universe/autoware.universe/vehicle /autoware/src/universe/autoware.universe/vehicle
COPY src/universe/autoware.universe/launch/tier4_vehicle_launch /autoware/src/universe/autoware.universe/launch/tier4_vehicle_launch
COPY src/universe/autoware.universe/localization/autoware_pose2twist /autoware/src/universe/autoware.universe/localization/autoware_pose2twist
RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
    > /rosdep-universe-vehicle-depend-packages.txt \
    && cat /rosdep-universe-vehicle-depend-packages.txt
RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
    > /rosdep-universe-vehicle-exec-depend-packages.txt \
    && cat /rosdep-universe-vehicle-exec-depend-packages.txt


FROM rosdep-depend AS rosdep-universe-system-depend
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO

COPY src/universe/autoware.universe/system /autoware/src/universe/autoware.universe/system
COPY src/universe/autoware.universe/map/autoware_map_height_fitter /autoware/src/universe/autoware.universe/map/autoware_map_height_fitter
COPY src/universe/autoware.universe/launch/tier4_system_launch /autoware/src/universe/autoware.universe/launch/tier4_system_launch
#COPY src/universe/autoware.universe/localization/autoware_pose2twist /autoware/src/universe/autoware.universe/localization/autoware_pose2twist
RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
    > /rosdep-universe-system-depend-packages.txt \
    && cat /rosdep-universe-system-depend-packages.txt
RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
    > /rosdep-universe-system-exec-depend-packages.txt \
    && cat /rosdep-universe-system-exec-depend-packages.txt



FROM rosdep-depend AS rosdep-universe-depend
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO

COPY src/launcher /autoware/src/launcher
#COPY src/param /autoware/src/param
#COPY src/sensor_component /autoware/src/sensor_component
#COPY src/sensor_kit /autoware/src/sensor_kit
COPY src/universe /autoware/src/universe
#####COPY src/vehicle /autoware/src/vehicle
RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
  > /rosdep-universe-depend-packages.txt \
  && cat /rosdep-universe-depend-packages.txt

RUN /autoware/resolve_rosdep_keys.sh /autoware/src ${ROS_DISTRO} \
  > /rosdep-exec-depend-packages.txt \
  && cat /rosdep-exec-depend-packages.txt

# hadolint ignore=DL3006
FROM $AUTOWARE_BASE_IMAGE AS core-devel
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ENV CCACHE_DIR="/root/.ccache"

COPY docker/scripts/build_and_clean.sh /autoware/build_and_clean.sh
RUN chmod +x /autoware/build_and_clean.sh

# Set up development environment and tools
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  ./setup-dev-env.sh -y --module all --no-nvidia --no-cuda-drivers openadkit \
  && ./setup-dev-env.sh -y --module dev-tools openadkit \
  && pip uninstall -y ansible ansible-core \
  && /autoware/cleanup_apt.sh

# Install rosdep dependencies
COPY --from=rosdep-depend /rosdep-core-depend-packages.txt /tmp/rosdep-core-depend-packages.txt
# hadolint ignore=SC2002
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update \
  && cat /tmp/rosdep-core-depend-packages.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_apt.sh

RUN --mount=type=cache,target=${CCACHE_DIR} \
  --mount=type=bind,from=rosdep-depend,source=/autoware/src/core,target=/autoware/src/core \
  source /opt/ros/"$ROS_DISTRO"/setup.bash \
  && /autoware/build_and_clean.sh ${CCACHE_DIR} /opt/autoware

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]

FROM core-devel AS universe-common-devel
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ENV CCACHE_DIR="/root/.ccache"

# Install rosdep dependencies
COPY --from=rosdep-depend /rosdep-universe-common-depend-packages.txt /tmp/rosdep-universe-common-depend-packages.txt
# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update \
  && cat /tmp/rosdep-universe-common-depend-packages.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_apt.sh

# hadolint ignore=SC1091
RUN --mount=type=cache,target=${CCACHE_DIR} \
  --mount=type=bind,from=rosdep-depend,source=/autoware/src/universe/autoware.universe/common,target=/autoware/src/universe/autoware.universe/common \
  --mount=type=bind,from=rosdep-depend,source=/autoware/src/universe/external,target=/autoware/src/universe/external \
  --mount=type=bind,from=rosdep-depend,source=/autoware/src/vehicle,target=/autoware/src/vehicle \
  --mount=type=bind,from=rosdep-depend,source=/autoware/src/param,target=/autoware/src/param \
  --mount=type=bind,from=rosdep-depend,source=/autoware/src/obigo_launch,target=/autoware/src/obigo_launch \
  --mount=type=bind,from=rosdep-depend,source=/autoware/src/universe/autoware.universe/visualization,target=/autoware/src/universe/autoware.universe/visualization \
  source /opt/ros/"$ROS_DISTRO"/setup.bash \
  && source /opt/autoware/setup.bash \
  && /autoware/build_and_clean.sh ${CCACHE_DIR} /opt/autoware

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]

FROM universe-common-devel AS universe-common-devel-cuda
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Set up CUDA development environment
# hadolint ignore=SC2002
RUN --mount=type=ssh \
  ./setup-dev-env.sh -y --module all --no-cuda-drivers openadkit \
  && pip uninstall -y ansible ansible-core \
  && /autoware/cleanup_apt.sh true

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]

FROM universe-common-devel AS universe-perception-devel
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ENV CCACHE_DIR="/root/.ccache"

# Install rosdep dependencies
COPY --from=rosdep-universe-perception-depend /rosdep-universe-perception-depend-packages.txt /tmp/rosdep-universe-perception-depend-packages.txt
# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update \
  && cat /tmp/rosdep-universe-perception-depend-packages.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_apt.sh

# hadolint ignore=SC1091
RUN --mount=type=cache,target=${CCACHE_DIR} \
  --mount=type=bind,from=rosdep-universe-perception-depend,source=/autoware/src/universe/autoware.universe/perception,target=/autoware/src/universe/autoware.universe/perception \
  --mount=type=bind,from=rosdep-universe-perception-depend,source=/autoware/src/universe/autoware.universe/sensing/autoware_cuda_utils,target=/autoware/src/universe/autoware.universe/sensing/autoware_cuda_utils \
  --mount=type=bind,from=rosdep-universe-perception-depend,source=/autoware/src/universe/autoware.universe/sensing/autoware_pointcloud_preprocessor,target=/autoware/src/universe/autoware.universe/sensing/autoware_pointcloud_preprocessor \
  --mount=type=bind,from=rosdep-universe-perception-depend,source=/autoware/src/universe/autoware.universe/sensing/autoware_image_transport_decompressor,target=/autoware/src/universe/autoware.universe/sensing/autoware_image_transport_decompressor \
  --mount=type=bind,from=rosdep-universe-perception-depend,source=/autoware/src/universe/autoware.universe/sensing/autoware_pcl_extensions,target=/autoware/src/universe/autoware.universe/sensing/autoware_pcl_extensions \
  --mount=type=bind,from=rosdep-universe-perception-depend,source=/autoware/src/universe/autoware.universe/launch/tier4_perception_launch,target=/autoware/src/universe/autoware.universe/launch/tier4_perception_launch \
  --mount=type=bind,from=rosdep-universe-perception-depend,source=/autoware/src/universe/autoware.universe/evaluator/perception_online_evaluator,target=/autoware/src/universe/autoware.universe/evaluator/perception_online_evaluator \
  --mount=type=bind,from=rosdep-universe-perception-depend,source=/autoware/src/universe/autoware.universe/launch/perception_simulator_launch,target=/autoware/src/universe/autoware.universe/launch/perception_simulator_launch \
  --mount=type=bind,from=rosdep-universe-perception-depend,source=/autoware/src/universe/autoware.universe/simulator/dummy_perception_publisher,target=/autoware/src/universe/autoware.universe/simulator/dummy_perception_publisher \
  source /opt/ros/"$ROS_DISTRO"/setup.bash \
  && source /opt/autoware/setup.bash \
  && /autoware/build_and_clean.sh ${CCACHE_DIR} /opt/autoware

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]


FROM universe-common-devel-cuda AS universe-perception-devel-cuda
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ENV CCACHE_DIR="/root/.ccache"

# Install rosdep dependencies
COPY --from=rosdep-universe-perception-depend /rosdep-universe-perception-depend-packages.txt /tmp/rosdep-universe-perception-depend-packages.txt
# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update \
  && cat /tmp/rosdep-universe-perception-depend-packages.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_apt.sh

COPY --from=universe-perception-devel /opt/autoware /opt/autoware

# hadolint ignore=SC1091
RUN --mount=type=cache,target=${CCACHE_DIR} \
  --mount=type=bind,from=rosdep-universe-perception-depend,source=/autoware/src/universe/autoware.universe/perception,target=/autoware/src/universe/autoware.universe/perception \
  --mount=type=bind,from=rosdep-universe-perception-depend,source=/autoware/src/universe/autoware.universe/sensing/autoware_cuda_utils,target=/autoware/src/universe/autoware.universe/sensing/autoware_cuda_utils \
  source /opt/ros/"$ROS_DISTRO"/setup.bash \
  && source /opt/autoware/setup.bash \
  && /autoware/build_and_clean.sh ${CCACHE_DIR} /opt/autoware "--packages-above-and-dependencies autoware_tensorrt_common autoware_cuda_utils"

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]

FROM universe-common-devel AS universe-sensing-devel
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ENV CCACHE_DIR="/root/.ccache"

# Install rosdep dependencies
COPY --from=rosdep-universe-sensing-depend /rosdep-universe-sensing-depend-packages.txt /tmp/rosdep-universe-sensing-depend-packages.txt
# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update \
  && cat /tmp/rosdep-universe-sensing-depend-packages.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_apt.sh

# hadolint ignore=SC1091
RUN --mount=type=cache,target=${CCACHE_DIR} \
  --mount=type=bind,from=rosdep-universe-sensing-depend,source=/autoware/src/universe/autoware.universe/sensing,target=/autoware/src/universe/autoware.universe/sensing \
  --mount=type=bind,from=rosdep-universe-sensing-depend,source=/autoware/src/sensor_component,target=/autoware/src/sensor_component \
  --mount=type=bind,from=rosdep-universe-sensing-depend,source=/autoware/src/sensor_kit,target=/autoware/src/sensor_kit \
  --mount=type=bind,from=rosdep-universe-sensing-depend,source=/autoware/src/universe/autoware.universe/launch/tier4_sensing_launch,target=/autoware/src/universe/autoware.universe/launch/tier4_sensing_launch \
  --mount=type=bind,from=rosdep-universe-sensing-depend,source=/autoware/src/universe/autoware.universe/simulator/tier4_dummy_object_rviz_plugin,target=/autoware/src/universe/autoware.universe/simulator/tier4_dummy_object_rviz_plugin \
  source /opt/ros/"$ROS_DISTRO"/setup.bash \
  && source /opt/autoware/setup.bash \
  && /autoware/build_and_clean.sh ${CCACHE_DIR} /opt/autoware

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]

FROM universe-common-devel-cuda AS universe-sensing-devel-cuda
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ENV CCACHE_DIR="/root/.ccache"

# Install rosdep dependencies
COPY --from=rosdep-universe-sensing-depend /rosdep-universe-sensing-depend-packages.txt /tmp/rosdep-universe-sensing-depend-packages.txt
# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update \
  && cat /tmp/rosdep-universe-sensing-depend-packages.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_apt.sh

COPY --from=universe-sensing-devel /opt/autoware /opt/autoware

# hadolint ignore=SC1091
RUN --mount=type=cache,target=${CCACHE_DIR} \
  --mount=type=bind,from=rosdep-universe-sensing-depend,source=/autoware/src/universe/autoware.universe/sensing,target=/autoware/src/universe/autoware.universe/sensing \
  source /opt/ros/"$ROS_DISTRO"/setup.bash \
  && source /opt/autoware/setup.bash \
  && /autoware/build_and_clean.sh ${CCACHE_DIR} /opt/autoware "--packages-above-and-dependencies autoware_cuda_utils"

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]

FROM universe-common-devel AS universe-localization-devel
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ENV CCACHE_DIR="/root/.ccache"

# Install rosdep dependencies
COPY --from=rosdep-universe-localization-depend /rosdep-universe-localization-depend-packages.txt /tmp/rosdep-universe-localization-depend-packages.txt
# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update \
  && cat /tmp/rosdep-universe-localization-depend-packages.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_apt.sh

# hadolint ignore=SC1091
RUN --mount=type=cache,target=${CCACHE_DIR} \
  --mount=type=bind,from=rosdep-universe-localization-depend,source=/autoware/src/universe/autoware.universe/localization,target=/autoware/src/universe/autoware.universe/localization \
  --mount=type=bind,from=rosdep-universe-localization-depend,source=/autoware/src/universe/autoware.universe/map/autoware_map_height_fitter,target=/autoware/src/universe/autoware.universe/map/autoware_map_height_fitter \ 
  --mount=type=bind,from=rosdep-universe-localization-depend,source=/autoware/src/universe/autoware.universe/launch/tier4_localization_launch,target=/autoware/src/universe/autoware.universe/launch/tier4_localization_launch \
  --mount=type=bind,from=rosdep-universe-localization-depend,source=/autoware/src/universe/autoware.universe/sensing/autoware_pointcloud_preprocessor,target=/autoware/src/universe/autoware.universe/sensing/autoware_pointcloud_preprocessor \
  --mount=type=bind,from=rosdep-universe-localization-depend,source=/autoware/src/universe/autoware.universe/sensing/autoware_pcl_extensions,target=/autoware/src/universe/autoware.universe/sensing/autoware_pcl_extensions \
  source /opt/ros/"$ROS_DISTRO"/setup.bash \
  && source /opt/autoware/setup.bash \
  && /autoware/build_and_clean.sh ${CCACHE_DIR} /opt/autoware


FROM universe-common-devel AS universe-mapping-devel
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ENV CCACHE_DIR="/root/.ccache"

# Install rosdep dependencies
COPY --from=rosdep-universe-mapping-depend /rosdep-universe-mapping-depend-packages.txt /tmp/rosdep-universe-mapping-depend-packages.txt
# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update \
  && cat /tmp/rosdep-universe-mapping-depend-packages.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_apt.sh

# hadolint ignore=SC1091
RUN --mount=type=cache,target=${CCACHE_DIR} \
  --mount=type=bind,from=rosdep-universe-mapping-depend,source=/autoware/src/universe/autoware.universe/map,target=/autoware/src/universe/autoware.universe/map \
  --mount=type=bind,from=rosdep-universe-mapping-depend,source=/autoware/src/universe/autoware.universe/launch/tier4_map_launch,target=/autoware/src/universe/autoware.universe/launch/tier4_map_launch \
  source /opt/ros/"$ROS_DISTRO"/setup.bash \
  && source /opt/autoware/setup.bash \
  && /autoware/build_and_clean.sh ${CCACHE_DIR} /opt/autoware


FROM universe-common-devel AS universe-planning-devel
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ENV CCACHE_DIR="/root/.ccache"

# Install rosdep dependencies
COPY --from=rosdep-universe-planning-depend /rosdep-universe-planning-depend-packages.txt /tmp/rosdep-universe-planning-depend-packages.txt
# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update \
  && cat /tmp/rosdep-universe-planning-depend-packages.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_apt.sh

# hadolint ignore=SC1091
RUN --mount=type=cache,target=${CCACHE_DIR} \
  --mount=type=bind,from=rosdep-universe-planning-depend,source=/autoware/src/universe/autoware.universe/planning,target=/autoware/src/universe/autoware.universe/planning \
  # TODO(youtalk): Remove --mount options when https://github.com/autowarefoundation/autoware.universe/issues/8805 is resolved
  --mount=type=bind,from=rosdep-universe-planning-depend,source=/autoware/src/universe/autoware.universe/map/autoware_map_loader,target=/autoware/src/universe/autoware.universe/map/autoware_map_loader \
  --mount=type=bind,from=rosdep-universe-planning-depend,source=/autoware/src/universe/autoware.universe/map/autoware_map_projection_loader,target=/autoware/src/universe/autoware.universe/map/autoware_map_projection_loader \
  #--mount=type=bind,from=rosdep-universe-planning-depend,source=/autoware/src/universe/autoware.universe/sensing/autoware_pcl_extensions,target=/autoware/src/universe/autoware.universe/sensing/autoware_pcl_extensions \
  #--mount=type=bind,from=rosdep-universe-planning-depend,source=/autoware/src/universe/autoware.universe/sensing/autoware_pointcloud_preprocessor,target=/autoware/src/universe/autoware.universe/sensing/autoware_pointcloud_preprocessor \
  --mount=type=bind,from=rosdep-universe-planning-depend,source=/autoware/src/universe/autoware.universe/control/autoware_lane_departure_checker,target=/autoware/src/universe/autoware.universe/control/autoware_lane_departure_checker \
  --mount=type=bind,from=rosdep-universe-planning-depend,source=/autoware/src/universe/autoware.universe/launch/tier4_planning_launch,target=/autoware/src/universe/autoware.universe/launch/tier4_planning_launch \
  --mount=type=bind,from=rosdep-universe-planning-depend,source=/autoware/src/universe/autoware.universe/control/autoware_external_cmd_selector,target=/autoware/src/universe/autoware.universe/control/autoware_external_cmd_selector \
  --mount=type=bind,from=rosdep-universe-planning-depend,source=/autoware/src/universe/autoware.universe/evaluator/autoware_planning_evaluator,target=/autoware/src/universe/autoware.universe/evaluator/autoware_planning_evaluator \
  #--mount=type=bind,from=rosdep-universe-planning-depend,source=/autoware/src/universe/autoware.universe/evaluator/autoware_evaluator_utils,target=/autoware/src/universe/autoware.universe/evaluator/autoware_evaluator_utils \
  source /opt/ros/"$ROS_DISTRO"/setup.bash \
  && source /opt/autoware/setup.bash \
  && /autoware/build_and_clean.sh ${CCACHE_DIR} /opt/autoware

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]


FROM universe-common-devel AS universe-control-devel
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ENV CCACHE_DIR="/root/.ccache"

# Install rosdep dependencies
COPY --from=rosdep-universe-control-depend /rosdep-universe-control-depend-packages.txt /tmp/rosdep-universe-control-depend-packages.txt
# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update \
  && cat /tmp/rosdep-universe-control-depend-packages.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_apt.sh

# hadolint ignore=SC1091
RUN --mount=type=cache,target=${CCACHE_DIR} \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/control,target=/autoware/src/universe/autoware.universe/control \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/launch/tier4_control_launch,target=/autoware/src/universe/autoware.universe/launch/tier4_control_launch \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/sensing/autoware_pointcloud_preprocessor,target=/autoware/src/universe/autoware.universe/sensing/autoware_pointcloud_preprocessor \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/sensing/autoware_pcl_extensions,target=/autoware/src/universe/autoware.universe/sensing/autoware_pcl_extensions \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/evaluator/autoware_control_evaluator,target=/autoware/src/universe/autoware.universe/evaluator/autoware_control_evaluator \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/vehicle/autoware_external_cmd_converter,target=/autoware/src/universe/autoware.universe/vehicle/autoware_external_cmd_converter \
  #--mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/evaluator/autoware_evaluator_utils,target=/autoware/src/universe/autoware.universe/evaluator/autoware_evaluator_utils \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/vehicle/autoware_raw_vehicle_cmd_converter,target=/autoware/src/universe/autoware.universe/vehicle/autoware_raw_vehicle_cmd_converter \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/planning/autoware_route_handler,target=/autoware/src/universe/autoware.universe/planning/autoware_route_handler \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/launch/tier4_simulator_launch,target=/autoware/src/universe/autoware.universe/launch/tier4_simulator_launch \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/simulator/fault_injection,target=/autoware/src/universe/autoware.universe/simulator/fault_injection \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/simulator/dummy_perception_publisher,target=/autoware/src/universe/autoware.universe/simulator/dummy_perception_publisher \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/simulator/simple_planning_simulator,target=/autoware/src/universe/autoware.universe/simulator/simple_planning_simulator \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/simulator/learning_based_vehicle_model,target=/autoware/src/universe/autoware.universe/simulator/learning_based_vehicle_model \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/simulator/vehicle_door_simulator,target=/autoware/src/universe/autoware.universe/simulator/vehicle_door_simulator \
  #--mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/evaluator/diagnostic_converter,target=/autoware/src/universe/autoware.universe/evaluator/diagnostic_converter \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/launch/tier4_autoware_api_launch,target=/autoware/src/universe/autoware.universe/launch/tier4_autoware_api_launch \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/system/autoware_default_adapi,target=/autoware/src/universe/autoware.universe/system/autoware_default_adapi \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/system/default_ad_api_helpers/ad_api_adaptors,target=/autoware/src/universe/autoware.universe/system/default_ad_api_helpers/ad_api_adaptors \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/map/autoware_map_height_fitter,target=/autoware/src/universe/autoware.universe/map/autoware_map_height_fitter \
  --mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/system/diagnostic_graph_utils,target=/autoware/src/universe/autoware.universe/system/diagnostic_graph_utils \
  #--mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/perception/autoware_shape_estimation,target=/autoware/src/universe/autoware.universe/perception/autoware_shape_estimation \
  #--mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/perception/autoware_tensorrt_common,target=/autoware/src/universe/autoware.universe/perception/autoware_tensorrt_common \
  #--mount=type=bind,from=rosdep-universe-control-depend,source=/autoware/src/universe/autoware.universe/sensing/autoware_cuda_utils,target=/autoware/src/universe/autoware.universe/sensing/autoware_cuda_utils \
  source /opt/ros/"$ROS_DISTRO"/setup.bash \
  && source /opt/autoware/setup.bash \
  && /autoware/build_and_clean.sh ${CCACHE_DIR} /opt/autoware

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]


FROM universe-common-devel AS universe-vehicle-devel
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ENV CCACHE_DIR="/root/.ccache"

# Install rosdep dependencies
COPY --from=rosdep-universe-vehicle-depend /rosdep-universe-vehicle-depend-packages.txt /tmp/rosdep-universe-vehicle-depend-packages.txt
# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update \
  && cat /tmp/rosdep-universe-vehicle-depend-packages.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_apt.sh

# hadolint ignore=SC1091
RUN --mount=type=cache,target=${CCACHE_DIR} \
  --mount=type=bind,from=rosdep-universe-vehicle-depend,source=/autoware/src/universe/autoware.universe/vehicle,target=/autoware/src/universe/autoware.universe/vehicle \
  --mount=type=bind,from=rosdep-universe-vehicle-depend,source=/autoware/src/universe/autoware.universe/launch/tier4_vehicle_launch,target=/autoware/src/universe/autoware.universe/launch/tier4_vehicle_launch \
  #--mount=type=bind,from=rosdep-universe-vehicle-system-depend,source=/autoware/src/universe/autoware.universe/map/autoware_map_height_fitter,target=/autoware/src/universe/autoware.universe/map/autoware_map_height_fitter \
  --mount=type=bind,from=rosdep-universe-vehicle-depend,source=/autoware/src/universe/autoware.universe/localization/autoware_pose2twist,target=/autoware/src/universe/autoware.universe/localization/autoware_pose2twist \
  source /opt/ros/"$ROS_DISTRO"/setup.bash \
  && source /opt/autoware/setup.bash \
  && /autoware/build_and_clean.sh ${CCACHE_DIR} /opt/autoware

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]

FROM universe-common-devel AS universe-system-devel
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ENV CCACHE_DIR="/root/.ccache"

# Install rosdep dependencies
COPY --from=rosdep-universe-system-depend /rosdep-universe-system-depend-packages.txt /tmp/rosdep-universe-system-depend-packages.txt
# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update \
  && cat /tmp/rosdep-universe-system-depend-packages.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_apt.sh

# hadolint ignore=SC1091
RUN --mount=type=cache,target=${CCACHE_DIR} \
  --mount=type=bind,from=rosdep-universe-system-depend,source=/autoware/src/universe/autoware.universe/system,target=/autoware/src/universe/autoware.universe/system \
  --mount=type=bind,from=rosdep-universe-system-depend,source=/autoware/src/universe/autoware.universe/map/autoware_map_height_fitter,target=/autoware/src/universe/autoware.universe/map/autoware_map_height_fitter \
  --mount=type=bind,from=rosdep-universe-system-depend,source=/autoware/src/universe/autoware.universe/launch/tier4_system_launch,target=/autoware/src/universe/autoware.universe/launch/tier4_system_launch \
  #--mount=type=bind,from=rosdep-universe-vehicle-system-depend,source=/autoware/src/universe/autoware.universe/localization/autoware_pose2twist,target=/autoware/src/universe/autoware.universe/localization/autoware_pose2twist \
  source /opt/ros/"$ROS_DISTRO"/setup.bash \
  && source /opt/autoware/setup.bash \
  && /autoware/build_and_clean.sh ${CCACHE_DIR} /opt/autoware

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]



FROM universe-common-devel AS universe-devel
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ENV CCACHE_DIR="/root/.ccache"

# Install rosdep dependencies
COPY --from=rosdep-universe-depend /rosdep-universe-depend-packages.txt /tmp/rosdep-universe-depend-packages.txt
# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update \
  && cat /tmp/rosdep-universe-depend-packages.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_apt.sh


COPY --from=universe-perception-devel /opt/autoware /opt/autoware
COPY --from=universe-sensing-devel /opt/autoware /opt/autoware
COPY --from=universe-localization-devel /opt/autoware /opt/autoware
COPY --from=universe-mapping-devel /opt/autoware /opt/autoware
COPY --from=universe-planning-devel /opt/autoware /opt/autoware
COPY --from=universe-control-devel /opt/autoware /opt/autoware
COPY --from=universe-system-devel /opt/autoware /opt/autoware
COPY --from=universe-vehicle-devel /opt/autoware /opt/autoware

# hadolint ignore=SC1091
RUN --mount=type=cache,target=${CCACHE_DIR} \
  --mount=type=bind,from=rosdep-universe-depend,source=/autoware/src/launcher,target=/autoware/src/launcher \
  #--mount=type=bind,from=rosdep-universe-depend,source=/autoware/src/param,target=/autoware/src/param \
  #--mount=type=bind,from=rosdep-universe-depend,source=/autoware/src/sensor_component,target=/autoware/src/sensor_component \
  #--mount=type=bind,from=rosdep-universe-depend,source=/autoware/src/sensor_kit,target=/autoware/src/sensor_kit \
  --mount=type=bind,from=rosdep-universe-depend,source=/autoware/src/universe/autoware.universe/evaluator,target=/autoware/src/universe/autoware.universe/evaluator \
#  --mount=type=bind,from=rosdep-universe-depend,source=/autoware/src/universe/autoware.universe/launch,target=/autoware/src/universe/autoware.universe/launch \
  --mount=type=bind,from=rosdep-universe-depend,source=/autoware/src/universe/autoware.universe/simulator,target=/autoware/src/universe/autoware.universe/simulator \
  --mount=type=bind,from=rosdep-universe-depend,source=/autoware/src/universe/autoware.universe/tools,target=/autoware/src/universe/autoware.universe/tools \
#####  --mount=type=bind,from=rosdep-universe-depend,source=/autoware/src/vehicle,target=/autoware/src/vehicle \
  source /opt/ros/"$ROS_DISTRO"/setup.bash \
  && source /opt/autoware/setup.bash \
  && /autoware/build_and_clean.sh ${CCACHE_DIR} /opt/autoware

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]

FROM universe-common-devel-cuda AS universe-devel-cuda
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install rosdep dependencies
COPY --from=rosdep-universe-depend /rosdep-universe-depend-packages.txt /tmp/rosdep-universe-depend-packages.txt
# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  apt-get update \
  && cat /tmp/rosdep-universe-depend-packages.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_apt.sh

COPY --from=universe-perception-devel-cuda /opt/autoware /opt/autoware
COPY --from=universe-sensing-devel-cuda /opt/autoware /opt/autoware
COPY --from=universe-devel /opt/autoware /opt/autoware

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]

# hadolint ignore=DL3006
FROM $AUTOWARE_BASE_IMAGE AS adsw-perception
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ARG LIB_DIR
ARG SETUP_ARGS

# Set up runtime environment and artifacts
COPY --from=rosdep-universe-perception-depend /rosdep-universe-perception-exec-depend-packages.txt /tmp/perception-depend.txt
COPY --from=rosdep-universe-sensing-depend /rosdep-universe-sensing-exec-depend-packages.txt /tmp/sensing-depend.txt
COPY --from=rosdep-universe-localization-depend /rosdep-universe-localization-exec-depend-packages.txt /tmp/localization-depend.txt
COPY --from=rosdep-universe-mapping-depend /rosdep-universe-mapping-exec-depend-packages.txt /tmp/mapping-depend.txt

RUN cat /tmp/perception-depend.txt /tmp/sensing-depend.txt /tmp/localization-depend.txt /tmp/mapping-depend.txt | sort | uniq > /tmp/depend.txt

# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  ./setup-dev-env.sh -y --module all --no-nvidia --no-cuda-drivers --runtime openadkit \
  && pip uninstall -y ansible ansible-core \
  && apt-get update \
  && cat /tmp/depend.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_system.sh $LIB_DIR $ROS_DISTRO

COPY --from=universe-perception-devel /opt/autoware /opt/autoware
COPY --from=universe-sensing-devel /opt/autoware /opt/autoware
COPY --from=universe-localization-devel /opt/autoware /opt/autoware
COPY --from=universe-mapping-devel /opt/autoware /opt/autoware

# Copy bash aliases
COPY docker/etc/.bash_aliases /root/.bash_aliases
RUN echo "source /opt/autoware/setup.bash" > /etc/bash.bashrc

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]


FROM $AUTOWARE_BASE_CUDA_IMAGE AS adsw-perception-cuda
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ARG LIB_DIR

# Set up runtime environment and artifacts
COPY --from=rosdep-universe-perception-depend /rosdep-universe-perception-exec-depend-packages.txt /tmp/perception-depend.txt
COPY --from=rosdep-universe-sensing-depend /rosdep-universe-sensing-exec-depend-packages.txt /tmp/sensing-depend.txt
COPY --from=rosdep-universe-localization-depend /rosdep-universe-localization-exec-depend-packages.txt /tmp/localization-depend.txt
COPY --from=rosdep-universe-mapping-depend /rosdep-universe-mapping-exec-depend-packages.txt /tmp/mapping-depend.txt

RUN cat /tmp/perception-depend.txt /tmp/sensing-depend.txt /tmp/localization-depend.txt /tmp/mapping-depend.txt | sort | uniq > /tmp/depend.txt

# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  ./setup-dev-env.sh -y --module all --no-nvidia --no-cuda-drivers --runtime openadkit \
  && pip uninstall -y ansible ansible-core \
  && apt-get update \
  && cat /tmp/depend.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_system.sh $LIB_DIR $ROS_DISTRO

COPY --from=universe-perception-devel-cuda /opt/autoware /opt/autoware
COPY --from=universe-sensing-devel-cuda /opt/autoware /opt/autoware
COPY --from=universe-localization-devel /opt/autoware /opt/autoware
COPY --from=universe-mapping-devel /opt/autoware /opt/autoware

# Copy bash aliases
COPY docker/etc/.bash_aliases /root/.bash_aliases
RUN echo "source /opt/autoware/setup.bash" > /etc/bash.bashrc

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]



FROM $AUTOWARE_BASE_IMAGE AS adsw-decision
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ARG LIB_DIR

# Install rosdep dependencies
COPY --from=rosdep-universe-planning-depend /rosdep-universe-planning-exec-depend-packages.txt /tmp/planning-depend.txt
COPY --from=rosdep-universe-system-depend /rosdep-universe-system-exec-depend-packages.txt /tmp/system-depend.txt

RUN cat /tmp/planning-depend.txt /tmp/system-depend.txt | sort | uniq > /tmp/depend.txt

# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  ./setup-dev-env.sh -y --module all --no-nvidia --no-cuda-drivers --runtime openadkit \
  && pip uninstall -y ansible ansible-core \
  && apt-get update \
  && cat /tmp/depend.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_system.sh $LIB_DIR $ROS_DISTRO

COPY --from=universe-planning-devel /opt/autoware /opt/autoware
COPY --from=universe-system-devel /opt/autoware /opt/autoware

# Copy bash aliases
COPY docker/etc/.bash_aliases /root/.bash_aliases
RUN echo "source /opt/autoware/setup.bash" > /etc/bash.bashrc

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]


FROM $AUTOWARE_BASE_IMAGE AS adsw-control
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ARG LIB_DIR

# Install rosdep dependencies
COPY --from=rosdep-universe-control-depend /rosdep-universe-control-exec-depend-packages.txt /tmp/control-depend.txt
COPY --from=rosdep-universe-vehicle-depend /rosdep-universe-vehicle-exec-depend-packages.txt /tmp/vehicle-depend.txt

RUN cat /tmp/control-depend.txt /tmp/vehicle-depend.txt | sort | uniq > /tmp/depend.txt

# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  ./setup-dev-env.sh -y --module all --no-nvidia --no-cuda-drivers --runtime openadkit \
  && pip uninstall -y ansible ansible-core \
  && apt-get update \
  && cat /tmp/depend.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_system.sh $LIB_DIR $ROS_DISTRO

COPY --from=universe-control-devel /opt/autoware /opt/autoware
COPY --from=universe-vehicle-devel /opt/autoware /opt/autoware

# Copy bash aliases
COPY docker/etc/.bash_aliases /root/.bash_aliases
RUN echo "source /opt/autoware/setup.bash" > /etc/bash.bashrc

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]

# hadolint ignore=DL3006
FROM $AUTOWARE_BASE_IMAGE AS universe
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ARG LIB_DIR

# Set up runtime environment
COPY --from=rosdep-universe-depend /rosdep-exec-depend-packages.txt /tmp/rosdep-exec-depend-packages.txt
# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  ./setup-dev-env.sh -y --module all --no-nvidia --no-cuda-drivers --runtime openadkit \
  && pip uninstall -y ansible ansible-core \
  && apt-get update \
  && cat /tmp/rosdep-exec-depend-packages.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_system.sh $LIB_DIR $ROS_DISTRO

COPY --from=universe-devel /opt/autoware /opt/autoware

# Copy bash aliases
COPY docker/etc/.bash_aliases /root/.bash_aliases
RUN echo "source /opt/autoware/setup.bash" > /etc/bash.bashrc

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]

# hadolint ignore=DL3006
FROM $AUTOWARE_BASE_CUDA_IMAGE AS universe-cuda
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO
ARG LIB_DIR

# Set up runtime environment
COPY --from=rosdep-universe-depend /rosdep-exec-depend-packages.txt /tmp/rosdep-exec-depend-packages.txt
# hadolint ignore=SC2002
RUN --mount=type=ssh \
  --mount=type=cache,target=/var/cache/apt,sharing=locked \
  ./setup-dev-env.sh -y --module all --no-nvidia --no-cuda-drivers --runtime openadkit \
  && pip uninstall -y ansible ansible-core \
  && apt-get update \
  && cat /tmp/rosdep-exec-depend-packages.txt | xargs apt-get install -y --no-install-recommends \
  && /autoware/cleanup_system.sh $LIB_DIR $ROS_DISTRO

COPY --from=universe-devel-cuda /opt/autoware /opt/autoware

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["/bin/bash"]
