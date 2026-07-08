# Autoware Partition Handoff

## 목표

이 프로젝트는 Autoware를 3개 파티션 Docker 이미지로 나눠 실행하는 테스트 프로젝트다.

최종 목표는 다음 흐름이 수동 topic pub 없이 동작하는 것이다.

1. perception / decision / control 파티션 Docker 컨테이너 실행
2. 각 컨테이너에서 top-level launch 하나씩 실행
3. RViz2에서 2D Pose Estimate 선택
4. RViz2에서 2D Goal Pose 선택
5. Route 생성
6. Auto 클릭
7. planning simulator lane driving scenario에서 ego vehicle 주행

이 테스트는 실제 센서 기반 주행이 아니라 planning simulator 기반 테스트다.

참고 문서:
- GOASP-[08] Autoware Partition-160125-085024.pdf
- 문서 기준 파티션 구성:
  - Perception Part: Perception, Sensing, Localization, Map, RViz2
  - Control Part: Control, VehicleInterface, Simulator, ADApi
  - Decision Part: Planning, System
- 문서 기준 테스트 시나리오:
  - planning simulation의 차선 주행 시나리오, Lane driving scenario

## 현재 프로젝트 경로

프로젝트 루트:

~/oss/oss_adsw

주요 파일:

partition/partition_config/sample-adsw-perception.json
partition/partition_config/sample-adsw-decision.json
partition/partition_config/sample-adsw-control.json

src/universe/autoware.universe/obigo_launch/launch/adsw_perception.launch.xml
src/universe/autoware.universe/obigo_launch/launch/adsw_decision.launch.xml
src/universe/autoware.universe/obigo_launch/launch/adsw_control.launch.xml

## 현재 파티션 구성 상태

현재 partition_config 기준으로 중요한 패키지는 어느 정도 들어가 있다.

Perception partition:
- obigo_launch
- autoware_launch
- perception_simulator_launch
- autoware_dummy_perception_publisher
- tier4_localization_launch
- tier4_map_launch
- tier4_perception_launch
- tier4_sensing_launch
- autoware_probabilistic_occupancy_grid_map
- perception / sensing / localization / map 관련 폴더

Decision partition:
- obigo_launch
- autoware_launch
- tier4_planning_launch
- tier4_system_launch
- tier4_autoware_api_launch
- planning / system 관련 폴더

Control partition:
- obigo_launch
- autoware_launch
- tier4_control_launch
- tier4_vehicle_launch
- tier4_simulator_launch
- tier4_autoware_api_launch
- autoware_simple_planning_simulator
- autoware_default_adapi
- autoware_adapi_adaptors
- autoware_vehicle_door_simulator
- control / vehicle 관련 폴더

따라서 현재 문제는 패키지가 전혀 없는 문제가 아니라, launch/runtime wiring이 정리되지 않은 문제로 본다.

## 이전 디버깅에서 확인한 이슈

### 1. RViz 초기 pose 토픽 문제

RViz의 2D Pose Estimate가 기본적으로 /initialpose로 나갔다.

하지만 simple_planning_simulator는 /initialpose3d를 구독한다.

그래서 매번 RViz Tool Properties에서 /initialpose3d로 바꿔야 했다.

최종 수정 필요:
- RViz 설정에서 2D Pose Estimate 토픽을 /initialpose3d로 고정하거나
- launch/remap으로 /initialpose를 /initialpose3d로 연결해야 한다.

### 2. ADAPI 누락 또는 중복 문제

RViz Auto / operation mode UI를 위해 ADAPI가 필요했다.

이전에 tier4_autoware_api_component.launch.xml를 임시로 추가했지만, 한 번은 중복 include되어 ADAPI 노드가 여러 개 떴다.

중복 증상:
- /adapi/container 2개
- /adapi/node/operation_mode 4개
- /adapi/node/vehicle_door 4개

최종 수정 필요:
- ADAPI는 정확히 한 번만 실행되어야 한다.
- 어느 파티션이 ADAPI를 담당할지 명확히 정해야 한다.
- 문서 구조상 Control Part에 ADApi가 포함되어 있으므로 control 쪽을 우선 검토한다.
- 중복 실행 금지.

### 3. control launch에서 simulator 누락

처음에는 control launch에서 simple_planning_simulator가 자연스럽게 실행되지 않았다.

그래서 /localization/kinematic_state가 없거나 차량 pose가 갱신되지 않았다.

이전에 임시로 adsw_control.launch.xml에 launch_simulator 옵션과 planning_simulator.launch.xml include를 넣었다.

최종 수정 필요:
- control partition launch에서 planning simulator가 자연스럽게 실행되어야 한다.
- 사용자가 별도로 simulator 관련 topic pub를 하면 안 된다.

### 4. localization initialization state 문제

/localization/initialization_state publisher가 없어서 RViz Localization 상태가 Unknown에 머물렀다.

임시로 state: 3을 publish해서 넘겼지만, 최종 구조에서는 수동 topic pub를 쓰면 안 된다.

최종 수정 필요:
- simulator/localization launch에서 자연스럽게 처리되게 하거나
- 필요한 경우 obigo_launch 내부 helper node로 처리하되 수동 명령은 없애야 한다.

### 5. planning이 perception output을 기다리던 문제

Route는 생성되었다.

확인된 토픽:
- /planning/mission_planning/route

하지만 planning이 아래에서 멈췄다.
- waiting for dynamic_object
- waiting for occupancy_grid

임시로 아래 토픽을 publish하니 trajectory가 생성됐다.
- /perception/object_recognition/objects
- /perception/occupancy_grid_map/map

