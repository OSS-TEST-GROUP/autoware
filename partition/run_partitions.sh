#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(readlink -f "$(dirname "$0")")
WORKSPACE_ROOT=$(readlink -f "$SCRIPT_DIR/..")

REPO="${PARTITION_IMAGE_REPO:-}"
MAP_PATH="$HOME/autoware_map/sample-map-planning"
ROS_DOMAIN="${ROS_DOMAIN_ID:-42}"
START_DELAY=10
HOST_SOURCE_DIR="${HOST_SOURCE_DIR:-$HOME/source}"
LOG_DIR="$WORKSPACE_ROOT/log"

print_help() {
    cat <<'EOF'
Usage: partition/run_partitions.sh [OPTIONS]

Options:
  --repo <repo>          Docker image repo, or set PARTITION_IMAGE_REPO
  --map-path <path>      Host map path (default: ~/autoware_map/sample-map-planning)
  --domain-id <id>       ROS_DOMAIN_ID (default: 42)
  --delay <sec>          Delay between partitions (default: 10)
  --help, -h             Show this help

Logs are written under /workspace/log inside each container.
On the host this is the repo log/ directory.
EOF
}

while [ "${1:-}" != "" ]; do
    case "$1" in
    --repo)
        REPO="$2"
        shift
        ;;
    --map-path)
        MAP_PATH="$2"
        shift
        ;;
    --domain-id)
        ROS_DOMAIN="$2"
        shift
        ;;
    --delay)
        START_DELAY="$2"
        shift
        ;;
    --help | -h)
        print_help
        exit 0
        ;;
    *)
        echo "Unknown option: $1" >&2
        print_help
        exit 1
        ;;
    esac
    shift
done

if [ ! -d "$MAP_PATH" ]; then
    echo "Map path does not exist: $MAP_PATH" >&2
    exit 1
fi

if [ -z "$REPO" ]; then
    echo "Docker image repo is required." >&2
    echo "Use --repo <repo> or set PARTITION_IMAGE_REPO." >&2
    exit 1
fi

mkdir -p "$LOG_DIR" "$HOST_SOURCE_DIR/fastdds" "$HOST_SOURCE_DIR/ros2"
: >"$LOG_DIR/perception_log.txt"
: >"$LOG_DIR/decision_log.txt"
: >"$LOG_DIR/control_log.txt"

X_ARGS=()
if [ -n "${DISPLAY:-}" ]; then
    X_ARGS=(-e "DISPLAY=$DISPLAY" -v /tmp/.X11-unix/:/tmp/.X11-unix)
    if command -v xhost >/dev/null 2>&1; then
        xhost + >/dev/null || true
    fi
fi

COMMON_ARGS=(
    --rm
    --net=host
    --pid=host
    --ipc=host
    -e "LOCAL_UID=$(id -u)"
    -e "LOCAL_GID=$(id -g)"
    -e "LOCAL_USER=$(id -un)"
    -e "LOCAL_GROUP=$(id -gn)"
    -e "FASTDDS_BUILTIN_TRANSPORTS=UDPv4"
    -e "ROS_DOMAIN_ID=$ROS_DOMAIN"
    -e "XAUTHORITY=${XAUTHORITY:-}"
    -e "XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-}"
    -v /etc/localtime:/etc/localtime:ro
    -v "$WORKSPACE_ROOT:/workspace"
    -v "$MAP_PATH:/autoware_map:ro"
    -v "$HOST_SOURCE_DIR/fastdds:/fastdds:rw"
    -v "$WORKSPACE_ROOT:/exec"
    -v "$HOST_SOURCE_DIR/ros2:/ros2"
)

CONTAINERS=(
    "adsw-perception-$ROS_DOMAIN"
    "adsw-decision-$ROS_DOMAIN"
    "adsw-control-$ROS_DOMAIN"
)

cleanup() {
    echo
    echo "Stopping partition containers..."
    docker stop "${CONTAINERS[@]}" >/dev/null 2>&1 || true
}
trap cleanup INT TERM EXIT

remove_stale_container() {
    local name="$1"
    if docker ps -a --format '{{.Names}}' | grep -Fxq "$name"; then
        echo "Removing stale container: $name"
        docker rm -f "$name" >/dev/null
    fi
}

start_partition() {
    local label="$1"
    local name="$2"
    local tag="$3"
    local script="$4"
    local log_file="$5"

    remove_stale_container "$name"

    echo "Starting $label: $REPO:${tag}"
    docker run -d \
        --name "$name" \
        "${COMMON_ARGS[@]}" \
        "${X_ARGS[@]}" \
        "$REPO:${tag}" \
        bash -lc "mkdir -p /workspace/log && $script > /workspace/log/$log_file 2>&1" >/dev/null
}

echo "Repo: $REPO"
echo "Map: $MAP_PATH"
echo "ROS_DOMAIN_ID: $ROS_DOMAIN"
echo "Delay: ${START_DELAY}s"
echo "CUDA: disabled"
echo "Logs: $LOG_DIR"
echo

start_partition "perception" "${CONTAINERS[0]}" "sample-adsw-perception" "/autoware/start_script/adsw-perception.sh" "perception_log.txt"
sleep "$START_DELAY"
start_partition "decision" "${CONTAINERS[1]}" "sample-adsw-decision" "/autoware/start_script/adsw-decision.sh" "decision_log.txt"
sleep "$START_DELAY"
start_partition "control" "${CONTAINERS[2]}" "sample-adsw-control" "/autoware/start_script/adsw-control.sh" "control_log.txt"

echo
echo "All partitions are running. Press Ctrl-C to stop them."
echo
tail -n +1 -F \
    "$LOG_DIR/perception_log.txt" \
    "$LOG_DIR/decision_log.txt" \
    "$LOG_DIR/control_log.txt"
