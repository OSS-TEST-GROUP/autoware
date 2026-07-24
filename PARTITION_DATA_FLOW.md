# Autoware Partition Data Flow

이 문서는 현재 `katech-partition` 구성에서 RViz로 더미 장애물을 배치했을 때
Perception, Decision/Planning, Control 파티션 사이에서 데이터가 전달되는 흐름을
정리합니다.

## 1. 파티셔닝 기준과 용어

현재 프로젝트는 **컴포넌트 기반 파티셔닝**입니다. Autoware의 기능 영역을 다음과
같이 세 Docker 파티션으로 묶습니다.

| 파티션 | 포함하는 주요 컴포넌트 |
| --- | --- |
| Perception | Map, Sensing, Localization, Perception, Visualization/RViz |
| Decision | Planning, System, Visualization |
| Control | Control, Vehicle Interface, Simulator, AD API |

`partition/partition_config/*.json`에서 `folders`는 위 컴포넌트의 소스 범위를
정의합니다. `packages`는 공통 launch, 설정 또는 다른 컴포넌트에 있는 빌드·실행
의존성을 보완합니다. 따라서 JSON에 패키지 이름이 들어 있어도 파티션 경계를
개별 패키지로 정한 패키지 기반 파티셔닝은 아닙니다.

이 문서와 함께 제공하는 Excel에서는 다음 계층을 구분합니다.

```text
파티션 -> 컴포넌트 -> ROS 2 패키지 -> 노드 -> Publisher/Subscriber -> 토픽
```

- **파티션**: 별도 Docker 이미지와 컨테이너로 실행되는 배포 단위
- **컴포넌트**: Map, Perception, Planning, Control과 같은 기능 영역
- **패키지**: 소스, 실행 파일, launch 및 설정을 배포하는 ROS 2 빌드 단위
- **노드**: 패키지에서 실행되어 ROS graph에 참여하는 런타임 프로세스 또는 component
- **토픽**: Publisher 노드와 Subscriber 노드 사이의 메시지 통신 채널

## 2. 핵심 요약

주행 명령이 생성되는 기본 순서는 다음과 같습니다.

```text
RViz 더미 객체 배치
  -> Perception: 가상 LiDAR Pointcloud 생성
  -> Sensing: Pointcloud 축소 및 차량 영역 제거
  -> Perception: CPU 군집화, 형상 추정, 추적, 예측
  -> Decision/Planning: 경로와 속도 계획, 장애물 앞 정지 trajectory 생성
  -> Control: trajectory 추종, 조향/가감속 명령 생성
  -> 차량 시뮬레이터: 명령을 적용하고 차량 상태를 다시 발행
  -> Decision/Planning 및 Control: 갱신된 차량 상태를 피드백으로 사용
```

즉, 장애물 정보의 주 경로는 `Perception -> Decision/Planning -> Control`입니다.
Control이 장애물 정보를 처리한 뒤 Decision으로 다시 전달하는 구조는 아닙니다.
Control에서 생성된 차량 상태는 시뮬레이터를 거쳐 Planning과 Control 양쪽으로
피드백됩니다.

현재 시험에서 확인된 동작은 차선을 변경해 장애물을 우회하는 동작이 아니라,
Planning이 장애물 앞에 정지점과 0 m/s 구간을 넣고 Control이 이를 따라 정지하는
동작입니다. 장애물을 삭제하면 Planning이 다시 주행 가능한 trajectory를 만들고
차량이 출발합니다.

## 3. 파티션별 역할

| 파티션 | 주요 역할 | 다른 파티션으로 보내는 핵심 토픽 |
| --- | --- | --- |
| Perception | RViz 객체를 가상 LiDAR Pointcloud로 만들고 Sensing 전처리 후 CPU로 검출·추적·예측 | `/perception/object_recognition/objects`, `/perception/obstacle_segmentation/pointcloud` |
| Decision/Planning | 경로, 장애물, 차량 상태를 이용해 최종 주행 trajectory 생성 | `/planning/scenario_planning/trajectory` |
| Control | 최종 trajectory를 추종해 조향 및 가감속 명령 생성 | `/control/command/control_cmd` |
| Control의 차량 시뮬레이터 | 제어 명령을 차량 운동으로 반영하고 차량 상태 생성 | `/localization/kinematic_state`, `/localization/acceleration`, `/vehicle/status/*` |

