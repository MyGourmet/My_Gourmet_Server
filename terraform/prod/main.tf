# Terraform configuration to set up providers by version.
terraform {
  required_providers {
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 4.0"
    }
  }
}

# Configures the provider to use the resource block's specified project for quota checks.
provider "google-beta" {
  user_project_override = true
  credentials           = file("my-gourmet-160fb-3f17914b9edb.json")
}

# Configures the provider to not use the resource block's specified project for quota checks.
# This provider should only be used during project creation and initializing services.
provider "google-beta" {
  alias                 = "no_user_project_override"
  user_project_override = false
}

resource "google_firebase_project" "default" {
  provider = google-beta
  project  = var.project_id
}

resource "google_storage_bucket" "default" {
  provider = google-beta
  project  = var.project_id
  name     = "model-jp-my-gourmet-image-classification-2023-08"
  location = var.region

  public_access_prevention = "enforced"
}

resource "google_firebase_storage_bucket" "default" {
  provider  = google-beta
  project   = var.project_id
  bucket_id = google_storage_bucket.default.id
}

resource "google_firestore_database" "default" {
  provider    = google-beta
  project     = var.project_id
  type        = "FIRESTORE_NATIVE"
  location_id = var.region
  name        = "(default)"
}

resource "google_firebase_android_app" "default" {
  provider     = google-beta
  project      = var.project_id
  display_name = "MyGourmet"
  package_name = "com.blue_waltz.my_gourmet"

  lifecycle {
    ignore_changes = [
      sha1_hashes,
      sha256_hashes,
    ]
  }
}

# resource "google_project_service" "compute" {
#   provider = google-beta
#   project  = var.project_id
#   service  = "compute.googleapis.com"
# }


