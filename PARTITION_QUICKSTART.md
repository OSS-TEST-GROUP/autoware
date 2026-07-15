# Partition Quickstart

PC와 보드에서 Autoware partition 이미지를 빌드하고 실행하는 공통 절차입니다.  
현재 기본 실행은 CUDA를 사용하지 않습니다.

## 1. Repo 받기

```bash
sudo apt update
sudo apt install -y git git-lfs python3-vcstool jq

mkdir -p ~/oss
cd ~/oss
git clone <repo-url> oss_adsw
cd ~/oss/oss_adsw
```

## 2. 환경 변수 정하기

Docker image repo 이름은 직접 정합니다.  
로컬에서만 쓸 거면 임의 이름을 써도 되고, Docker Hub에 push할 거면 `<dockerhub-id>/<repo-name>` 형식으로 씁니다.

```bash
REPO=<image-repo>
MAP_PATH=~/autoware_map/sample-map-planning
```

예시:

```bash
REPO=partition-test
REPO=mydockerid/partition-test
```

플랫폼은 실행 환경에 맞게 하나만 선택합니다.

PC:

```bash
PLATFORM=linux/amd64
```

ARM64 보드:

```bash
PLATFORM=linux/arm64
```

현재 장비가 ARM64인지 확인:

```bash
uname -m
```

`aarch64`이면 `PLATFORM=linux/arm64`를 사용합니다.

## 3. 맵 데이터 위치

맵은 host의 `MAP_PATH` 위치에 둡니다.

```bash
ls -al "$MAP_PATH"
```

최소 파일:

```text
lanelet2_map.osm
pointcloud_map.pcd
map_projector_info.yaml
pointcloud_map_metadata.yaml
```

컨테이너 안에서는 이 폴더가 `/autoware_map`으로 마운트됩니다.

## 4. Docker 확인

```bash
docker --version
docker buildx version
```

## 5. 빌드

No CUDA 이미지로 빌드합니다.

```bash
cd ~/oss/oss_adsw

./partition/partition_build.sh \
  --repo "$REPO" \
  --platform "$PLATFORM" \
  --no-cuda
```

빌드 결과 확인:

```bash
docker images | grep "$REPO"
```

생성되는 태그:

```text
sample-adsw-perception
sample-adsw-decision
sample-adsw-control
```

## 6. 실행

스크립트 실행 시 한 터미널에서 perception -> decision -> control 순서로 실행됩니다.
간격은 10초입니다.

```bash
cd ~/oss/oss_adsw

./partition/run_partitions.sh \
  --repo "$REPO" \
  --map-path "$MAP_PATH" \
  --domain-id 42
```

로그는 컨테이너 내부 기준 `/workspace/log`에 생성됩니다.  
Host에서는 repo의 `log/` 폴더입니다.

```text
log/perception_log.txt
log/decision_log.txt
log/control_log.txt
```

종료:

```bash
Ctrl-C
```

스크립트가 perception / decision / control 컨테이너를 같이 종료합니다.

## 7. RViz 조작

RViz는 perception partition에서 뜹니다.

1. 맵이 보이는지 확인합니다.
2. `2D Pose Estimate`로 초기 위치를 찍습니다.
3. `2D Goal Pose`로 목표 위치를 찍습니다.
4. route가 생성되면 `Auto`를 누릅니다.
5. 차량이 차선을 따라 이동하는지 확인합니다.

perception -> decision -> control 순서로 모두 실행 되는 것을 확인 후 pose를 찍어야 합니다.

## 8. 단일 partition 수동 실행

문제 확인이 필요하면 기존 `partition_run.sh`로 각각 실행할 수 있습니다.

Perception:

```bash
ROS_DOMAIN_ID=42 ./partition/partition_run.sh --rm --no-nvidia \
  --repo "$REPO" \
  --tag sample-adsw-perception \
  --map-path "$MAP_PATH" \
  /autoware/start_script/adsw-perception.sh
```

Decision:

```bash
ROS_DOMAIN_ID=42 ./partition/partition_run.sh --rm --no-nvidia \
  --repo "$REPO" \
  --tag sample-adsw-decision \
  --map-path "$MAP_PATH" \
  /autoware/start_script/adsw-decision.sh
```

