#%%
import os
import re
import json
import time
from datetime import datetime
from textwrap import dedent
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional
from rich.console import Console
from rich.markdown import Markdown
from dotenv import load_dotenv

from langchain_ollama import OllamaLLM
from openai import OpenAI
from exa_py import Exa
from langchain_exa.tools import ExaSearchResults

# LLM Wrapper 

class LLMWrapper:
    def __init__(
        self,
        backend="ollama",
        model="llama3.1",
        openai_api_key=None,
        openai_base_url=None
    ):
        self.backend = backend
        self.model = model
        if backend == "openai":
            self.client = OpenAI(
                base_url=openai_base_url or "https://api.openai.com/v1",
                api_key=openai_api_key,
            )
        elif backend == "ollama":
            self.llm = OllamaLLM(model=model)
        else:
            raise ValueError("backend must be either 'ollama' or 'openai'")

    def invoke(self, prompt):
        if self.backend == "ollama":
            return self.llm.invoke(prompt).strip()
        elif self.backend == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return response.choices[0].message.content.strip()
        else:
            raise ValueError("backend must be either 'ollama' or 'openai'")

#  Utilities 

def parse_claims_to_list(claims_str: str) -> List[str]:
    return re.findall(r"\d+\.\s*(.+)", claims_str)

def process_search_response_parallel(search_response, max_tokens=1000, max_workers=4) -> str:
    if hasattr(search_response, 'results'):
        results_list = search_response.results
    elif isinstance(search_response, dict) and 'results' in search_response:
        results_list = search_response['results']
    else:
        raise TypeError("search_response must contain an iterable list of results under 'results' attribute or key.")

    def process_single_result(result):
        try:
            result_str = json.dumps(result, ensure_ascii=False, indent=2)
        except TypeError:
            result_str = str(result)
        max_chars = max_tokens * 4
        return result_str[:max_chars]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        processed = list(executor.map(process_single_result, results_list))
    valid_results = [r for r in processed if r and r.strip()]
    return "\n\n".join(valid_results)

#  Main Pipeline 

