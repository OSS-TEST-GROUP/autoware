# Autoware Partition 실행 순서

이 문서는 새 환경에서 이 repo를 받은 뒤 perception / decision / control partition 이미지를 빌드하고, planning simulator lane driving 시나리오를 실행하는 순서다.

목표 흐름:

1. perception / decision / control Docker 이미지 빌드
2. partition 컨테이너 3개 실행
3. 각 컨테이너에서 top-level launch 1개씩 실행
4. RViz2에서 2D Pose Estimate, 2D Goal Pose 지정
5. Route 생성 확인
6. Auto 클릭
7. simple planning simulator 기반 ego vehicle 이동 확인

런타임에서 `ros2 topic pub`로 상태를 수동 보정하지 않는다.

## 0. 전제

Ubuntu 환경에서 Docker가 설치되어 있고, 현재 사용자가 Docker를 실행할 수 있어야 한다.

필요 도구:

```bash
sudo apt update
sudo apt install -y git git-lfs python3-vcstool jq
```

Docker buildx 확인:

```bash
docker buildx version
```

X11 RViz 실행을 위해 로컬 GUI 환경에서 실행한다. 원격 접속 환경이면 `DISPLAY`와 X11 forwarding이 먼저 정상이어야 한다.

## 1. Repo 준비

```bash
mkdir -p ~/oss
cd ~/oss
git clone <repo-url> oss_adsw
cd ~/oss/oss_adsw
```

브랜치가 따로 있으면 전환한다.

```bash
git checkout <branch-name>
```

`partition_config`에는 아래 세 파일만 빌드 대상으로 있어야 한다.

```bash
find partition/partition_config -maxdepth 1 -type f -name '*.json' -printf '%f\n' | sort
```

기대 출력:

```text
sample-adsw-control.json
sample-adsw-decision.json
sample-adsw-perception.json
```

## 2. 맵 준비

실행 시 map directory가 컨테이너의 `/autoware_map`에 read-only로 마운트된다.

예시 경로:

```bash
MAP_PATH=~/autoware_map/sample-map-planning
```

맵 폴더에는 최소한 아래 파일들이 있어야 한다.

```text
lanelet2_map.osm
pointcloud_map.pcd
map_projector_info.yaml
pointcloud_map_metadata.yaml
```

확인:

```bash
ls -al "$MAP_PATH"
```

`/path/to/your/map` 같은 placeholder 경로를 그대로 쓰면 안 된다.

## 3. partition_run.sh 고정 마운트 경로 확인

현재 `partition/partition_run.sh`에는 아래 host path가 추가 마운트된다.

```text
/home/junohb/source/fastdds
/home/junohb/source/ros2
```

새 환경에서 같은 경로가 없다면 우선 디렉터리를 만든다.

```bash
mkdir -p /home/junohb/source/fastdds
mkdir -p /home/junohb/source/ros2
```

사용자명이 `junohb`가 아니라면 `partition/partition_run.sh`의 해당 경로를 현재 환경에 맞게 수정한다.

## 4. 이미지 빌드

CUDA 없이 amd64 기준으로 빌드:

```bash
cd ~/oss/oss_adsw

./partition/partition_build.sh \
  --repo junohb/autoware-partition \
  --no-cuda \
  --platform linux/amd64
```

빌드가 끝나면 아래 태그가 있어야 한다.

```bash
docker images | grep 'junohb/autoware-partition'
```

기대 태그:

```text
junohb/autoware-partition:sample-adsw-perception
junohb/autoware-partition:sample-adsw-decision
junohb/autoware-partition:sample-adsw-control
```

## 5. 실행 방법 A: 컨테이너 열고 내부에서 launch

터미널 3개를 연다.

공통 변수:

```bash
cd ~/oss/oss_adsw
MAP_PATH=~/autoware_map/sample-map-planning
REPO=junohb/autoware-partition
```

### 5.1 Perception 컨테이너

터미널 1:

```bash
./partition/partition_run.sh --rm --no-nvidia \
  --repo "$REPO" \
  --tag sample-adsw-perception \
  --map-path "$MAP_PATH"
```

컨테이너 안:

```bash
source /opt/autoware/setup.bash
ros2 launch obigo_launch sample_adsw_perception_run.launch.xml map_path:=/autoware_map
```

이 launch에서 RViz2가 뜬다.

### 5.2 Decision 컨테이너

터미널 2:

```bash
./partition/partition_run.sh --rm --no-nvidia \
  --repo "$REPO" \
  --tag sample-adsw-decision \
  --map-path "$MAP_PATH"
```

컨테이너 안:

```bash
source /opt/autoware/setup.bash
ros2 launch obigo_launch sample_adsw_decision_run.launch.xml map_path:=/autoware_map
```

### 5.3 Control 컨테이너

터미널 3:

