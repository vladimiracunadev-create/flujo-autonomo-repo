PYTHON ?= python
UV ?= uv

.PHONY: help install install-dev sync run-panel list smoke flow-health test lint validate clean

help:
	@echo "Targets disponibles:"
	@echo "  install       Instalar dependencias mínimas (pip)"
	@echo "  install-dev   Instalar dependencias dev + schema (pip)"
	@echo "  sync          Sincronizar entorno con uv (recomendado)"
	@echo "  run-panel     Levantar panel local"
	@echo "  list          Listar flujos"
	@echo "  smoke         Ejecutar smoke test integral"
	@echo "  test          Correr suite pytest"
	@echo "  lint          Ejecutar ruff"
	@echo "  validate      Validar manifests (schema + acciones registradas)"
	@echo "  flow-health   Ejecutar healthcheck del sistema"
	@echo "  clean         Limpiar artefactos locales"

install:
	$(PYTHON) -m pip install -r requirements.txt

install-dev:
	$(PYTHON) -m pip install -e ".[dev,schema]"

sync:
	$(UV) sync --extra dev --extra schema

run-panel:
	$(PYTHON) -m app.server

list:
	$(PYTHON) -m engine.runner list

smoke:
	$(PYTHON) scripts/smoke_test.py

flow-health:
	$(PYTHON) -m engine.runner run flows/05_system_healthcheck

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

validate:
	$(PYTHON) scripts/validate_project.py

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov *.egg-info build dist
