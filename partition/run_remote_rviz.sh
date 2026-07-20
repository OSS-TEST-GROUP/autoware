#!/usr/bin/env bash

set -euo pipefail

REPO="${PARTITION_IMAGE_REPO:-}"
ROS_DOMAIN="${ROS_DOMAIN_ID:-42}"
NETWORK_INTERFACE=""
RVIZ_CONFIG="/opt/autoware/share/obigo_launch/rviz/autoware.rviz"
CONTAINER_NAME=""

print_help() {
    cat <<'EOF'
Usage: partition/run_remote_rviz.sh [OPTIONS]

Run only RViz2 on a desktop PC and connect to headless Autoware partitions.

Options:
  --repo <repo>             Docker image repo, or set PARTITION_IMAGE_REPO
  --domain-id <id>          ROS_DOMAIN_ID (default: 42)
  --network-interface <if>  Cyclone DDS network interface (e.g., enp3s0)
  --rviz-config <path>      RViz config path inside the image
  --help, -h                Show this help
EOF
}

while [ "${1:-}" != "" ]; do
    case "$1" in
    --repo)
        REPO="$2"
        shift
        ;;
    --domain-id)
        ROS_DOMAIN="$2"
        shift
        ;;
    --network-interface)
        NETWORK_INTERFACE="$2"
        shift
        ;;
    --rviz-config)
        RVIZ_CONFIG="$2"
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

if [ -z "$REPO" ]; then
    echo "Docker image repo is required." >&2
    echo "Use --repo <repo> or set PARTITION_IMAGE_REPO." >&2
    exit 1
fi

if [ -z "${DISPLAY:-}" ]; then
    echo "DISPLAY is not set. Run this script from the desktop GUI session." >&2
    exit 1
fi

if [ -n "$NETWORK_INTERFACE" ] && ! ip link show "$NETWORK_INTERFACE" >/dev/null 2>&1; then
    echo "Network interface does not exist: $NETWORK_INTERFACE" >&2
    exit 1
fi

CONTAINER_NAME="adsw-remote-rviz-$ROS_DOMAIN"

if docker ps -a --format '{{.Names}}' | grep -Fxq "$CONTAINER_NAME"; then
    docker rm -f "$CONTAINER_NAME" >/dev/null
fi

X_ARGS=(
    -e "DISPLAY=$DISPLAY"
    -e "QT_X11_NO_MITSHM=1"
    -v /tmp/.X11-unix/:/tmp/.X11-unix
)

if [ -n "${XAUTHORITY:-}" ] && [ -f "$XAUTHORITY" ]; then
    X_ARGS+=(-e "XAUTHORITY=$XAUTHORITY" -v "$XAUTHORITY:$XAUTHORITY:ro")
fi

if [ -n "${XDG_RUNTIME_DIR:-}" ] && [ -d "$XDG_RUNTIME_DIR" ]; then
    X_ARGS+=(-e "XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR" -v "$XDG_RUNTIME_DIR:$XDG_RUNTIME_DIR")
fi

DEVICE_ARGS=()
if [ -d /dev/dri ]; then
    DEVICE_ARGS+=(--device /dev/dri:/dev/dri)
fi

DDS_ARGS=(
    -e "RMW_IMPLEMENTATION=rmw_cyclonedds_cpp"
    -e "ROS_LOCALHOST_ONLY=0"
)

if [ -n "$NETWORK_INTERFACE" ]; then
    CYCLONEDDS_CONFIG="<CycloneDDS><Domain><General><Interfaces><NetworkInterface name=\"$NETWORK_INTERFACE\" multicast=\"true\"/></Interfaces><AllowMulticast>true</AllowMulticast></General></Domain></CycloneDDS>"
    DDS_ARGS+=(-e "CYCLONEDDS_URI=$CYCLONEDDS_CONFIG")
elif [ -n "${CYCLONEDDS_URI:-}" ]; then
    DDS_ARGS+=(-e "CYCLONEDDS_URI=$CYCLONEDDS_URI")
fi

if command -v xhost >/dev/null 2>&1; then
    xhost "+si:localuser:$(id -un)" >/dev/null || true
fi

echo "Repo: $REPO"
echo "ROS_DOMAIN_ID: $ROS_DOMAIN"
echo "DDS interface: ${NETWORK_INTERFACE:-auto}"
echo "RViz config: $RVIZ_CONFIG"

docker run -it --rm \
    --name "$CONTAINER_NAME" \
    --net=host \
    --ipc=host \
    -e "LOCAL_UID=$(id -u)" \
    -e "LOCAL_GID=$(id -g)" \
    -e "LOCAL_USER=$(id -un)" \
    -e "LOCAL_GROUP=$(id -gn)" \
    -e "ROS_DOMAIN_ID=$ROS_DOMAIN" \
    -e "FASTDDS_BUILTIN_TRANSPORTS=UDPv4" \
    "${DDS_ARGS[@]}" \
    "${X_ARGS[@]}" \
    "${DEVICE_ARGS[@]}" \
    "${REPO}:sample-adsw-perception" \
    rviz2 -d "$RVIZ_CONFIG"
