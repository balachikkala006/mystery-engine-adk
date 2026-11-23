"""Deploy the Interactive AI Mystery Engine to Vertex AI Agent Engine.

Wraps `root_agent` in `vertexai.agent_engines.AdkApp` with Cloud Trace enabled
and provisions a managed Agent Engine deployment.

Prerequisites:
    pip install "google-cloud-aiplatform[adk,agent_engines]"
    export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
    export GOOGLE_CLOUD_LOCATION="us-central1"
    export STAGING_BUCKET="gs://your-staging-bucket"

Usage:
    python deploy/deploy_agent_engine.py
"""

from __future__ import annotations

import os
import sys

import vertexai
from vertexai import agent_engines

from mystery_engine.agent import root_agent


def deploy() -> str:
    """Provision the Mystery Engine on Vertex AI Agent Engine and return its resource name."""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    staging_bucket = os.environ.get("STAGING_BUCKET")

    if not project or not staging_bucket:
        print(
            "Error: Set GOOGLE_CLOUD_PROJECT and STAGING_BUCKET (e.g. gs://my-bucket) first.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    vertexai.init(project=project, location=location, staging_bucket=staging_bucket)

    adk_app = agent_engines.AdkApp(
        agent=root_agent,
        enable_tracing=True,
    )

    remote_app = agent_engines.create(
        agent_engine=adk_app,
        display_name="interactive-ai-mystery-engine",
        description="Freestyle Track multi-agent detective engine built with Google ADK.",
        requirements=[
            "google-cloud-aiplatform[adk,agent_engines]>=1.95.0",
            "google-adk>=1.14.0",
            "pydantic>=2.10.0",
            "mcp>=1.6.0",
            "aiosqlite>=0.20.0",
            "opentelemetry-api>=1.28.0",
            "opentelemetry-sdk>=1.28.0",
        ],
        extra_packages=["mystery_engine"],
    )

    print(f"Deployed Vertex AI Agent Engine: {remote_app.resource_name}")
    return remote_app.resource_name


if __name__ == "__main__":
    deploy()
