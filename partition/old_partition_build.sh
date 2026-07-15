#!/usr/bin/env bash

set -e

# Function to print help message
print_help() {
    echo "Usage: build.sh [OPTIONS]"
    echo "Options:"
    echo "  --help          Display this help message"
    echo "  -h              Display this help message"
    echo "  --no-cuda       Disable CUDA support"
    echo "  --platform      Specify the platform (default: current platform)"
    echo "  --devel-only    Build devel image only"
    echo ""
    echo "Note: The --platform option should be one of 'linux/amd64' or 'linux/arm64'."
}

SCRIPT_DIR=$(readlink -f "$(dirname "$0")")
echo "SCRIPT_DIR:$SCRIPT_DIR"
WORKSPACE_ROOT="$SCRIPT_DIR/.."
targets=()
stages=(
    "core-devel"
	"universe-common-devel"
	"universe-common-devel-cuda"
	"universe-perception-devel" 
	"universe-sensing-devel"
	"universe-perception-devel-cuda"
	"universe-sensing-devel-cuda" 
	"universe-localization-devel" 
	"universe-mapping-devel" 
	"universe-planning-devel"
	"universe-control-devel"
	"universe-vehicle-devel"
	"universe-system-devel"
	"universe-devel-cuda"
	"universe-cuda"
	"adsw-perception"
	"adsw-perception-cuda"
	"adsw-decision"
	"adsw-control"
    )  

# Parse arguments
parse_arguments() {
    while [ "$1" != "" ]; do
        case "$1" in
        --help | -h)
            print_help
            exit 1
            ;;
        --no-cuda)
            option_no_cuda=true
            ;;
        --platform)
            option_platform="$2"
            shift
            ;;
        --target)
            stages=("$2")
            shift
            ;;
        --devel-only)
            option_devel_only=true
            ;;
        *)
            echo "Unknown option: $1"
            print_help
            exit 1
            ;;
        esac
        shift
    done
}

# Set CUDA options
set_cuda_options() {
    if [ "$option_no_cuda" = "true" ]; then
        setup_args="--no-nvidia"
        image_name_suffix=""
    else
        image_name_suffix="-cuda"
    fi
}

# Set build options
set_build_options() {
    if [ "$option_devel_only" = "true" ]; then
        targets=("universe-devel")
    #else
    #    targets=("$target")
    fi
}

# Set platform
set_platform() {
    if [ -n "$option_platform" ]; then
        platform="$option_platform"
    else
        platform="linux/amd64"
        if [ "$(uname -m)" = "aarch64" ]; then
            platform="linux/arm64"
        fi
    fi
}

# Set arch lib dir
set_arch_lib_dir() {
    if [ "$platform" = "linux/arm64" ]; then
        lib_dir="aarch64"
    elif [ "$platform" = "linux/amd64" ]; then
        lib_dir="x86_64"
    else
        echo "Unsupported platform: $platform"
        exit 1
    fi
}

# Load env
load_env() {
    source "$WORKSPACE_ROOT/amd64.env"
    if [ "$platform" = "linux/arm64" ]; then
        source "$WORKSPACE_ROOT/arm64.env"
    fi
}

# Clone repositories
copy_config() {
target_root="$WORKSPACE_ROOT/src/obigo_launch/config_files"
mkdir -p "$target_root"

    if [ ! -d "$WORKSPACE_ROOT/src" ]; then
       exit 1
    fi

find "$WORKSPACE_ROOT/src" -type d -name config | while read -r config_dir; do
    package_xml_path="$(dirname "$config_dir")/package.xml"

    if [[ -f "$package_xml_path" ]]; then
        package_name=$(awk -F'[<>]' '/<name>/ {print $3}' "$package_xml_path")

        if [[ -n "$package_name" ]]; then
            target_dir="$target_root/$package_name"
            mkdir -p "$target_dir"

            cp -r "$config_dir/"* "$target_dir/"
            echo "Copied files from $config_dir to $target_dir"
        else
            echo "Warning: <name> tag not found in $package_xml_path"
        fi
    else
        echo "Warning: package.xml not found for config folder $config_dir"
    fi
done
}

# Clone repositories
clone_repositories() {
    cd "$WORKSPACE_ROOT"
    if [ ! -d "src" ]; then
        mkdir -p src
        vcs import src <autoware.repos
    else
        echo "Source directory already exists. Updating repositories..."
        vcs import src <autoware.repos
        vcs pull src
    fi
}

# Build base images
build_base_images() {
    # https://github.com/docker/buildx/issues/484
    export BUILDKIT_STEP_LOG_MAX_SIZE=10000000

    echo "Building images for platform: $platform"
    echo "ROS distro: $rosdistro"
    echo "Base image: $base_image"
    echo "Setup args: $setup_args"
    echo "Lib dir: $lib_dir"
    echo "Image name suffix: $image_name_suffix"
    echo "Target: $target"

    base_option=()
    base_option+=("--load")
    base_option+=("--progress=plain")
    base_option+=("-f $SCRIPT_DIR/docker-bake-base.hcl")
	base_option+=("--set *.context=$WORKSPACE_ROOT")
    base_option+=("--set *.ssh=default")
    base_option+=("--set *.platform=$platform")
    base_option+=("--set *.args.ROS_DISTRO=$rosdistro")
    base_option+=("--set *.args.BASE_IMAGE=$base_image")
    base_option+=("--set *.args.SETUP_ARGS=$setup_args")
    base_option+=("--set *.args.LIB_DIR=$lib_dir")
	base_option+=("--set base.tags=zeusyoon/adsw:latest-$lib_dir")
    base_option+=("--set base-cuda.tags=zeusyoon/adsw:cuda-latest-$lib_dir")
	
    set -x
	docker buildx bake ${base_option[@]}
    set +x		
}

