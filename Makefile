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

postinstall: create-env
	$(ENV_NAME)/bin/python -m spacy download en_core_web_sm

activate:
	@echo "To activate, run: source $(ENV_NAME)/bin/activate"

clean:
	rm -rf $(ENV_NAME) dist/ *.egg-info __pycache__ factverifai/__pycache__ factverifai/*.egg-info

build: create-env
	$(ENV_NAME)/bin/python -m build

publish: build
	$(ENV_NAME)/bin/twine upload dist/*
