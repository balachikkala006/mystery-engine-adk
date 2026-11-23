terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  required_apis = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "aiplatform.googleapis.com",
    "cloudtrace.googleapis.com",
    "dlp.googleapis.com",
  ])
}

resource "google_project_service" "enabled_apis" {
  for_each           = local.required_apis
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "mystery_engine_repo" {
  location      = var.region
  repository_id = "${var.service_name}-images"
  description   = "Container registry for the Interactive AI Mystery Engine (Google ADK)"
  format        = "DOCKER"

  depends_on = [google_project_service.enabled_apis]
}

resource "google_storage_bucket" "agent_engine_staging" {
  name                        = "${var.project_id}-${var.service_name}-staging"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  depends_on = [google_project_service.enabled_apis]
}

resource "google_service_account" "mystery_engine_sa" {
  account_id   = "${var.service_name}-sa"
  display_name = "Interactive AI Mystery Engine Runtime SA"
}

resource "google_secret_manager_secret" "google_api_key" {
  secret_id = var.api_key_secret_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled_apis]
}

resource "google_secret_manager_secret_iam_member" "api_key_accessor" {
  secret_id = google_secret_manager_secret.google_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.mystery_engine_sa.email}"
}

resource "google_project_iam_member" "cloud_trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.mystery_engine_sa.email}"
}

resource "google_project_iam_member" "cloud_dlp_user" {
  project = var.project_id
  role    = "roles/dlp.user"
  member  = "serviceAccount:${google_service_account.mystery_engine_sa.email}"
}

resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.mystery_engine_sa.email}"
}

resource "google_cloud_run_v2_service" "mystery_engine" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.mystery_engine_sa.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.container_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      env {
        name  = "MYSTERY_FAST_MODEL"
        value = var.fast_model
      }

      env {
        name  = "MYSTERY_PLANNING_MODEL"
        value = var.planning_model
      }

      env {
        name  = "SESSION_BACKEND"
        value = "sqlite"
      }

      env {
        name  = "LOG_FORMAT"
        value = "json"
      }

      env {
        name  = "OTEL_EXPORTER"
        value = "cloud_trace"
      }

      env {
        name  = "ENABLE_CLOUD_DLP"
        value = "true"
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_api_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.enabled_apis,
    google_secret_manager_secret_iam_member.api_key_accessor,
  ]
}
