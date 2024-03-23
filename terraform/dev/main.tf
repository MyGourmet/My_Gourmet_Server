# Terraform configuration for development environment
terraform {
  required_providers {
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 4.0"
    }
  }
}

# Use separate credentials for dev-gcf-v2-sourcesthe development environment if necessary
provider "google-beta" {
  user_project_override = true
  credentials           = file("my-gourmet-dev-f5b45-b6daba966c24.json")
}

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
  name     = "dev-model-jp-my-gourmet-image-classification-2024-0204"
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

# Update android app configurations for development
resource "google_firebase_android_app" "default" {
  provider     = google-beta
  project      = var.project_id
  display_name = "MyGourmet"
  package_name = "com.blue_waltz.my_gourmet.dev"

  lifecycle {
    ignore_changes = [
      sha1_hashes,
      sha256_hashes,
    ]
  }
}

# Commented-out resources can be enabled if those services are needed in development
# Make sure to use the correct project ID and service names for the dev environment
