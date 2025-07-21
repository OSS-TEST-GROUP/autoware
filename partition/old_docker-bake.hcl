group "default" {
  targets = [
    "core-devel",
    "universe-common-devel",
    "universe-perception-devel",
    "universe-sensing-devel",
    "universe-localization-devel",
    "universe-mapping-devel",
    "universe-planning-devel",
    "universe-control-devel",
    "universe-vehicle-devel",
    "universe-system-devel",
    "adsw-perception",
    "adsw-decision",
    "adsw-control",
    "universe-devel",
    "universe"
  ]
}

// For docker/metadata-action
target "docker-metadata-action-core-devel" {}
target "docker-metadata-action-universe-common-devel" {}
target "docker-metadata-action-universe-perception-devel" {}
target "docker-metadata-action-universe-perception" {}
target "docker-metadata-action-universe-sensing-devel" {}
target "docker-metadata-action-universe-sensing" {}
target "docker-metadata-action-universe-localization-devel" {}
target "docker-metadata-action-universe-mapping-devel" {}
target "docker-metadata-action-universe-vehicle-devel" {}
target "docker-metadata-action-universe-system-devel" {}
target "docker-metadata-action-universe-planning-devel" {}
target "docker-metadata-action-universe-control-devel" {}
target "docker-metadata-action-adsw-perception" {}
target "docker-metadata-action-adsw-decision" {}
target "docker-metadata-action-adsw-control" {}
target "docker-metadata-action-universe-devel" {}
target "docker-metadata-action-universe" {}

target "core-devel" {
  inherits = ["docker-metadata-action-core-devel"]
  dockerfile = "partition/Dockerfile"
  target = "core-devel"
}

target "universe-common-devel" {
  inherits = ["docker-metadata-action-universe-common-devel"]
  dockerfile = "partition/Dockerfile"
  target = "universe-common-devel"
}

target "universe-perception-devel" {
  inherits = ["docker-metadata-action-universe-perception-devel"]
  dockerfile = "partition/Dockerfile"
  target = "universe-perception-devel"
}


target "universe-sensing-devel" {
  inherits = ["docker-metadata-action-universe-sensing-devel"]
  dockerfile = "partition/Dockerfile"
  target = "universe-sensing-devel"
}

target "universe-localization-devel" {
  inherits = ["docker-metadata-action-universe-localization-devel"]
  dockerfile = "partition/Dockerfile"
  target = "universe-localization-devel"
}

target "universe-mapping-devel" {
  inherits = ["docker-metadata-action-universe-mapping-devel"]
  dockerfile = "partition/Dockerfile"
  target = "universe-mapping-devel"
}

target "universe-planning-devel" {
  inherits = ["docker-metadata-action-universe-planning-devel"]
  dockerfile = "partition/Dockerfile"
  target = "universe-planning-devel"
}

target "universe-control-devel" {
  inherits = ["docker-metadata-action-universe-control-devel"]
  dockerfile = "partition/Dockerfile"
  target = "universe-control-devel"
}

target "universe-vehicle-devel" {
  inherits = ["docker-metadata-action-universe-vehicle-devel"]
  dockerfile = "partition/Dockerfile"
  target = "universe-vehicle-devel"
}

target "universe-system-devel" {
  inherits = ["docker-metadata-action-universe-system-devel"]
  dockerfile = "partition/Dockerfile"
  target = "universe-system-devel"
}

target "adsw-perception" {
  inherits = ["docker-metadata-action-adsw-perception"]
  dockerfile = "partition/Dockerfile"
  target = "adsw-perception"
}

target "adsw-decision" {
  inherits = ["docker-metadata-action-adsw-decision"]
  dockerfile = "partition/Dockerfile"
  target = "adsw-decision"
}

target "adsw-control" {
  inherits = ["docker-metadata-action-adsw-control"]
  dockerfile = "partition/Dockerfile"
  target = "adsw-control"
}

target "universe-devel" {
  inherits = ["docker-metadata-action-universe-devel"]
  dockerfile = "partition/Dockerfile"
  target = "universe-devel"
}

target "universe" {
  inherits = ["docker-metadata-action-universe"]
  dockerfile = "partition/Dockerfile"
  target = "universe"
}
