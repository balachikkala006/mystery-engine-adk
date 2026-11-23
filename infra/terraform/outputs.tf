output "cloud_run_url" {
  description = "Public HTTPS URL of the deployed Mystery Engine Cloud Run service."
  value       = google_cloud_run_v2_service.mystery_engine.uri
}

output "artifact_registry_repository" {
  description = "Artifact Registry Docker repository path for pushing container builds."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.mystery_engine_repo.repository_id}"
}

output "agent_engine_staging_bucket" {
  description = "GCS staging bucket URI for Vertex AI Agent Engine deployments."
  value       = "gs://${google_storage_bucket.agent_engine_staging.name}"
}

output "service_account_email" {
  description = "Dedicated least-privilege runtime service account email."
  value       = google_service_account.mystery_engine_sa.email
}
