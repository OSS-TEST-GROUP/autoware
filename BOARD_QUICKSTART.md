# Board Quickstart

새 보드에서 소스를 받고, ARM64 + NVIDIA GPU 환경으로 빌드/실행하는 최소 절차입니다.

## 1. 소스 받기

```bash
mkdir -p ~/oss
cd ~/oss
git clone https://gitlab.lotte-autops.com/oss_group1/oss_adsw.git
cd oss_adsw
```

필요 패키지가 없으면 설치합니다.

```bash
sudo apt update
sudo apt install -y git python3-vcstool
```

## 2. 보드 환경 확인

```bash
uname -m
nvidia-smi
```

`uname -m`이 `aarch64`이면 빌드 플랫폼은 `linux/arm64`입니다.

## 3. Docker GPU 설정

```bash
sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

GPU가 컨테이너에서 보이는지 확인합니다.

```bash
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi
```

## 4. CUDA 이미지 빌드

```bash
./partition/partition_build.sh \
  --repo junohb/autoware-partition \
  --platform linux/arm64
```

CUDA를 쓰지 않을 때만 아래처럼 빌드합니다.

```bash
./partition/partition_build.sh \
  --repo junohb/autoware-partition \
  --platform linux/arm64 \
  --no-cuda
```

## 5. 실행

CUDA 이미지로 실행할 때는 `--no-nvidia`를 붙이지 않습니다.

컨테이너 셸만 열기:

```bash
./partition/partition_run.sh \
  --rm \
  --repo junohb/autoware-partition \
  --tag adsw-control \
  --exec-path ~/autoware_exec \
  --map-path ~/autoware_map/sample-map-planning \
  /bin/bash
```

Control 실행:

```bash
./partition/partition_run.sh \
  --rm \
  --repo junohb/autoware-partition \
  --tag adsw-control \
  --exec-path ~/autoware_exec \
  --map-path ~/autoware_map/sample-map-planning \
  /autoware/start_script/adsw-control.sh
```

Decision 실행:

```bash
./partition/partition_run.sh \
  --rm \
  --repo junohb/autoware-partition \
  --tag adsw-decision \
  --exec-path ~/autoware_exec \
  --map-path ~/autoware_map/sample-map-planning \
  /autoware/start_script/adsw-decision.sh
```

Perception 실행:

```bash
./partition/partition_run.sh \
  --rm \
  --repo junohb/autoware-partition \
  --tag adsw-perception \
  --exec-path ~/autoware_exec \
  --map-path ~/autoware_map/sample-map-planning \
  /autoware/start_script/adsw-perception.sh
```

`--no-cuda`로 빌드한 이미지는 실행할 때 `--no-nvidia`를 붙입니다.

```bash
./partition/partition_run.sh \
  --rm \
  --repo junohb/autoware-partition \
  --tag adsw-control \
  --exec-path ~/autoware_exec \
  --map-path ~/autoware_map/sample-map-planning \
  --no-nvidia \
  /autoware/start_script/adsw-control.sh
```

실행 중지:

```bash
Ctrl+C
```

다시 실행:

위의 Control/Decision/Perception 실행 명령을 그대로 다시 실행합니다.

다른 터미널에서 멈출 때:

```bash
docker ps
docker stop <container_id>
```

## 6. 태그 규칙

CUDA 빌드:

```text
adsw-control-cuda
adsw-decision-cuda
adsw-perception-cuda
```

No CUDA 빌드:

```text
adsw-control
adsw-decision
adsw-perception
```

`partition_run.sh`는 `--no-nvidia`가 없으면 자동으로 `-cuda` 태그를 사용합니다.
