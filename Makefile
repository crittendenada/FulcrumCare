.PHONY: dev seed backend frontend

dev:
	@echo "Starting FulcrumCare (backend + frontend)…"
	@trap 'kill 0' INT; \
	(cd backend && uvicorn main:app --reload --port 8000) & \
	(cd frontend && export PATH="$$HOME/.local/share/fnm:$$PATH" && eval "$$(fnm env)" && npm run dev) & \
	wait

backend:
	cd backend && uvicorn main:app --reload --port 8000

frontend:
	cd frontend && export PATH="$$HOME/.local/share/fnm:$$PATH" && eval "$$(fnm env)" && npm run dev

seed:
	python3 db/seed.py
	@echo "Demo data reset."
