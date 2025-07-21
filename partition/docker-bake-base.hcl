group "default" {
  targets = [
    "base",
    "base-cuda"
  ]
}

// For docker/metadata-action
target "docker-metadata-action-base" {}
target "docker-metadata-action-base-cuda" {}

target "base" {
  inherits = ["docker-metadata-action-base"]
  dockerfile = "partition/Dockerfile.base"
  target = "base"
}

target "base-cuda" {
  inherits = ["docker-metadata-action-base-cuda"]
  dockerfile = "partition/Dockerfile.base"
  target = "base-cuda"
}
