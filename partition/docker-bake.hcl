group "default" {
  targets = [
    "partition"
  ]
}


// For docker/metadata-action
target "docker-metadata-action-core-devel" {}
target "docker-metadata-action-universe-common-devel" {}
target "docker-metadata-action-partition" {}

//target "core-devel" {
//  inherits = ["docker-metadata-action-core-devel"]
//  dockerfile = "partition/newDockerfile"
//  target = "core-devel"
//}

//target "universe-common-devel" {
//  inherits = ["docker-metadata-action-universe-common-devel"]
//  dockerfile = "partition/newDockerfile"
//  target = "universe-common-devel"
//}

target "partition" {
  inherits = ["docker-metadata-action-partition"]
//  dockerfile = "partition/newDockerfile"
  target = "partition"

}


target "partition-multi-platform" {
  inherits = ["docker-metadata-action-partition"]
//  dockerfile = "partition/newDockerfile"
  target = "partition"
  output = ["type=registry"]
  platforms = [
    "linux/amd64",
    "linux/arm64"
  ]

  platform "linux/amd64" {
    args = {
      LIB_DIR = "x86_64"
    }
  }

  platform "linux/arm64" {
    args = {
      LIB_DIR = "aarch64"
    }
  }
}