세 컨테이너는 `--net=host`와 동일한 `ROS_DOMAIN_ID`를 사용하므로 별도의 Docker
컨테이너 링크 없이 ROS 2 DDS 토픽으로 통신합니다.

### 3.1 파티션 경계 토픽

| Publisher | 토픽 | 메시지 형식 | 주요 Subscriber |
| --- | --- | --- | --- |
| RViz | `/simulation/dummy_perception_publisher/object_info` | `tier4_simulation_msgs/msg/DummyObject` | Perception `dummy_perception_publisher` |
| Perception | `/perception/object_recognition/objects` | `autoware_perception_msgs/msg/PredictedObjects` | Decision/Planning 플래너, Control 안전 감시 노드, RViz |
| Perception | `/perception/obstacle_segmentation/pointcloud` | `sensor_msgs/msg/PointCloud2` | Decision/Planning 플래너, Control AEB 및 충돌 검사 노드 |
| Decision/Planning | `/planning/scenario_planning/trajectory` | `autoware_planning_msgs/msg/Trajectory` | Control `trajectory_follower`, 차량 시뮬레이터 |
| Control | `/control/command/control_cmd` | `autoware_control_msgs/msg/Control` | Control 파티션의 `simple_planning_simulator` |
| 차량 시뮬레이터 | `/localization/kinematic_state` | `nav_msgs/msg/Odometry` | Decision/Planning 및 Control |
| 차량 시뮬레이터 | `/localization/acceleration` | `geometry_msgs/msg/AccelWithCovarianceStamped` | Decision/Planning 및 Control |
| 차량 시뮬레이터 | `/vehicle/status/velocity_status` | `autoware_vehicle_msgs/msg/VelocityReport` | Control 및 상태 관리 노드 |
| 차량 시뮬레이터 | `/vehicle/status/steering_status` | `autoware_vehicle_msgs/msg/SteeringReport` | Control 및 상태 관리 노드 |

## 4. 전체 토픽 흐름

```text
[RViz: Bus/Car/Pedestrian Tool]
  /simulation/dummy_perception_publisher/object_info
    tier4_simulation_msgs/msg/DummyObject
        |
        v
[Perception: dummy_perception_publisher]
  /sensing/lidar/virtual/pointcloud_raw
    sensor_msgs/msg/PointCloud2
        |
        v
[Sensing: voxel_grid_downsample_filter_node]
  /sensing/lidar/concatenated/pointcloud
        |
        v
[Sensing: crop_box_filter_node]
  /perception/obstacle_segmentation/pointcloud
        |
        v
[Perception: virtual_lidar_euclidean_cluster]
  /perception/object_recognition/detection/labeled_clusters
        tier4_perception_msgs/msg/DetectedObjectsWithFeature
        |
        v
      shape_estimation
        |
        v
  /perception/object_recognition/detection/objects_with_feature
        tier4_perception_msgs/msg/DetectedObjectsWithFeature
        |
        v
      detected_object_feature_remover
        |
        v
  /perception/object_recognition/detection/objects
        autoware_perception_msgs/msg/DetectedObjects
        |
        v
      multi_object_tracker
        |
        v
  /perception/object_recognition/tracking/objects
        autoware_perception_msgs/msg/TrackedObjects
        |
        v
      map_based_prediction
        |
        v
  /perception/object_recognition/objects
        autoware_perception_msgs/msg/PredictedObjects
        |
        v
[Decision/Planning]
  behavior_path_planner
    -> behavior_velocity_planner
    -> path_smoother / path_optimizer
    -> motion_velocity_planner
    -> obstacle_cruise_planner
    -> scenario_selector
    -> velocity_smoother
    -> planning_validator
        |
        v
  /planning/scenario_planning/trajectory
        autoware_planning_msgs/msg/Trajectory
        |
        v
[Control]
  trajectory_follower
    -> /control/trajectory_follower/control_cmd
    -> vehicle_cmd_gate
    -> /control/command/control_cmd
        autoware_control_msgs/msg/Control
        |
        v
[Control 파티션: simple_planning_simulator]
  /localization/kinematic_state
  /localization/acceleration
  /vehicle/status/velocity_status
  /vehicle/status/steering_status
  /vehicle/status/control_mode
        |
        +----> Decision/Planning 피드백
        +----> Control 피드백
```

