.PHONY: install lint test eval run web a2a docker-build clean

install:
	uv sync --extra dev

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

test:
	uv run pytest -v

eval:
	RUN_LIVE_EVALS=1 uv run pytest tests/test_evals.py -v -m eval

run:
	uv run python main.py

web:
	uv run adk web .

a2a:
	uv run python -m mystery_engine.a2a_server

docker-build:
	docker build -t mystery-engine-adk:latest .

clean:
	rm -rf .pytest_cache .ruff_cache data/sessions/*.db __pycache__