# Build images
build_images() {
    # https://github.com/docker/buildx/issues/484
    export BUILDKIT_STEP_LOG_MAX_SIZE=10000000

    echo "Building images for platform: $platform"
    echo "ROS distro: $rosdistro"
    echo "Base image: $base_image"
    echo "Setup args: $setup_args"
    echo "Lib dir: $lib_dir"
    echo "Image name suffix: $image_name_suffix"
    echo "Targets: ${targets[*]}"
	echo "Stage: $1"

    autoware_base_image="zeusyoon/adsw:latest-$lib_dir"
    autoware_base_cuda_image="zeusyoon/adsw:cuda-latest-$lib_dir"

    echo "autoware_base_image: $autoware_base_image"
    echo "autoware_base_cuda_image: $autoware_base_cuda_image"


    build_option=()
    build_option+=("--load")
    build_option+=("--progress=plain")
    build_option+=("-f $SCRIPT_DIR/docker-bake.hcl")
	build_option+=("-f $SCRIPT_DIR/docker-bake-cuda.hcl")
    build_option+=("--set *.context=$WORKSPACE_ROOT")
    build_option+=("--set *.ssh=default")
    build_option+=("--set *.platform=$platform")
    build_option+=("--set *.args.ROS_DISTRO=$rosdistro")
    build_option+=("--set *.args.BASE_IMAGE=$base_image")
    build_option+=("--set *.args.AUTOWARE_BASE_IMAGE=$autoware_base_image")
    build_option+=("--set *.args.AUTOWARE_BASE_CUDA_IMAGE=$autoware_base_cuda_image")
    build_option+=("--set *.args.SETUP_ARGS=$setup_args")
    build_option+=("--set *.args.LIB_DIR=$lib_dir")
    build_option+=("--set core-devel.tags=zeusyoon/adsw:core-devel-$lib_dir")
    build_option+=("--set universe-common-devel.tags=zeusyoon/adsw:universe-common-devel-$lib_dir")
	build_option+=("--set universe-common-devel-cuda.tags=zeusyoon/adsw:universe-common-devel-$lib_dir-cuda")
    build_option+=("--set universe-perception-devel.tags=zeusyoon/adsw:universe-perception-devel-$lib_dir")
	build_option+=("--set universe-perception-devel-cuda.tags=zeusyoon/adsw:universe-perception-devel-$lib_dir-cuda")
    build_option+=("--set universe-sensing-devel.tags=zeusyoon/adsw:universe-sensing-devel-$lib_dir")
	build_option+=("--set universe-sensing-devel-cuda.tags=zeusyoon/adsw:universe-sensing-devel-$lib_dir-cuda")
    build_option+=("--set universe-localization-devel.tags=zeusyoon/adsw:universe-localization-devel-$lib_dir")
    build_option+=("--set universe-mapping-devel.tags=zeusyoon/adsw:universe-mapping-devel-$lib_dir")
    build_option+=("--set universe-planning-devel.tags=zeusyoon/adsw:universe-planning-devel-$lib_dir")
    build_option+=("--set universe-control-devel.tags=zeusyoon/adsw:universe-control-devel-$lib_dir")
    build_option+=("--set universe-vehicle-devel.tags=zeusyoon/adsw:universe-vehicle-devel-$lib_dir")
    build_option+=("--set universe-system-devel.tags=zeusyoon/adsw:universe-system-devel-$lib_dir")
    build_option+=("--set universe-devel.tags=zeusyoon/adsw:universe-devel-$lib_dir")
	build_option+=("--set universe-devel-cuda.tags=zeusyoon/adsw:universe-devel-$lib_dir-cuda")
    build_option+=("--set universe.tags=zeusyoon/adsw:universe-$lib_dir")
	build_option+=("--set universe-cuda.tags=zeusyoon/adsw:universe-$lib_dir-cuda")
    build_option+=("--set adsw-perception.tags=zeusyoon/adsw:adsw-perception-$lib_dir")
	build_option+=("--set adsw-perception-cuda.tags=zeusyoon/adsw:adsw-perception-$lib_dir-cuda")
    build_option+=("--set adsw-decision.tags=zeusyoon/adsw:adsw-decision-$lib_dir")
    build_option+=("--set adsw-control.tags=zeusyoon/adsw:adsw-control-$lib_dir")

    set -x
    docker buildx bake ${build_option[@]} "$1" #"${targets[@]}"
    set +x
}

# Remove dangling images
remove_dangling_images() {
    docker image prune -f
}



# Main script execution
parse_arguments "$@"
set_cuda_options
set_build_options
set_platform
set_arch_lib_dir
load_env
copy_config
#clone_repositories

build_base_images

index=0
while [ $index -lt ${#stages[@]} ]; do
    build_images "${stages[$index]}"
	index=$((index+1))
done

remove_dangling_images
