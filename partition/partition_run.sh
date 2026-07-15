#!/usr/bin/env bash
# shellcheck disable=SC2086,SC2124

set -e

# Define terminal colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR=$(readlink -f "$(dirname "$0")")

WORKSPACE_ROOT="$SCRIPT_DIR/.."
source "$WORKSPACE_ROOT/amd64.env"
if [ "$(uname -m)" = "aarch64" ]; then
    source "$WORKSPACE_ROOT/arm64.env"
fi

# Default values
option_no_nvidia=false
option_devel=false
option_headless=false
MAP_PATH=""
WORKSPACE_PATH=""
USER_ID=""
WORKSPACE=""
DEFAULT_LAUNCH_CMD="ros2 launch autoware_launch autoware.launch.xml map_path:=/autoware_map vehicle_model:=sample_vehicle sensor_model:=sample_sensor_kit"
repo="ghcr.io/autowarefoundation/autoware"
RM=""   
DATA_PATH=""
EXEC_PATH=""
EXEC=""
HOST_SOURCE_DIR="${HOST_SOURCE_DIR:-$HOME/source}"

# Function to print help message
print_help() {
    echo -e "\n------------------------------------------------------------"
    echo -e "${RED}Note:${NC} The --map-path option is mandatory for the runtime. For development environment with shell access, use --devel option."
    echo -e "      Default launch command: ${GREEN}${DEFAULT_LAUNCH_CMD}${NC}"
    echo -e "------------------------------------------------------------"
    echo -e "${RED}Usage:${NC} run.sh [OPTIONS] [LAUNCH_CMD](optional)"
    echo -e "Options:"
    echo -e "  ${GREEN}--help/-h${NC}       Display this help message"
    echo -e "  ${GREEN}--map-path${NC}      Specify to mount map files into /autoware_map (mandatory for runtime)"
    echo -e "  ${GREEN}--devel${NC}         Launch the latest Autoware development environment with shell access"
    echo -e "  ${GREEN}--workspace${NC}     (--devel only)Specify the directory to mount into /workspace, by default it uses current directory (pwd)"
    echo -e "  ${GREEN}--no-nvidia${NC}     Disable NVIDIA GPU support"
    echo -e "  ${GREEN}--headless${NC}      Run Autoware in headless mode (default: false)"
    echo ""
}

# Parse arguments
parse_arguments() {
    while [ "$1" != "" ]; do
        case "$1" in
        --help | -h)
            print_help
            exit 1
            ;;
        --no-nvidia)
            option_no_nvidia=true
            ;;
        --devel)
            option_devel=true
            ;;
        --headless)
            option_headless=true
            ;;
        --rm)
            RM="--rm"    
            ;;
        --workspace)
            WORKSPACE_PATH="$2"
            shift
            ;;
        --map-path)
            MAP_PATH="$2"
            shift
            ;;
        --data-path)
            DATA_PATH="$2"
            shift
            ;;
        --exec-path)
            EXEC_PATH="$2"
            shift
            ;;  			            
        --pkg)
            package=-"$2"
            shift
            ;;
        --tag)
            tag="$2"
            shift
            ;;            
        --repo)
            repo="$2"
            shift
            ;;                        
        --*)
            echo "Unknown option: $1"
            print_help
            exit 1
            ;;
        -*)
            echo "Unknown option: $1"
            print_help
            exit 1
            ;;
        *)
            LAUNCH_CMD="$@"
            break
            ;;
        esac
        shift
    done
}

