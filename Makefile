.PHONY: submodules fetch-live front-dev front-build front-preview

fetch-live:
	python3 scripts/fetch_worldcup2026_live.py

submodules:
	@if [ ! -f .gitmodules ]; then \
		echo "Nenhum submodule configurado (.gitmodules nao encontrado)."; \
		exit 0; \
	fi
	@echo "Sincronizando configuracao dos submodules..."
	@if git submodule sync --recursive; then \
		echo "Configuracao sincronizada."; \
	else \
		echo "Aviso: nao foi possivel sincronizar .git/config; continuando com os paths do .gitmodules."; \
	fi
	@echo "Baixando submodules com acesso disponivel..."
	@paths=$$(git config --file .gitmodules --get-regexp '^submodule\..*\.path$$' | awk '{print $$2}'); \
	if [ -z "$$paths" ]; then \
		echo "Nenhum path de submodule encontrado em .gitmodules."; \
		exit 0; \
	fi; \
	for path in $$paths; do \
		echo ""; \
		echo "==> $$path"; \
		if git submodule update --init --recursive "$$path"; then \
			echo "OK: $$path"; \
		else \
			echo "SKIP: sem acesso ou erro ao baixar $$path"; \
		fi; \
	done

## Internals Commands
#front-dev:
#	cd worldcup && npm install && npm run dev
#
#front-build:
#	cd worldcup && npm install && npm run build
#
#front-preview:
#	cd worldcup && npm run preview
