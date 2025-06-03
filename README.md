# FactVerfAI

Is a Python package that enables robust, automated fact-checking of claims and statements using the latest open-source LLMs and web search APIs. Given any text, FactVerifAI intelligently extracts one or more fact-checkable claims, queries the web for evidence, and generates a json output fact-checking report with references. The package supports parallel processing for faster performance. It is ideal for journalists, researchers, developers, and anyone who wants to automate claim verification in a reproducible, auditable way. It supports local hosted LLMs via [Ollama](https://ollama.com) and Open AI backends. 

---


To install the package:

```
pip install factverifai
```

## How to use
- Create new .env example from .env.example and paste EXA api key
- (Optional) add Open AI api key here.


### How to use with Open AI
```
import os
from dotenv import load_dotenv
from factverifai import fact_check

load_dotenv()

text = "British cuisine is the best in the world."

result = fact_check(
    text,
    model="albert-small",
    llm_backend="openai",
    max_workers=4,
    verbose=True,
    exa=os.getenv('EXA_API_KEY'),
    openai_api_key=os.getenv('ALBERT_API_KEY'),
    openai_base_url="https://albert.api.etalab.gouv.fr/v1"
)
```

### How to use with Ollama (local LLM)
```
import os
from dotenv import load_dotenv
from factverifai import fact_check

load_dotenv()

text = "Nicușor Dan is the president of Romania in 2025, winning against Simion"

result = fact_check(
    text,
    model="llama3.1",
    llm_backend="ollama",
    max_workers=4,
    verbose=True,
    exa=os.getenv('EXA_API_KEY'),
)
```

max_workers sets parallelism (higher is faster for many claims).

verbose=True enables detailed debug printing.

## Setup for developers


1. Create and install the environment and dependencies. This will:

Go to the folder where `factverifai` is and run the Makefile:

```bash
make
```

This will:
- Create a virtual environment named `factverifai-env` (if it doesn't already exist)
- Install `pip-tools` if necessary
- Compile and install both main and development dependencies
- Add a Jupyter kernel for the virtual environment (if not already added)

2. Activate the environment: 
```
source factverifai-env/bin/activate
```

3. Configure Ollama or OPEN AI

Visit the Ollama website https://ollama.com/download and download the latest version.

Install the version used in this project
```
ollama pull llama3.1
```

Or register for an [OPEN AI](https://platform.openai.com/api-keys)  api key. 

4. Register for an Exa Api Key

Register on the [Exa](https://dashboard.exa.ai/playground) website and generate an API key. 


5. Configure Secrets
Make a copy of the `.env.example` file and save it as `.env`inside the  factverify folder.
Add the `EXA_API_KEY` and your Open AI api key (if required) to your `.env` file.

> **Note:**
> If a new key or variable is added to the `.env` file, make sure to update the `.env.example` file as well. This ensures others know what environment variables are needed without exposing actual secrets.


## Managing dependencies

In this project, main dependencies are those required for the core functionality of the project and are necessary for both development and production environments. These should be added to requirements.in. On the other hand, development dependencies are only needed during development (e.g., testing tools, linters, and debuggers). These should be added to requirements-dev.in. By keeping them separate, we ensure that production environments remain lean and only contain essential packages, while development environments have everything needed for effective development and testing.

To manage and install dependencies, you can use the provided Makefile. It offers the following targets:

- `make` — Installs both main and development dependencies.
- `make requirements` — Installs main dependencies from `requirements.in`.
- `make dev-requirements` — Installs development dependencies from `requirements-dev.in`.


- **For main dependencies** (needed for both development and production):
  - If you want to add a library to the main installation, add the package name to `requirements.in`.
  - Run `make requirements` to install them.

- **For development dependencies** (only needed during development):
  - If you are exploring libraries and want to add them for development purposes, add the library to `requirements-dev.in`.
  - Run `make dev-requirements` to install them.

- **To install all dependencies** (both main and development):
  - Run `make` to install everything.