## 5. RViz에서 Perception까지

### 5.1 RViz 장애물 입력

RViz의 `Bus`, `Car`, `Pedestrian` 도구는 선택한 위치, 방향, 속도, 객체 종류와
크기를 `DummyObject` 메시지로 발행합니다.

| 동작 | 토픽 | 메시지 | 주요 값 |
| --- | --- | --- | --- |
| 객체 생성 | `/simulation/dummy_perception_publisher/object_info` | `tier4_simulation_msgs/msg/DummyObject` | `action=ADD`, UUID, pose, velocity, classification, shape |
| 객체 이동 | 같은 토픽 | 같은 메시지 | `action=MODIFY` |
| 객체 삭제 | 같은 토픽 | 같은 메시지 | `action=DELETE` |
| 전체 삭제 | 같은 토픽 | 같은 메시지 | `action=DELETEALL` |

기본 RViz 설정에서 Bus와 Pedestrian의 초기 속도는 0 m/s이고, Car는 3 m/s입니다.

### 5.2 가상 LiDAR 및 CPU 객체 검출

Perception 파티션의 `dummy_perception_publisher`는 `DummyObject`의 위치와 크기를
이용해 LiDAR 필드가 포함된 가상 Pointcloud만 생성합니다. 검출 객체를 직접
Planning에 주입하지 않습니다.

```text
/sensing/lidar/virtual/pointcloud_raw
  -> voxel_grid_downsample_filter_node
  -> /sensing/lidar/concatenated/pointcloud
  -> crop_box_filter_node
  -> /perception/obstacle_segmentation/pointcloud
  -> virtual_lidar_euclidean_cluster
  -> /perception/object_recognition/detection/labeled_clusters
```

`voxel_grid_downsample_filter_node`는 점 수를 줄이고,
`crop_box_filter_node`는 차량 자체 영역을 제거합니다.
`virtual_lidar_euclidean_cluster`는 GPU나 CUDA 없이 PCL 기반 CPU 군집화를
수행합니다.

실제 LiDAR 하드웨어 드라이버와 DNN 분류기를 실행하는 구성은 아닙니다. 따라서
RViz에서 Bus, Car, Pedestrian 도구를 사용해도 CPU 군집화 이후 객체 분류는
`UNKNOWN`이 됩니다. 현재 목적은 더미 검출 객체의 직통 전달이 아니라,
Pointcloud가 Sensing 전처리와 Perception 검출을 거쳐 Planning에 전달되는 흐름을
검증하는 것입니다.

### 5.3 Perception 내부 처리 순서

| 순서 | 노드 | 입력 | 출력 | 처리 내용 |
| --- | --- | --- | --- | --- |
| 1 | `dummy_perception_publisher` | `/simulation/dummy_perception_publisher/object_info` | `/sensing/lidar/virtual/pointcloud_raw` | 더미 객체 형상을 LiDAR 형식 Pointcloud로 변환 |
| 2 | `voxel_grid_downsample_filter_node` | `/sensing/lidar/virtual/pointcloud_raw` | `/sensing/lidar/concatenated/pointcloud` | CPU voxel downsample |
| 3 | `crop_box_filter_node` | `/sensing/lidar/concatenated/pointcloud` | `/perception/obstacle_segmentation/pointcloud` | 차량 자체 영역 제거 |
| 4 | `virtual_lidar_euclidean_cluster` | `/perception/obstacle_segmentation/pointcloud` | `.../detection/labeled_clusters` | CPU Euclidean 군집화 및 UNKNOWN 객체 생성 |
| 5 | `shape_estimation` | `.../detection/labeled_clusters` | `.../detection/objects_with_feature` | 클러스터에서 객체 형상 추정 |
| 6 | `detected_object_feature_remover` | `.../detection/objects_with_feature` | `.../detection/objects` | 특징 필드를 제거해 표준 `DetectedObjects` 생성 |
| 7 | `multi_object_tracker` | `.../detection/objects` | `.../tracking/objects` | 프레임 간 객체 ID, 위치, 속도를 추적 |
| 8 | `map_based_prediction` | `.../tracking/objects`, `/map/vector_map` | `/perception/object_recognition/objects` | 지도와 추적 결과를 이용해 객체의 예측 경로 생성 |

