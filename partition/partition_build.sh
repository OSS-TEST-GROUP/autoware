#!/usr/bin/env bash

set -e

# Function to print help message
print_help() {
    echo "Usage: build.sh [OPTIONS]"
    echo "Options:"
    echo "  --help          Display this help message"
    echo "  -h              Display this help message"
    echo "  --repo          Specify the Docker Hub repository (e.g., username/repository)"
    echo "  --no-cuda       Disable CUDA support"
    echo "  --platform      Specify the platform (default: current platform)"
    echo "  --devel-only    Build devel image only"
    echo ""
    echo "Note: The --platform option should be one of 'linux/amd64' or 'linux/arm64'."
}

SCRIPT_DIR=$(readlink -f "$(dirname "$0")")
echo "SCRIPT_DIR:$SCRIPT_DIR"
WORKSPACE_ROOT="$SCRIPT_DIR/.."
partitions=()

# targets=()
# stages=(
#     "core-devel"
#     "universe-common-devel"
#     "universe-common-devel-cuda"
#     "universe-perception-devel"
#     "universe-sensing-devel"
#     "universe-perception-devel-cuda"
#     "universe-sensing-devel-cuda"
#     "universe-localization-devel"
#     "universe-mapping-devel"
#     "universe-planning-devel"
#     "universe-control-devel"
#     "universe-vehicle-devel"
#     "universe-system-devel"
#     "universe-devel-cuda"
#     "universe-cuda"
#     "adsw-perception"
#     "adsw-perception-cuda"
#     "adsw-decision"
#     "adsw-control"
# )

repo=""
output_type="--load"
ssh_allow_option=()
ssh_set_option=()

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
        --repo)
            repo=("$2")
            shift
            ;;
        --devel-only)
            option_devel_only=true
            ;;
        --push)
            output_type="--push"
            ;;    
        *)
            echo "Unknown option: $1"
            print_help
            exit 1
            ;;
        esac
        shift
    done

    if [ -z "$repo" ]; then
        echo "Error: --repo option is required." >&2
        print_help
        exit 1
    fi
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
# set_build_options() {
#     if [ "$option_devel_only" = "true" ]; then
#         targets=("universe-devel")
#     #else
#     #    targets=("$target")
#     fi
# }

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