def fact_check(
    text: str,
    model: str = "llama3.1",
    exa_results: int = 5,
    treat_input_as_single_claim: bool = False,
    max_workers: int = None,
    verbose: bool = False,
    exa: str = None,
    llm_backend: str = "ollama",  # "ollama" or "openai"
    openai_api_key: str = None,
    openai_base_url: str = None,
) -> dict:
    start_time = time.time()
    #  LLM and Search Setup 
    llm = LLMWrapper(
        backend=llm_backend,
        model=model,
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
    )
    exa_client = Exa(api_key=exa)
    exa_tool = ExaSearchResults(
        client=exa_client,
        exa_api_key=exa,
    )

    #  Claim Extraction 
    if treat_input_as_single_claim:
        claims_list = [text.strip()]
        original_claims = [text.strip()]
    else:
        extract_claims_prompt = dedent("""
            Given the text below, extract the most important, discrete, fact-checkable claim(s).
            - If the text is about a single event (even if it has multiple details in one sentence), condense it into one main claim that captures the central meaning.
            - Only split into separate claims if the text contains clearly unrelated facts.
            - Ignore trivial details (such as dates or years) if they are obvious from context.
            - Return a numbered list, one claim per line.
            - Only return claims that could be independently fact-checked.
            - If only one important claim exists, return just "1. [the main claim]".

            Text:
            {text}
        """).format(text=text)

        claims_output = llm.invoke(extract_claims_prompt)
        claims_list = parse_claims_to_list(claims_output)
        original_claims = [text.strip()] * len(claims_list)
        if not claims_list:
            print("No fact-checkable claims found.")
            return {}

    if verbose:
        print(f"\n[INFO] Fact-checking {len(claims_list)} claim(s)...\n")

    rephrase_prompt_template = dedent("""
        Rephrase the following claim as a concise, neutral, single-sentence statement for use as a web-search query.
        Do NOT evaluate the truthfulness or accuracy of the claim.
        Do NOT phrase it as a question.
        Do NOT add explanations or extra information.
        Keep all specific details intact.

        Claim:
        {claim}
    """)

    factcheck_prompt_template = dedent("""
        You are FactCheckAI, an expert fact-checker. Below is a set of search results and news excerpts (processed_output). Your task is to check the claim using ONLY the information in these results. 

        ***IMPORTANT:***
        - DO NOT mention any websites, URLs, or sources that do not appear in the evidence below.
        - DO NOT reference any knowledge outside of what is shown in the evidence.
        - If you cannot find at least three independent pieces of evidence (three unique URLs) in the provided text, write: "Insufficient evidence to fact-check this claim."
        - List all quotes and references directly from the provided processed_output.
        - **WARNING: You must only use the evidence above. If you reference any source, quote, or information not shown above, you will be penalized. Do NOT mention BBC, Guardian, Sky News, or any site not in EVIDENCE above.**

        
        **EVIDENCE:**
        {processed_output}
        

        Now, create a fact-checking report in the following format (filling in all sections):

        ## The Claim
        {claim}

        ## Agent Reasoning (step by step)
        [Explain step by step how you evaluated the evidence. DO NOT mention sources not present in EVIDENCE above.]

        ## Accuracy Score (0 = Completely False, 100 = Clearly Accurate)
        **Score:** [Assign a value from 0-100 based only on the EVIDENCE above.]
                                             
        ## Justification [Summarize why the claim is accurate or inaccurate, based ONLY on the provided EVIDENCE.] 

        ## References
        [List at least three unique URLs from EVIDENCE above. For each, quote a key sentence that supports or refutes the claim. If fewer than three, state: "Insufficient evidence to fact-check this claim."]
    """)

    all_reports = [None] * len(claims_list)
    today = datetime.now().strftime("%Y-%m-%d")

    def process_single_claim(claim, idx=None):
        t0 = time.time()
        rephrased_claim = llm.invoke(rephrase_prompt_template.format(claim=claim))
        search_response = exa_tool.run({
            "query": rephrased_claim,
            "num_results": exa_results
        })
        processed_output = process_search_response_parallel(search_response)
        report = llm.invoke(factcheck_prompt_template.format(
            claim=claim,
            rephrased_claim=rephrased_claim,
            processed_output=processed_output,
            current_date=today
        ))
        # --- Extract justification right here! ---
        justification_match = re.search(
            r"##\s*Justification[^\n]*\n+(.*?)(?:\n+##\s*References|\Z)",
            report,
            re.DOTALL | re.IGNORECASE
        )
        justification = justification_match.group(1).strip() if justification_match else ""
        t1 = time.time()
        if verbose:
            header = f"\n=== Claim {idx+1 if idx is not None else ''} ==="
            print(header)
            print("Claim:", claim)
            print("Justification:", justification)
            print(f"Time to search and compose report: {t1-t0:.2f} seconds\n")
        return {
            "report": report,
            "rephrased_claim": rephrased_claim
        }


    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_single_claim, claim, idx): idx for idx, claim in enumerate(claims_list)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                result = future.result()
                all_reports[idx] = result
            except Exception as e:
                all_reports[idx] = {"report": f"Error processing claim: {e}", "rephrased_claim": ""}

    structured = {}
    for idx, result_item in enumerate(all_reports):
        report = result_item["report"]
        rephrased_claim = result_item["rephrased_claim"]
        original_claim = original_claims[idx]

        score_match = re.search(r"\*\*Score:\*\*\s*\[?(\d+)", report)
        accuracy = int(score_match.group(1)) if score_match else None

        justification_match = re.search(
            r"##\s*Justification[^\n]*\n+(.*?)(?:\n+##\s*References|\Z)",
            report,
            re.DOTALL | re.IGNORECASE
        )
        justification = justification_match.group(1).strip() if justification_match else ""

        references_match = re.search(r"## References\s*(.*)", report, re.DOTALL)
        references_raw = references_match.group(1).strip() if references_match else ""
        url_list = re.findall(r'https?://\S+', references_raw)

        structured[f"claim{idx+1}"] = {
            "original": original_claim,
            "rephrased": rephrased_claim,
            "accuracy": accuracy,
            "justification": justification,
            "references": url_list
        }

    elapsed = time.time() - start_time
    if verbose:
        print(f"\n[INFO] Processed {len(claims_list)} claim(s) in {elapsed:.2f} seconds.\n")
    else:
        print(f"\nProcessed {len(claims_list)} claim(s) in {elapsed:.2f} seconds.")

    return structured

#%%


# %%


# %%