# Set the docker image and workspace variables
set_variables() {

    # Set image based on option
    IMAGE="${repo}:${tag}"
    #IMAGE="ghcr.io/autowarefoundation/autoware:${tag}"
    #IMAGE="obigo:${tag}"

    # Set workspace path, if not provided use the current directory
    if [ "$WORKSPACE_PATH" = "" ]; then
        WORKSPACE_PATH=$(pwd)
    fi
    WORKSPACE="-v ${WORKSPACE_PATH}:/workspace"

    if [ "$EXEC_PATH" = "" ]; then
        EXEC_PATH=$(pwd)
    fi
    EXEC="-v ${EXEC_PATH}:/exec"

    mkdir -p "${HOST_SOURCE_DIR}/ros2"

    # Set user ID and group ID to match the local user
    USER_ID="-e LOCAL_UID=$(id -u) -e LOCAL_GID=$(id -g) -e LOCAL_USER=$(id -un) -e LOCAL_GROUP=$(id -gn)"

    # Set map path
    if [ "$MAP_PATH" != "" ]; then
        mkdir -p "${HOST_SOURCE_DIR}/fastdds"
        MAP="-v ${MAP_PATH}:/autoware_map:ro -v ${HOST_SOURCE_DIR}/fastdds:/fastdds:rw"
    fi

    if [ "$DATA_PATH" != "" ]; then
        DATA="-v ${DATA_PATH}:/autoware_data:ro"
    fi

    # Set launch command
    if [ "$LAUNCH_CMD" = "" ]; then
        LAUNCH_CMD="/bin/bash"
    fi

}

# Set GPU flag based on option
set_gpu_flag() {
    if [ "$option_no_nvidia" = "true" ]; then
        GPU_FLAG=""
    else
        GPU_FLAG="--gpus all"
        IMAGE=${IMAGE}-cuda
    fi
}

# Set X display variables
set_x_display() {
    MOUNT_X=""
    if [ "$option_headless" = "false" ]; then
        MOUNT_X="-e DISPLAY=$DISPLAY -v /tmp/.X11-unix/:/tmp/.X11-unix"
        xhost + >/dev/null
    fi
}

# Main script execution
main() {
    # Parse arguments
    parse_arguments "$@"
    set_variables
    set_gpu_flag
    set_x_display

    if [ "$option_devel" = "true" ]; then
        echo -e "${GREEN}-----------------------------------------------------------------${NC}"
        echo -e "${BLUE}Launching Autoware development environment${NC}"
    else
        echo -e "${GREEN}-----------------------------------------------------------------${NC}"
        echo -e "${GREEN}Launching Autoware${NC}"
    fi

    #IMAGE=${IMAGE}${package}

    echo -e "${GREEN}IMAGE:${NC} ${IMAGE}"
    if [ "$option_devel" = "true" ]; then
        echo -e "${GREEN}WORKSPACE PATH(mounted):${NC} ${WORKSPACE_PATH}:/workspace"
    fi
    if [ "$MAP_PATH" != "" ]; then
        echo -e "${GREEN}MAP PATH(mounted):${NC} ${MAP_PATH}:/autoware_map"
    fi
    echo -e "${GREEN}LAUNCH CMD:${NC} ${LAUNCH_CMD}"
    echo -e "${GREEN}HOST SOURCE DIR:${NC} ${HOST_SOURCE_DIR}"
    echo -e "${GREEN}ROS DOMAIN ID:${NC} ${ROS_DOMAIN_ID:-0}"
    echo -e "${GREEN}-----------------------------------------------------------------${NC}"

    # Launch the container
    set -x
    docker run -it ${RM} --net=host --pid=host --ipc=host ${GPU_FLAG} ${USER_ID} ${MOUNT_X} \
        -e FASTDDS_BUILTIN_TRANSPORTS=UDPv4 -e ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0} -e XAUTHORITY=${XAUTHORITY} -e XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR -e NVIDIA_DRIVER_CAPABILITIES=all -v /etc/localtime:/etc/localtime:ro \
        ${WORKSPACE} ${MAP} ${DATA} ${EXEC} -v ${HOST_SOURCE_DIR}/ros2:/ros2 ${IMAGE} \
        ${LAUNCH_CMD}
}

# Execute the main script
main "$@"
