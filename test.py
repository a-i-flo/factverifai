#%%
import os
import re
import json
import time
from pathlib import Path
from datetime import datetime
from textwrap import dedent
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional
from rich.console import Console
from rich.markdown import Markdown


from dotenv import load_dotenv
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain_exa.tools import ExaSearchResults

from exa_py import Exa
#%%
exa_client = Exa(api_key="213af424-ea0e-42d9-b852-9b48f74cb07b")

exa_tool = ExaSearchResults(
    client=exa_client,
    exa_api_key="213af424-ea0e-42d9-b852-9b48f74cb07b",
)
llm = OllamaLLM(model="llama3.1")
text = 'Trump is dead'
#rephrased_claim = llm.invoke(rephrase_prompt.format(claim=claim)).strip()
search_response = exa_tool.run({
    "query": text,
    "num_results": 5
})
# %%
search_response
# %%