마지막 `PredictedObjects` 토픽이 Perception 파티션의 대표 객체 출력입니다.
Decision/Planning의 여러 플래너와 Control의 안전 감시 노드가 이 토픽을
구독합니다.

## 6. Perception에서 Decision/Planning까지

### 6.1 경로와 장애물 입력

목적지를 지정하면 Mission Planning이 전역 route를 만듭니다.

```text
/planning/mission_planning/goal
  -> Mission Planning
  -> /planning/mission_planning/route
```

RViz에서 장애물을 추가하거나 삭제해도 이 전역 route 자체가 새로 생성되는 것은
아닙니다. Decision/Planning은 같은 route 위에서 객체와 포인트클라우드를 보고
지역 path 및 속도가 포함된 trajectory를 계속 갱신합니다.

주요 Planning 입력은 다음과 같습니다.

| 입력 | 토픽 | 용도 |
| --- | --- | --- |
| 전역 route | `/planning/mission_planning/route` | 목적지까지 따라갈 차선 결정 |
| 예측 객체 | `/perception/object_recognition/objects` | 객체 위치, 종류, 속도와 예측 경로 판단 |
| 장애물 포인트클라우드 | `/perception/obstacle_segmentation/pointcloud` | 장애물 점군 기반 정지 및 안전 판단 |
| 차량 위치 및 속도 | `/localization/kinematic_state` | 현재 차량 상태 기준 계획 |
| 차량 가속도 | `/localization/acceleration` | 속도 계획과 smoothing |
| 지도 | `/map/vector_map` | 차선, 주행 가능 영역 및 규칙 판단 |

### 6.2 Decision/Planning 내부 처리 순서

| 순서 | 노드 | 주요 객체 입력 | 주요 출력 | 역할 |
| --- | --- | --- | --- | --- |
| 1 | `behavior_path_planner` | `PredictedObjects`, route, vector map, odometry | `behavior_planning/path_with_lane_id` | 차선 수준의 주행 path 결정 |
| 2 | `behavior_velocity_planner` | `PredictedObjects`, pointcloud, path, odometry | `behavior_planning/path` | 교차로, 횡단보도 등 행동 규칙에 따른 속도 및 정지 계획 |
| 3 | `path_smoother` / `path_optimizer` | behavior path | `path_optimizer/trajectory` | 기하학적으로 부드러운 기본 trajectory 생성 |
| 4 | `motion_velocity_planner` | `PredictedObjects`, pointcloud, trajectory, odometry | `motion_velocity_planner/trajectory` | 동적 장애물 정지, 차선 이탈 등 속도 제약 반영 |
| 5 | `obstacle_cruise_planner` | `PredictedObjects`, pointcloud, trajectory, odometry | `/planning/scenario_planning/lane_driving/trajectory` | 전방 장애물에 대한 감속, 정지 또는 추종 속도 반영 |
| 6 | `scenario_selector` | lane-driving trajectory | `.../scenario_selector/trajectory` | 차선 주행과 주차 시나리오 중 현재 trajectory 선택 |
| 7 | `velocity_smoother` | 선택된 trajectory, acceleration | `.../velocity_smoother/trajectory` | 속도, 가속도, jerk 제한을 만족하도록 평활화 |
| 8 | `planning_validator` | 평활화된 trajectory | `/planning/scenario_planning/trajectory` | 유효성을 검사한 최종 Control 입력 발행 |

표에서 `behavior_planning/...`과 `path_optimizer/...`는 Planning 내부 상대 토픽을
간단히 표시한 것입니다. 파티션 간 핵심 인터페이스는 다음 두 토픽입니다.

```text
Perception -> Decision/Planning
/perception/object_recognition/objects

Decision/Planning -> Control
/planning/scenario_planning/trajectory
```

### 6.3 이번 Bus 시험에서 정지한 이유

현재 기본 preset은 다음과 같습니다.

- `launch_static_obstacle_avoidance: true`
- `launch_dynamic_obstacle_avoidance: false`
- `motion_stop_planner_type: obstacle_cruise_planner`

그러나 실제 rosbag에서는 `static_obstacle_avoidance` 후보 path가 생성되지 않았고,
최종 trajectory의 전방 정지 거리가 약 30 m에서 약 19.3 m로 짧아졌습니다.
따라서 이번 시험에서 확인된 직접 원인은 차선 변경형 회피나 Control AEB가 아니라
Planning의 motion velocity/obstacle cruise 단계에서 반영된 정지 trajectory입니다.

