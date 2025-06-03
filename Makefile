.PHONY: all requirements create-env add-jupyter-kernel install-pip-tools activate install postinstall dev-requirements clean build publish

ENV_NAME ?= factverifai-env

all: create-env dev-requirements requirements add-jupyter-kernel install postinstall

create-env:
	@if [ ! -f "$(ENV_NAME)/bin/pip" ]; then \
		echo "Creating virtual environment: $(ENV_NAME)"; \
		rm -rf $(ENV_NAME); \
		python3 -m venv $(ENV_NAME); \
	else \
		echo "Virtual environment $(ENV_NAME) already exists. Skipping creation."; \
	fi

install-pip-tools: create-env
	@echo "Checking if pip-tools is installed..."
	@if ! $(ENV_NAME)/bin/pip show pip-tools > /dev/null 2>&1; then \
		echo "pip-tools not found. Installing..."; \
		$(ENV_NAME)/bin/pip install pip-tools; \
	else \
		echo "pip-tools is already installed. Skipping installation."; \
	fi

requirements: create-env install-pip-tools
	@echo "Compiling and installing main requirements..."
	$(ENV_NAME)/bin/pip-compile requirements.in
	$(ENV_NAME)/bin/pip install -r requirements.txt
	$(ENV_NAME)/bin/pip install -e .

dev-requirements: create-env install-pip-tools
	@if [ -f dev-requirements.in ]; then \
		echo "Compiling and installing dev requirements..."; \
		$(ENV_NAME)/bin/pip-compile dev-requirements.in; \
		$(ENV_NAME)/bin/pip install -r dev-requirements.txt; \
	fi

install: create-env
	$(ENV_NAME)/bin/pip install -r requirements.txt
	$(ENV_NAME)/bin/pip install -e .

add-jupyter-kernel: create-env
	@echo "Checking if Jupyter kernel for environment $(ENV_NAME) exists..."
	@if jupyter kernelspec list | grep -q "$(ENV_NAME)"; then \
		echo "Jupyter kernel for $(ENV_NAME) already exists. Skipping addition."; \
	else \
		echo "Adding Jupyter kernel for environment $(ENV_NAME)..."; \
		$(ENV_NAME)/bin/python -m ipykernel install --user --name=$(ENV_NAME) --display-name "Jupyter $(ENV_NAME)"; \
	fi

activate:
	@echo "To activate, run: source $(ENV_NAME)/bin/activate"

clean:
	rm -rf $(ENV_NAME) dist/ *.egg-info __pycache__ factverifai/__pycache__ factverifai/*.egg-info

build: create-env
	$(ENV_NAME)/bin/python -m build

publish: build
	$(ENV_NAME)/bin/twine upload dist/*



# ollama docker commands
ollama-setup:
	@echo "setting up ollama environment.."
	@if [ ! -f .env ]; then \
		echo "creating .env from .env.example.."; \
		cp .env.example .env; \
		echo "please edit .env file with your EXA_API_KEY"; \
	else \
		echo ".env file already exists"; \
	fi

ollama-up: ollama-setup
	@echo "starting ollama service.."
	@if grep -q "USE_NVIDIA_GPU=true" .env 2>/dev/null; then \
		echo "using nvidia gpu profile.."; \
		docker compose --profile gpu up -d; \
	else \
		echo "using cpu profile.."; \
		docker compose --profile cpu up -d; \
	fi

ollama-init-model:
	@echo "setting up default model (one time setup).."
	@echo "checking if ollama docker image exists locally..."
	@if ! docker images | grep -q ollama; then \
		echo "ollama docker image not found - this will download ~2-3GB (first time only)"; \
	fi
	@echo "starting ollama service (this may take 5-10 minutes on first run)..."
	@until docker compose exec ollama ollama list > /dev/null 2>&1; do \
		echo "waiting for ollama container to be ready... (checking every 5s)"; \
		sleep 5; \
	done
	@echo "ollama is ready! now downloading model (~1GB)..."
	docker compose exec ollama ollama pull gemma3:1b
	@echo "model setup complete"

ollama-down:
	@echo "stopping ollama service..."
	docker compose down

ollama-full-setup: ollama-up ollama-init-model
	@echo "ollama setup complete"
	@echo ""
	@echo "now install factverifai in your project:"
	@echo "  pip install factverifai"
	@echo ""
	@echo "then use it in python:"
	@echo "  from factverifai import fact_check"
	@echo "  fact_check('your claim here')"