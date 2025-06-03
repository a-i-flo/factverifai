
#%%
import os
from factverifai import fact_check
from dotenv import load_dotenv
load_dotenv()

text = """
Mongolia PM resigns after public fury. \n
British cuisine recently voted as number 1 food in Europe. \n
Hop to it, Space Hoppers to return as part of new green travel revolution. \n
Brilliant PSG demolish Inter Milan 4-0 to win first Champions League title.
"""
#%%
# To use Open AI:
result_openai = fact_check(
    text,
    model="albert-large",
    llm_backend="openai",
    max_workers=4,
    verbose=True,
    exa=os.getenv('EXA_API_KEY'),
    openai_api_key=os.getenv('ALBERT_API_KEY'),
    openai_base_url="https://albert.api.etalab.gouv.fr/v1"
)
result_openai
# %%
result_openai
#%%
# To use Ollama:
result_ollama = fact_check(
    text,
    model="llama3.1",
    llm_backend="ollama",
    max_workers=4,
    verbose=True,
    exa=os.getenv('EXA_API_KEY'),
)
result_ollama
# %%
print(os.getenv('ALBERT_API_KEY'))
# %%