현재 rosbag만으로는 `DynamicObstacleStopModule`과 `obstacle_cruise_planner` 중 어느
하위 모듈이 최종 정지점을 삽입했는지까지 확정할 수 없습니다. 이를 구분하려면
`/planning/scenario_planning/status/stop_reasons`와
`/planning/velocity_factors/motion_velocity_planner`를 함께 기록해 factor의 모듈
이름과 정지 위치를 확인해야 합니다.

단순히 `launch_static_obstacle_avoidance=true`인 것만으로 모든 장애물을 자동으로
우회하지는 않습니다. 회피 가능 여부는 장애물 위치와 크기, 인접 차선 및 drivable
area, 안전 여유 거리, 승인 상태, 각 회피 모듈 파라미터에 따라 달라집니다.

## 7. Decision/Planning에서 Control까지

### 7.1 Trajectory 추종

Control의 `trajectory_follower`는 다음 값을 함께 사용합니다.

| 입력 | 토픽 |
| --- | --- |
| 최종 기준 trajectory | `/planning/scenario_planning/trajectory` |
| 현재 위치 및 속도 | `/localization/kinematic_state` |
| 현재 조향각 | `/vehicle/status/steering_status` |
| 현재 가속도 | `/localization/acceleration` |
| 운전 모드 | `/system/operation_mode/state` |

이 노드는 trajectory의 위치, 자세, 속도와 현재 차량 상태의 오차를 계산해 조향 및
종방향 제어 명령을 만듭니다.

```text
trajectory_follower
  -> /control/trajectory_follower/control_cmd
  -> vehicle_cmd_gate
  -> /control/command/control_cmd
```

`vehicle_cmd_gate`는 Auto, External, Emergency 명령과 현재 운전 모드를 확인하고
실제로 차량에 보낼 최종 명령을 선택합니다.

Planning trajectory에 장애물 앞 0 m/s 정지점이 들어가면 longitudinal controller가
감속 명령을 만들고, 장애물이 삭제되어 전방 속도가 다시 양수가 되면 가속 명령을
만듭니다.

### 7.2 차량 시뮬레이터와 피드백

현재 Control 파티션은 실제 차량 인터페이스 대신 `simple_planning_simulator`를
실행합니다. 시뮬레이터의 주요 입출력은 다음과 같습니다.

| 방향 | 토픽 | 설명 |
| --- | --- | --- |
| Control -> Simulator | `/control/command/control_cmd` | 최종 조향 및 가감속 명령 |
| Control -> Simulator | `/control/command/gear_cmd` | 기어 명령 |
| Simulator -> Planning/Control | `/localization/kinematic_state` | 차량 pose, 속도 및 odometry |
| Simulator -> Planning/Control | `/localization/acceleration` | 차량 가속도 |
| Simulator -> Control | `/vehicle/status/velocity_status` | 차량 속도 보고 |
| Simulator -> Control | `/vehicle/status/steering_status` | 조향 상태 보고 |
| Simulator -> Control | `/vehicle/status/control_mode` | 제어 모드 보고 |
| Simulator -> 전체 시스템 | `/tf` | 차량 좌표계 위치 갱신 |

이 피드백 때문에 Planning은 움직인 차량의 새 위치를 기준으로 trajectory를 다시
계산하고, Control은 현재 상태와 목표 상태의 오차를 반복해서 줄입니다.

## 8. Control의 안전 감시 경로

Control에는 주 trajectory 추종과 별도로 AEB 및 충돌 검사 노드가 존재합니다.

```text
/perception/obstacle_segmentation/pointcloud
  -> autonomous_emergency_braking

/perception/object_recognition/objects
  -> collision_detector / predicted_path_checker 등
```

현재 AEB 파라미터는 `use_pointcloud_data=true`,
`use_predicted_object_data=false`입니다. 따라서 AEB는 `PredictedObjects`보다
포인트클라우드를 직접 사용하도록 설정되어 있습니다.

다만 확인한 rosbag에서는 AEB virtual wall이나 AEB metric이 발생하지 않았습니다.
이번 정지는 Control AEB가 직접 emergency stop을 건 것이 아니라, Planning에서
생성한 정지 trajectory를 Control이 정상 추종한 결과로 판단됩니다.

## 9. 실제 시험에서 확인된 이벤트

