group "default" {
  targets = [
    "universe-common-devel-cuda",
    "universe-perception-devel-cuda",
    "universe-sensing-devel-cuda",
    "adsw-perception-cuda",
    "universe-devel-cuda",
    "universe-cuda"
  ]
}

// For docker/metadata-action
target "docker-metadata-action-universe-common-devel-cuda" {}
target "docker-metadata-action-universe-perception-devel-cuda" {}
target "docker-metadata-action-universe-sensing-devel-cuda" {}
target "docker-metadata-action-adsw-perception-cuda" {}
target "docker-metadata-action-universe-devel-cuda" {}
target "docker-metadata-action-universe-cuda" {}

target "universe-common-devel-cuda" {
  inherits = ["docker-metadata-action-universe-common-devel-cuda"]
  dockerfile = "partition/Dockerfile"
  target = "universe-common-devel-cuda"
}

target "universe-perception-devel-cuda" {
  inherits = ["docker-metadata-action-universe-perception-devel-cuda"]
  dockerfile = "partition/Dockerfile"
  target = "universe-perception-devel-cuda"
}

target "universe-sensing-devel-cuda" {
  inherits = ["docker-metadata-action-universe-sensing-devel-cuda"]
  dockerfile = "partition/Dockerfile"
  target = "universe-sensing-devel-cuda"
}

target "adsw-perception-cuda" {
  inherits = ["docker-metadata-action-adsw-perception-cuda"]
  dockerfile = "partition/Dockerfile"
  target = "adsw-perception-cuda"
}

target "universe-devel-cuda" {
  inherits = ["docker-metadata-action-universe-devel-cuda"]
  dockerfile = "partition/Dockerfile"
  target = "universe-devel-cuda"
}

target "universe-cuda" {
  inherits = ["docker-metadata-action-universe-cuda"]
  dockerfile = "partition/Dockerfile"
  target = "universe-cuda"
}
