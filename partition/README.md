# Autoware 파티션 빌드 시스템

PC/보드에서 처음 빌드/실행하는 절차는 repo 루트의 `PARTITION_QUICKSTART.md`를 기준으로 합니다.

## 1. 개요

이 시스템은 Autoware의 방대한 소스 코드를 기능별 **파티션(Partition)**으로 나누어 모듈화된 Docker 이미지를 빌드하기 위해 설계되었습니다. 이 접근 방식은 전체 Autoware를 빌드하는 대신 필요한 패키지만 포함하는 경량 이미지를 생성하여, 배포를 단순화하고 이미지 크기를 줄이며 빌드 시간을 단축하는 이점을 제공합니다.

## 2. 사전 요구 사항

빌드 스크립트를 실행하기 전에 다음 도구가 시스템에 설치되어 있어야 합니다.

-   Docker 및 [Buildx](https://docs.docker.com/buildx/working-with-buildx/)
-   [jq](https://stedolan.github.io/jq/): 커맨드 라인 JSON 프로세서

### 멀티 플랫폼 빌드를 위한 추가 요구 사항

`--push` 옵션을 사용하여 멀티 플랫폼 이미지를 빌드하고 레지스트리로 푸시하려면, `docker-container` 드라이버를 사용하는 `buildx` 빌더가 설정되어 있어야 합니다. 이 드라이버는 QEMU를 통해 네이티브가 아닌 아키텍처의 빌드를 지원합니다.

다음 명령어를 사용하여 `docker-container` 드라이버 기반의 새로운 빌더를 생성하고 활성화할 수 있습니다.

```bash
# 새로운 빌더 생성
docker buildx create --name mybuilder --driver docker-container --use
```

## 3. 파티션 빌드 방법

### 1단계: 파티션 정의

새로운 파티션을 정의하려면 `partition/partition_config/` 디렉토리 내에 `.json` 파일을 생성합니다. 예를 들어, `my_perception_partition.json` 파일을 생성할 수 있습니다.

JSON 파일은 다음 두 개의 키를 가져야 합니다.

-   `packages`: 파티션에 포함할 ROS 2 패키지 이름의 배열입니다.
-   `folders`: 파티션에 포함할 추가적인 폴더 경로의 배열입니다.

**예시: `my_perception_partition.json`**

```json
{
    "packages": [
        "autoware_camera_lidar_calibrator",
        "autoware_image_projection_based_fusion",
        "autoware_pointcloud_preprocessor"
    ],
    "folders": [
        "src/universe/autoware.universe/perception"
    ]
}
```

### 2단계: 빌드 스크립트 실행

프로젝트 루트 디렉토리에서 `partition_build.sh` 스크립트를 실행하여 파티션을 빌드합니다.

#### 로컬 환경용 빌드 (단일 아키텍처)

현재 사용 중인 PC의 아키텍처에 맞는 이미지를 빌드하여 로컬 Docker 데몬으로 로드합니다.

```bash
./partition/partition_build.sh --repo <image-repo>
```

#### 멀티 아키텍처 이미지 빌드 및 푸시

`linux/amd64`와 `linux/arm64` 아키텍처 이미지를 모두 빌드하고, 이를 Manifest List로 묶어 지정된 registry로 푸시합니다. 이 방법을 사용하면 `docker pull` 명령 실행 시 클라이언트의 아키텍처에 맞는 이미지가 자동으로 다운로드됩니다.

```bash
./partition/partition_build.sh --repo <image-repo> --push
```

### 스크립트 옵션

-   `--repo <repo>`: (**필수**) 이미지 태그에 사용할 Docker image repository (예: `partition-test`, `myuser/autoware-custom`).
-   `--push`: 멀티 아키텍처 이미지를 빌드하고 레지스트리로 푸시합니다. 이 옵션을 생략하면 로컬 환경용 단일 아키텍처 이미지를 빌드합니다.
-   `--no-cuda`: CUDA 지원 없이 이미지를 빌드합니다.
-   `--help`: 도움말 메시지를 표시합니다.

## 4. 시스템 동작 원리

1.  `partition_build.sh` 스크립트는 `partition/partition_config` 디렉토리의 모든 `.json` 파일을 순회합니다.
2.  각 JSON 파일로부터 `packages`와 `folders` 목록을 파싱합니다.
3.  `Dockerfile.template` 파일의 플레이스홀더(`%COPY_LIST%`, `%BIND_LIST%`)를 파싱된 패키지 및 폴더 경로로 치환하여, 각 파티션에 대한 전용 `[partition_name]_Dockerfile`을 생성합니다.
4.  `docker buildx bake` 명령을 호출하여 생성된 Dockerfile과 `docker-bake.hcl` 설정에 따라 이미지를 빌드합니다.
5.  `--push` 옵션 사용 여부에 따라 `partition-multi-platform` 타겟(멀티 아키텍처) 또는 `partition` 타겟(단일 아키텍처)을 선택하여 빌드를 진행합니다.

## 5. 파티션 이미지 실행 및 활용

빌드된 파티션 이미지는 독립적으로 실행 가능한 컨테이너입니다.

```bash
./partition/partition_run.sh --rm --repo {repo} --tag {image tag} --exec-path ~/autoware_exec/ --map-path ~/autoware_map/sample-map-planning --no-nvidia
```

```bash
docker run -it --rm <image-repo>:<partition_name>
```

**중요**: 이 이미지는 정의한 패키지만 포함하고 있으므로, 내부의 노드들을 실행하려면 ROS 2의 launch 시스템을 사용해야 합니다.

### 노드 실행 방법

컨테이너 내부에서 `ros2 launch` 명령을 사용하여 원하는 노드를 실행할 수 있습니다.

```bash
# 컨테이너 내부에서 실행
source /opt/ros/humble/setup.bash
ros2 launch <package_in_your_partition> <launch_file.py>
```

### 권장 방식: 전용 Launch 패키지 구성

단순한 파티션이 아니라면, 파티션의 모든 노드를 체계적으로 실행하고 관리하기 위해 **전용 ROS 2 Launch 패키지를 구성하는 것을 강력히 권장합니다.**

1.  파티션의 실행 로직(노드 실행, 파라미터 설정 등)을 담은 top-level launch 파일을 포함하는 새로운 ROS 2 패키지를 생성합니다.
2.  이 launch 패키지의 이름을 파티션의 `.json` 설정 파일 내 `packages` 배열에 추가합니다.
3.  이렇게 하면 파티션 이미지에 launch 패키지가 포함되어, 컨테이너 내부에서 단일 명령으로 전체 파티션을 손쉽게 실행할 수 있습니다.

**전용 Launch 패키지 사용 예시:**

```bash
# 컨테이너 내부에서 실행
ros2 launch my_partition_launch top_level_launch.py
```

---

### 💡 팁: 의존성 에러 해결하기

파티션 빌드 중 `colcon build` 단계에서 특정 패키지를 찾을 수 없다는 의존성 에러가 발생할 수 있습니다. 이는 현재 파티션에 포함된 패키지들이 의존하는 다른 패키지가 파티션 구성에 누락되었기 때문입니다.

**해결 방법:**
1.  에러 메시지에서 찾을 수 없는 패키지 이름을 확인합니다.
2.  해당 파티션의 `.json` 설정 파일 (`partition/partition_config/`)을 엽니다.
3.  `packages` 배열에 누락된 패키지 이름을 추가합니다.
4.  스크립트를 다시 실행하여 빌드를 재시도합니다.