`dummy_obstacle_20260722_173416` rosbag에서 확인된 흐름은 다음과 같습니다.

| 시각(기록 시작 기준) | 이벤트 |
| --- | --- |
| 약 37.6초 | RViz에서 첫 Bus `ADD` |
| 약 47.5초 | Auto 전환 |
| 약 48.5초 | Control 주행 명령 시작 |
| 약 61.3초 | Planning의 정지 trajectory에 따라 Control 정지 명령 |
| 약 62.6초 | 차량 정지 확인 |
| 약 75.8초 | Bus `DELETEALL` |
| 약 77.0초 | 전방 trajectory가 열리며 Control 재출발 명령 |
| 약 82.8초 | 두 번째 Bus `ADD` |
| 약 84.9초 | 다시 정지 명령 |
| 약 89.4초 | Bus 삭제 |
| 약 90.5초 | 다시 출발 명령 |

같은 기록에서 최종 객체 토픽
`/perception/object_recognition/objects`는 총 1,136개 메시지 중 463개가 객체를
포함했고, 객체 분류는 Bus로 확인됐습니다. 이는 RViz 객체가 단순 화면 표시로
끝난 것이 아니라 Perception의 검출, 추적, 예측 단계를 거쳐 Planning 입력까지
도달했다는 근거입니다.

## 10. 확인 명령

세 파티션을 같은 `ROS_DOMAIN_ID`로 실행한 상태에서 다음 명령으로 각 경계를
확인할 수 있습니다.

```bash
# RViz -> Perception 입력
ros2 topic echo --once /simulation/dummy_perception_publisher/object_info

# Perception 중간 및 최종 출력
ros2 topic hz /perception/object_recognition/detection/objects
ros2 topic hz /perception/object_recognition/tracking/objects
ros2 topic hz /perception/object_recognition/objects

# Decision/Planning -> Control
ros2 topic hz /planning/scenario_planning/trajectory

# Control -> 차량 시뮬레이터
ros2 topic hz /control/command/control_cmd

# 차량 상태 피드백
ros2 topic hz /localization/kinematic_state
ros2 topic hz /vehicle/status/steering_status
```

토픽 연결 관계는 다음 명령으로 publisher와 subscriber까지 확인할 수 있습니다.

```bash
ros2 topic info -v /perception/object_recognition/objects
ros2 topic info -v /planning/scenario_planning/trajectory
ros2 topic info -v /control/command/control_cmd
```

rosbag으로 전체 흐름을 검증할 때는 최소한 다음 토픽을 포함합니다.

```text
/simulation/dummy_perception_publisher/object_info
/perception/object_recognition/detection/objects
/perception/object_recognition/tracking/objects
/perception/object_recognition/objects
/perception/obstacle_segmentation/pointcloud
/planning/mission_planning/route
/planning/scenario_planning/lane_driving/trajectory
/planning/scenario_planning/trajectory
/planning/scenario_planning/status/stop_reasons
/planning/velocity_factors/motion_velocity_planner
/control/trajectory_follower/control_cmd
/control/command/control_cmd
/localization/kinematic_state
/localization/acceleration
/vehicle/status/velocity_status
/vehicle/status/steering_status
```

## 11. 현재 구성을 결정하는 주요 파일

| 구분 | 파일 |
| --- | --- |
| Perception 실행 설정 | `src/universe/autoware.universe/obigo_launch/launch/sample_adsw_perception_run.launch.xml` |
| Perception 객체 처리 연결 | `src/universe/autoware.universe/obigo_launch/launch/components/perception_simulator_component.launch.xml` |
| 더미 객체 검출 토픽 | `src/universe/autoware.universe/simulator/autoware_dummy_perception_publisher/launch/dummy_perception_publisher.launch.xml` |
| Decision 실행 설정 | `src/universe/autoware.universe/obigo_launch/launch/sample_adsw_decision_run.launch.xml` |
| Planning 기본 preset | `src/universe/autoware.universe/obigo_launch/config/planning/preset/default_preset.yaml` |
| Control 실행 설정 | `src/universe/autoware.universe/obigo_launch/launch/sample_adsw_control_run.launch.xml` |
| 차량 시뮬레이터 토픽 | `src/universe/autoware.universe/simulator/autoware_simple_planning_simulator/launch/simple_planning_simulator.launch.py` |
