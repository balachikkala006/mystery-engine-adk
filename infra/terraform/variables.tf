variable "project_id" {
  description = "Google Cloud project ID for deploying the Mystery Engine."
  type        = string
}

variable "region" {
  description = "Google Cloud region for Cloud Run, Artifact Registry, and Vertex AI."
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Cloud Run service name and resource prefix."
  type        = string
  default     = "mystery-engine-adk"
}

variable "container_image" {
  description = "Fully qualified Artifact Registry image URI for the built Docker container."
  type        = string
}

variable "api_key_secret_id" {
  description = "Secret Manager secret ID storing the Gemini API key."
  type        = string
  default     = "GOOGLE_API_KEY"
}

variable "fast_model" {
  description = "Low-latency Gemini Flash model for interactive routing, dialogue, and tools."
  type        = string
  default     = "gemini-3.5-flash"
}

variable "planning_model" {
  description = "High-reasoning Gemini model for parallel worldbuilding and lore critique."
  type        = string
  default     = "gemini-3.8-flash"
}

variable "min_instances" {
  description = "Minimum Cloud Run instances."
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum Cloud Run instances."
  type        = number
  default     = 3
}