최종 수정 필요:
- 실제 센서 테스트가 아니므로 perception_simulator_launch 또는 autoware_dummy_perception_publisher를 사용해야 한다.
- 수동 empty object / empty occupancy grid publisher는 최종 해결책이 아니다.

### 6. /system/operation_mode/availability 없음

/system/operation_mode/state는 있었지만 /system/operation_mode/availability publisher가 없었다.

ADAPI operation_mode 노드는 둘 다 구독한다.
- /system/operation_mode/state
- /system/operation_mode/availability

availability가 없어서 /api/operation_mode/state에서 autonomous available이 false였다.

최종 수정 필요:
- system/control/adapi launch 구성을 통해 availability가 자연스럽게 나와야 한다.
- 수동 topic pub 금지.

### 7. Auto 전환 문제

/api/operation_mode/change_to_autonomous 서비스를 수동 호출하면 성공했고 mode: 2가 되었다.

즉 operation mode 전환 자체는 가능했다.

최종 목표:
- RViz Auto 버튼만 눌러도 자연스럽게 mode: 2로 전환되어야 한다.

### 8. vehicle_cmd_gate가 control command를 막던 문제

/controller raw output은 나왔다.
- /control/trajectory_follower/control_cmd

하지만 최종 command는 처음에 안 나왔다.
- /control/command/control_cmd

원인은 vehicle_cmd_gate가 pause/stop 상태였기 때문이다.

확인된 상태:
- /control/vehicle_cmd_gate/is_paused true
- /system/fail_safe/mrm_state publisher 없음

임시로 mrm_state NORMAL/NONE을 publish하고 set_stop false, set_pause false를 호출하니 /control/command/control_cmd가 33Hz로 나왔다.

최종 수정 필요:
- vehicle_cmd_gate가 매번 수동 set_pause/set_stop 없이 정상 동작해야 한다.
- fail-safe / mrm / system 관련 launch 구성을 검토해야 한다.
- 수동 topic pub나 강제 service call에 의존하면 안 된다.

### 9. control_cmd는 나오는데 simulator 차량이 안 움직임

/control/command/control_cmd는 33Hz로 나왔다.

하지만 /localization/kinematic_state의 x/y 좌표가 고정이었다.

simple_planning_simulator 구독 토픽:
- /control/command/control_cmd
- /control/command/gear_cmd
- /initialpose3d
- /planning/scenario_planning/trajectory
- /vehicle/engage
- /vehicle/command/manual_control_cmd
- /vehicle/command/manual_gear_command

simple_planning_simulator 발행 토픽:
- /localization/kinematic_state
- /vehicle/status/velocity_status
- /vehicle/status/gear_status
- /vehicle/status/control_mode

한때 /vehicle/engage publisher가 없었다.

최종 수정 필요:
- simple_planning_simulator가 자연스럽게 engage / gear / control mode 조건을 만족해야 한다.
- 수동 /vehicle/engage true publish는 상태를 꼬이게 만들 수 있으므로 최종 방식으로 쓰면 안 된다.

### 10. 수동 topic pub 때문에 Stop/Auto 상태가 꼬임

아래 topic들을 강제로 publish하니 RViz Stop을 눌러도 다시 Auto/Moving으로 돌아가는 문제가 생겼다.
- /autoware/engage
- /vehicle/engage
- /system/operation_mode/availability
- /system/fail_safe/mrm_state

최종 원칙:
- 런타임 수동 ros2 topic pub 금지
- 컨테이너 안 임시 수정 금지
- 소스 수정 후 이미지 재빌드
- 파티션별 top-level launch로 해결

## 원하는 최종 실행 형태

Perception container:

source /opt/autoware/setup.bash
ros2 launch obigo_launch sample_adsw_perception_run.launch.xml map_path:=/autoware_map

Decision container:

source /opt/autoware/setup.bash
ros2 launch obigo_launch sample_adsw_decision_run.launch.xml map_path:=/autoware_map

Control container:

source /opt/autoware/setup.bash
ros2 launch obigo_launch sample_adsw_control_run.launch.xml map_path:=/autoware_map

RViz 조작:
1. 2D Pose Estimate
2. 2D Goal Pose
3. Auto

기대 결과:
- route 생성
- trajectory 생성
- /control/command/control_cmd 생성
- /localization/kinematic_state 갱신
- RViz ego vehicle 이동

## Codex 작업 요청

먼저 파일을 수정하지 말고 현재 repo를 분석하라.

분석할 항목:
1. 현재 perception / decision / control launch가 각각 무엇을 include하는지
2. ADAPI가 어느 파티션에서 몇 번 실행되는 구조인지
3. simple_planning_simulator가 어디서 실행되는지
4. /initialpose3d 설정이 어디서 처리되는지
5. planning simulator lane driving에 필요한 topic 중 natural publisher가 없는 것이 무엇인지
6. 기존 패키지 include만으로 해결 가능한지, helper node/wrapper launch가 필요한지

그 다음 수정 계획을 제안하라.

수정 방향:
1. obigo_launch 아래에 파티션별 wrapper launch 추가 가능
2. RViz initial pose topic을 /initialpose3d로 고정
3. ADAPI 중복 실행 방지
4. simulator는 control part에서 자연스럽게 실행
5. perception simulator 또는 dummy perception publisher를 perception part에서 자연스럽게 실행
6. system/fail-safe/operation_mode availability 문제는 올바른 launch include로 해결
7. 수동 ros2 topic pub를 요구하지 말 것
8. 수정은 컨테이너 안이 아니라 source tree에 반영
9. 수정 후 partition image rebuild 명령 제공
10. 최종 docker 실행 및 launch 명령 제공
11. 검증 명령과 기대 출력 제공
EOF