Control:

```bash
ROS_DOMAIN_ID=42 ./partition/partition_run.sh --rm --no-nvidia \
  --repo "$REPO" \
  --tag sample-adsw-control \
  --map-path "$MAP_PATH" \
  /autoware/start_script/adsw-control.sh
```

## 9. 안정화 내용

현재 절차에는 PC와 보드 양쪽에서 같은 방식으로 쓰기 위해 아래 보정이 반영되어 있습니다.

- CUDA 미사용: `--no-cuda` 빌드와 no-CUDA image tag만 사용합니다.
- SSH agent 없이 빌드 가능: `SSH_AUTH_SOCK`이 없을 때 BuildKit SSH forwarding을 생략합니다.
- 빌드 병렬도 제한: `COLCON_PARALLEL_WORKERS`와 `CMAKE_BUILD_PARALLEL_LEVEL` 기본값을 2로 낮춰 OOM 가능성을 줄였습니다.
- `FASTDDS_BUILTIN_TRANSPORTS=UDPv4`: multi-container에서 FastDDS shared memory 문제를 피합니다.
- `--pid=host --ipc=host`: launch process 이름과 shared memory가 컨테이너별로 꼬이는 문제를 줄입니다.
- `ROS_DOMAIN_ID=42`: host에 설치된 다른 ROS/Autoware 환경이나 이전 실행 잔여 daemon과 섞이지 않게 분리합니다.

## 10. 환경별 주의사항

PC:

- 보통 `PLATFORM=linux/amd64`를 사용합니다.
- RViz가 뜨려면 host의 `DISPLAY`가 정상이어야 합니다.

ARM64 보드:

- `uname -m`이 `aarch64`이면 `PLATFORM=linux/arm64`를 사용합니다.
- 빌드 중 OOM이 나면 swap을 확인합니다.

```bash
free -h
swapon --show
```

- 보드에 별도 Autoware/ROS가 설치되어 있으면 `ROS_DOMAIN_ID=42`처럼 domain을 분리해서 실행합니다.

## 11. 자주 본 문제

SSH agent 오류:

```text
invalid empty ssh agent socket
```

현재 빌드 스크립트는 `SSH_AUTH_SOCK`이 없으면 SSH forwarding 없이 빌드합니다.

RViz bus error:

보드에서 map marker 표시 중 RViz가 `Bus error`로 죽을 수 있습니다. 주행 자체와 별개로 visualization 쪽 문제일 수 있으므로 로그와 marker 설정을 분리해서 확인합니다.

Auto 버튼 비활성화:

먼저 `log/decision_log.txt`에서 route / trajectory / planner error를 확인합니다. `control`의 timeout은 대개 trajectory가 안 들어와서 생기는 결과입니다.

중복 노드 확인:

```bash
docker exec -it adsw-decision-42 bash -lc '
source /opt/autoware/setup.bash
ros2 node list | sort | uniq -d
'
```

## 12. CUDA 참고

현재는 CUDA 빌드와 CUDA 실행을 사용하지 않습니다.  
이 절차는 문제 재현이나 비교가 필요할 때만 참고합니다.

CUDA 빌드:

```bash
./partition/partition_build.sh \
  --repo "$REPO" \
  --platform "$PLATFORM"
```

생성되는 CUDA 태그:

```text
sample-adsw-perception-cuda
sample-adsw-decision-cuda
sample-adsw-control-cuda
```

CUDA runtime 확인이 필요할 때:

```bash
sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi
```

과거에 본 CUDA 관련 문제:

```text
pull access denied ... cuda-latest
```

CUDA 빌드에서는 `base-cuda` 이미지가 먼저 로컬에 있어야 합니다. 현재 빌드 스크립트는 CUDA 빌드 시 `base-cuda`도 같이 빌드하도록 보정되어 있습니다.

## 13. 참고

원본 가이드:

```text
GOASP-[08] Autoware Partition-160125-085024.pdf
```

원본 가이드는 PC 환경에서 Autoware partition feasibility를 검증한 문서이고, 이 문서는 PC/보드에서 실제 빌드/실행하면서 추가된 보정 사항까지 반영한 실행 절차입니다.