```bash
./partition/partition_run.sh --rm --no-nvidia \
  --repo "$REPO" \
  --tag sample-adsw-control \
  --map-path "$MAP_PATH"
```

컨테이너 안:

```bash
source /opt/autoware/setup.bash
ros2 launch obigo_launch sample_adsw_control_run.launch.xml map_path:=/autoware_map
```

## 6. 실행 방법 B: 컨테이너 실행과 launch를 한 줄로 실행

터미널 3개에서 각각 실행한다.

공통 변수:

```bash
cd ~/oss/oss_adsw
MAP_PATH=~/autoware_map/sample-map-planning
REPO=junohb/autoware-partition
```

Perception:

```bash
./partition/partition_run.sh --rm --no-nvidia \
  --repo "$REPO" \
  --tag sample-adsw-perception \
  --map-path "$MAP_PATH" \
  bash -lc 'source /opt/autoware/setup.bash && ros2 launch obigo_launch sample_adsw_perception_run.launch.xml map_path:=/autoware_map'
```

Decision:

```bash
./partition/partition_run.sh --rm --no-nvidia \
  --repo "$REPO" \
  --tag sample-adsw-decision \
  --map-path "$MAP_PATH" \
  bash -lc 'source /opt/autoware/setup.bash && ros2 launch obigo_launch sample_adsw_decision_run.launch.xml map_path:=/autoware_map'
```

Control:

```bash
./partition/partition_run.sh --rm --no-nvidia \
  --repo "$REPO" \
  --tag sample-adsw-control \
  --map-path "$MAP_PATH" \
  bash -lc 'source /opt/autoware/setup.bash && ros2 launch obigo_launch sample_adsw_control_run.launch.xml map_path:=/autoware_map'
```

## 7. RViz 조작

Perception launch에서 뜬 RViz2에서 진행한다.

1. 맵이 보이는지 확인한다.
2. `2D Pose Estimate`를 선택하고 차 위치를 찍는다.
3. `2D Goal Pose`를 선택하고 목표 지점을 찍는다.
4. Route가 생성되는지 확인한다.
5. `Auto`를 클릭한다.
6. ego vehicle이 움직이는지 확인한다.

RViz 2D Pose Estimate는 `/initialpose3d`로 설정되어 있어야 한다.

## 8. 검증 명령

아무 컨테이너에서 실행 가능하다.

```bash
source /opt/autoware/setup.bash
```

Map:

```bash
ros2 topic hz /map/vector_map_marker
ros2 topic hz /map/pointcloud_map
```

Route / trajectory:

```bash
ros2 topic hz /planning/mission_planning/route
ros2 topic hz /planning/scenario_planning/trajectory
```

Control:

```bash
ros2 topic hz /control/trajectory_follower/control_cmd
ros2 topic hz /control/command/control_cmd
```

Simulator localization:

```bash
ros2 topic hz /localization/kinematic_state
ros2 topic echo --once /localization/kinematic_state
```

ADAPI 중복 확인:

```bash
ros2 node list | grep -E 'adapi|operation_mode'
```

ADAPI는 중복으로 여러 partition에서 뜨면 안 된다.

## 9. 흔한 문제

### 맵이 안 보임

먼저 map path를 확인한다.

```bash
ls -al "$MAP_PATH"
```

컨테이너 안에서는:

```bash
ls -al /autoware_map
```

아래 에러가 있으면 map path가 잘못된 것이다.

```text
No map projector info files found
PCD load failed: /autoware_map/pointcloud_map.pcd
```

### tag가 없다고 나옴

현재 빌드 대상 파일명을 확인한다.

```bash
find partition/partition_config -maxdepth 1 -type f -name '*.json' -printf '%f\n' | sort
```

파일명이 곧 Docker tag가 된다.

```text
sample-adsw-perception.json -> sample-adsw-perception
sample-adsw-decision.json   -> sample-adsw-decision
sample-adsw-control.json    -> sample-adsw-control
```

### RViz가 안 뜸

Host에서 `DISPLAY`를 확인한다.

```bash
echo "$DISPLAY"
xhost +
```

그 뒤 perception 컨테이너를 다시 실행한다.

### route는 생기는데 Auto가 비활성화됨

Decision / control 로그에서 아래 대기 메시지를 확인한다.

```text
waiting for dynamic_object
waiting for occupancy_grid
trajectory has not received
control_cmd has not received
```

이 프로젝트의 최종 원칙은 런타임 `ros2 topic pub`로 임시 보정하지 않는 것이다. 문제가 있으면 launch/source 설정을 수정하고 이미지를 다시 빌드한다.

## 10. 종료

각 launch 터미널에서 `Ctrl-C`로 종료한다.

남은 컨테이너 확인:

```bash
docker ps
```

필요하면 컨테이너를 종료한다.

```bash
docker stop <container-id>
```

