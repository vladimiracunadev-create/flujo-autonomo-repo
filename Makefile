PYTHON ?= python

.PHONY: help install run-panel list smoke flow-health

help:
	@echo "Targets disponibles:"
	@echo "  install     Instalar dependencias"
	@echo "  run-panel   Levantar panel local"
	@echo "  list        Listar flujos"
	@echo "  smoke       Ejecutar smoke test"
	@echo "  flow-health Ejecutar healthcheck del sistema"

install:
	$(PYTHON) -m pip install -r requirements.txt

run-panel:
	$(PYTHON) -m app.server

list:
	$(PYTHON) -m engine.runner list

smoke:
	$(PYTHON) scripts/smoke_test.py

flow-health:
	$(PYTHON) -m engine.runner run flows/05_system_healthcheck
