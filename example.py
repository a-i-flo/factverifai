
#%%
import os
from factverifai import fact_check
from dotenv import load_dotenv
load_dotenv()

text = 'Mongolia PM resigns after public fury. British cuisine is the best in the world. Belgium has better cheese than the France.'

#%%
# To use Open AI:
result_openai = fact_check(
    text,
    model="albert-small",
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
