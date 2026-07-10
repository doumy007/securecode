.PHONY: help install dev run migrate test lint clean docker-up docker-down

help:
	@echo "SecureCode AI - Comandos disponibles"
	@echo "install      Instalar dependencias"
	@echo "dev          Ejecutar en modo desarrollo"
	@echo "run          Ejecutar en modo producción"
	@echo "migrate      Ejecutar migraciones"
	@echo "test         Ejecutar tests"
	@echo "lint         Ejecutar linter"
	@echo "clean        Limpiar archivos temporales"
	@echo "docker-up    Iniciar servicios Docker"
	@echo "docker-down  Detener servicios Docker"

install:
	pip install -e .
	pip install -e ".[dev]"

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

migrate:
	alembic upgrade head

test:
	pytest -v --cov=app --cov-report=term-missing

lint:
	ruff check .
	mypy app

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -rf dist
	rm -rf build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

db-init:
	alembic init migrations 2>/dev/null || true
	alembic revision --autogenerate -m "initial"
	alembic upgrade head