# Set SSH forwarding options for Docker BuildKit.
set_ssh_options() {
    if [ -n "${SSH_AUTH_SOCK:-}" ] && [ -S "$SSH_AUTH_SOCK" ]; then
        ssh_allow_option=("--allow=ssh")
        ssh_set_option=("--set *.ssh=default")
    else
        ssh_allow_option=()
        ssh_set_option=()
        echo "SSH_AUTH_SOCK is not set or not a socket; building without SSH agent forwarding."
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
# copy_config() {

#     echo "copy_config==================================================="

#     cp -r "$WORKSPACE_ROOT/src/launcher/autoware_launch/autoware_launch/" "$WORKSPACE_ROOT/src/obigo_launch/"

#     target_root="$WORKSPACE_ROOT/src/obigo_launch/config_files"
#     mkdir -p "$target_root"

#     if [ ! -d "$WORKSPACE_ROOT/src" ]; then
#         exit 1
#     fi

#     find "$WORKSPACE_ROOT/src" -type d -name config | while read -r config_dir; do
#         package_xml_path="$(dirname "$config_dir")/package.xml"

#         if [[ -f "$package_xml_path" ]]; then
#             package_name=$(awk -F'[<>]' '/<name>/ {print $3}' "$package_xml_path")

#             if [[ -n "$package_name" ]]; then
#                 target_dir="$target_root/$package_name"
#                 mkdir -p "$target_dir"

#                 cp -r "$config_dir/"* "$target_dir/"
#                 echo "Copied files from $config_dir to $target_dir"
#             else
#                 echo "Warning: <name> tag not found in $package_xml_path"
#             fi
#         else
#             echo "Warning: package.xml not found for config folder $config_dir"
#         fi
#     done
# }

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


get_pkg_path() {

    local PKG_LIST="$1"
    local paths=()

    for pkg in $PKG_LIST; do
        path=$(find src -name package.xml -exec grep -l "<name>$pkg</name>" {} \;)
        if [ -n "$path" ]; then
            echo "$pkg: $(dirname "$path")" >&2
            paths+=($(dirname "$path"))
        else
            echo "$pkg: ❌ not found" >&2
            return 1
        fi
    done

    # return paths
    echo "${paths[@]}"
}


configuration_and_build() {
    local partition_name=""
    local folder_path="$1"

    if [ ! -d "$folder_path" ]; then
        echo "ERROR: '$folder_path' does not exist." >&2
        exit 1
    fi

    if ! command -v jq >/dev/null 2>&1; then
        echo "Error: 'jq' is not installed."
        echo ""
        echo "Install:"
        echo "  Ubuntu / Debian:"
        echo "    sudo apt update && sudo apt install -y jq"
        exit 1
    fi

    while read file; do
        local copy_list=""
        local bind_list=""

        echo "$file"

        if ! jq empty "$file" >/dev/null; then
            echo "Error: '$file' JSON parsing failed!"
            exit 1
        fi

        partition_name=$(basename $file '.json')
        echo "$partition_name"

        packages=$(jq -r '.packages // [] | .[]' "$file")

        echo "$packages"

        pkg_paths=$(get_pkg_path "${packages}")
        if [ $? -ne 0 ]; then
            echo "Error: Failed to find all packages for $partition_name. Aborting." >&2
            exit 1
        fi

        for path in $pkg_paths; do
            copy_list+="COPY ${path} /autoware/${path}\n"
            bind_list+="--mount=type=bind,from=${partition_name}-depend,source=/autoware/${path},target=/autoware/${path} \\\\\n"
        done

        folders=$(jq -r '.folders  // [] | .[]' "$file")
        for f in ${folders}; do
            copy_list+="COPY ${f} /autoware/${f}\n"
            bind_list+="--mount=type=bind,from=${partition_name}-depend,source=/autoware/${f},target=/autoware/${f} \\\\\n"
        done

        echo "=========copy_list============="
        echo -e "${copy_list}"
        echo "=========bind_list============="
        echo -e "${bind_list}"


        sed -e "s|%PARTITION_NAME%|$partition_name|g" \
            -e "s|%COPY_LIST%|${copy_list}|g" \
            -e "s|%BIND_LIST%|${bind_list}|g" \
            partition/Dockerfile.template >partition/${partition_name}_Dockerfile

        build_images "${partition_name}"

        rm -f partition/${partition_name}_Dockerfile

    done < <(find $folder_path -type f -name '*.json')
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
    base_option+=("$output_type")
    base_option+=("--progress=plain")
    base_option+=("-f $SCRIPT_DIR/docker-bake-base.hcl")
    base_option+=("--set *.context=$WORKSPACE_ROOT")
    base_option+=("${ssh_set_option[@]}")
    if [ "$output_type" = "--push" ]; then
        base_option+=("--set *.platform=linux/amd64,linux/arm64")
    else
        base_option+=("--set *.platform=$platform")
    fi
    base_option+=("--set *.args.ROS_DISTRO=$rosdistro")
    base_option+=("--set *.args.BASE_IMAGE=$base_image")
    base_option+=("--set *.args.SETUP_ARGS=$setup_args")
    base_option+=("--set *.args.LIB_DIR=$lib_dir")
    base_option+=("--set base.tags=$repo:latest")
    base_option+=("--set base-cuda.tags=$repo:cuda-latest")

    base_targets=("base")
    if [ "$option_no_cuda" != "true" ]; then
        base_targets+=("base-cuda")
    fi

    set -x
    docker buildx bake ${ssh_allow_option[@]} ${base_option[@]} ${base_targets[@]}
    set +x
}

# Build images
build_images() {
    local partition_name="$1"
    # https://github.com/docker/buildx/issues/484
    export BUILDKIT_STEP_LOG_MAX_SIZE=10000000

    echo "Building images for platform: $platform"
    echo "ROS distro: $rosdistro"
    echo "Base image: $base_image"
    echo "Setup args: $setup_args"
    echo "Lib dir: $lib_dir"
    echo "Image name suffix: $image_name_suffix"
    #echo "Targets: ${targets[*]}"
    echo "Stage: $1"


    autoware_base_image="${repo}:latest"
    autoware_base_cuda_image="${repo}:cuda-latest"

    echo "partition_name: $partition_name"
    echo "autoware_base_image: $autoware_base_image"
    echo "autoware_base_cuda_image: $autoware_base_cuda_image"

    build_option=()
    build_option+=("$output_type")
    #build_option+=("--push")
    build_option+=("--progress=plain")
    build_option+=("-f $SCRIPT_DIR/docker-bake.hcl")
    #build_option+=("-f $SCRIPT_DIR/docker-bake-cuda.hcl")
    build_option+=("--set *.context=$WORKSPACE_ROOT")
    build_option+=("${ssh_set_option[@]}")
    #build_option+=("--set *.platform=$platform")
    #build_option+=("--set *.platforms=linux/amd64,linux/arm64")
    build_option+=("--set *.args.ROS_DISTRO=$rosdistro")
    build_option+=("--set *.args.BASE_IMAGE=$base_image")
    build_option+=("--set *.args.AUTOWARE_BASE_IMAGE=$autoware_base_image")
    build_option+=("--set *.args.AUTOWARE_BASE_CUDA_IMAGE=$autoware_base_cuda_image")
    build_option+=("--set *.args.SETUP_ARGS=$setup_args")
    #build_option+=("--set *.args.LIB_DIR=$lib_dir")
    #build_option+=("--set partition.tags=$repo:${partition_name}-${lib_dir}")
    build_option+=("--set partition*.tags=${repo}:${partition_name}${image_name_suffix}")
    build_option+=("--set partition*.dockerfile=partition/${partition_name}_Dockerfile")
    build_option+=("--set partition*.target=${partition_name}${image_name_suffix}")

    set -x
    if [ "$output_type" = "--push" ]; then
        docker buildx bake ${ssh_allow_option[@]} ${build_option[@]} partition-multi-platform
    else
        docker buildx bake ${ssh_allow_option[@]} ${build_option[@]} partition
    fi
    set +x
}

# Remove dangling images
remove_dangling_images() {
    docker image prune -f
}

# Main script execution
parse_arguments "$@"
set_cuda_options
#set_build_options
set_platform
set_arch_lib_dir
set_ssh_options
load_env
#copy_config
clone_repositories

build_base_images
configuration_and_build "partition/partition_config"

remove_dangling_images
