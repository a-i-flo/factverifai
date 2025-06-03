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

# load environment variables
load_dotenv()

# llm model defaults
LOCAL_LLM_MODEL = os.getenv('LOCAL_LLM_MODEL')
DEFAULT_EXA_RESULTS = int(os.getenv('DEFAULT_EXA_RESULTS', '5'))
DEFAULT_MAX_WORKERS = int(os.getenv('DEFAULT_MAX_WORKERS', '4'))

# ---------- Utilities ----------

def timestamp_filename(prefix="fact_check", extension=".md") -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{prefix}_{timestamp}{extension}"

def ensure_dir(path: str):
    Path(path).mkdir(exist_ok=True, parents=True)

def parse_claims_to_list(claims_str: str) -> List[str]:
    """Extracts numbered claims from LLM output."""
    return re.findall(r"\d+\.\s*(.+)", claims_str)

def extract_urls(text: str) -> List[str]:
    return re.findall(r'https?://\S+', text)

def fetch_url_content(url: str, max_chars=1500) -> str:
    import requests
    try:
        response = requests.get(url, timeout=7)
        return response.text[:max_chars]
    except Exception:
        return f"Could not fetch content from {url}"

def process_search_response_parallel(search_response, max_tokens=1000, max_workers=4) -> str:
    """Processes each result in parallel, trims the result string representation."""
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
        max_chars = max_tokens * 4  # Rough token-to-char estimate
        return result_str[:max_chars]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        processed = list(executor.map(process_single_result, results_list))
    valid_results = [r for r in processed if r and r.strip()]
    return "\n---\n".join(valid_results)

# ---------- Core Fact-Checking Logic ----------
def process_single_claim(
    claim, llm, exa_tool, rephrase_prompt, factcheck_prompt, exa_results, today, verbose=False, idx=None
):
    import time
    t0 = time.time()
    rephrased_claim = llm.invoke(rephrase_prompt.format(claim=claim)).strip()
    search_response = exa_tool.run({
        "query": rephrased_claim,
        "num_results": exa_results
    })
    processed_output = process_search_response_parallel(search_response)
    report = llm.invoke(
        factcheck_prompt.format(
            claim=claim,
            rephrased_claim=rephrased_claim,
            processed_output=processed_output,
            current_date=today
        )
    )
    t1 = time.time()
    if verbose:
        header = f"\n=== Claim {idx+1 if idx is not None else ''} ==="
        print(header)
        print("Claim:", claim)
        print("Rephrased:", rephrased_claim)
        print(f"Time to search and compose report: {t1-t0:.2f} seconds\n")
    return report

def fact_check(
    text: str,
    output: str = "console",
    model: str = None,
    exa_results: int = None,
    treat_input_as_single_claim: bool = False,
    max_workers: int = None,
    verbose: bool = False,
    exa: str = None,
) -> list:
    """
    Main pipeline: extract claims, search, process evidence, fact-check (parallel for each claim).
    """
    import time
    start_time = time.time()
    
    # Use defaults from environment if not specified
    model = LOCAL_LLM_MODEL
    exa_results = exa_results or DEFAULT_EXA_RESULTS
    max_workers = max_workers or DEFAULT_MAX_WORKERS
    
    llm = OllamaLLM(model=model)
    exa_client = Exa(api_key=exa)
    exa_tool = ExaSearchResults(
        client=exa_client,
        exa_api_key=exa,
        )

    # Claim extraction
    if treat_input_as_single_claim:
        claims_list = [text.strip()]
    else:
        extract_claims_prompt = PromptTemplate(
            template=dedent("""
                Given the text below, extract the most important, discrete, fact-checkable claim(s).
                - If the text is about a single event (even if it has multiple details in one sentence), condense it into one main claim that captures the central meaning.
                - Only split into separate claims if the text contains clearly unrelated facts.
                - Ignore trivial details (such as dates or years) if they are obvious from context.
                - Return a numbered list, one claim per line.
                - Only return claims that could be independently fact-checked.
                - If only one important claim exists, return just "1. [the main claim]".

                Text:
                {text}
            """),
            input_variables=["text"]
        )

        extract_chain = extract_claims_prompt | llm
        claims_output = extract_chain.invoke({"text": text})
        claims_list = parse_claims_to_list(claims_output)
        if not claims_list:
            print("No fact-checkable claims found.")
            return []

    # Output destination print
    if verbose:
        if output == "console":
            print("\n[INFO] Output will be printed to the console.\n")
        else:
            print(f"\n[INFO] Output will be saved to folder: {output}\n")

    rephrase_prompt = PromptTemplate(
        template=dedent("""
            Rephrase the following claim as a concise, neutral, single-sentence statement for use as a web-search query.
            Do NOT evaluate the truthfulness or accuracy of the claim.
            Do NOT phrase it as a question.
            Do NOT add explanations or extra information.
            Keep all specific details intact.

            Claim:
            {claim}
        """),
        input_variables=["claim"]
    )

    factcheck_prompt = ChatPromptTemplate.from_template(dedent("""
        You are FactCheckAI, an expert fact-checker. Below is a set of search results and news excerpts (processed_output). Your task is to check the claim using ONLY the information in these results. 

        ***IMPORTANT:***
        - DO NOT mention any websites, URLs, or sources that do not appear in the evidence below.
        - DO NOT reference any knowledge outside of what is shown in the evidence.
        - If you cannot find at least three independent pieces of evidence (three unique URLs) in the provided text, write: "Insufficient evidence to fact-check this claim."
        - List all quotes and references directly from the provided processed_output.
        - **WARNING: You must only use the evidence above. If you reference any source, quote, or information not shown above, you will be penalized. Do NOT mention BBC, Guardian, Sky News, or any site not in EVIDENCE above.**

        ---
        **EVIDENCE:**
        {processed_output}
        ---

        Now, create a fact-checking report in the following format (filling in all sections):

        # [Write a compelling title for this fact-check]

        ## The Claim
        {claim}

        ## Rephrased Claim
        {rephrased_claim}

        ## Agent Reasoning (step by step)
        [Explain step by step how you evaluated the evidence. DO NOT mention sources not present in EVIDENCE above.]

        ## Inaccuracy Score (0 = Completely False, 100 = Clearly Accurate)
        **Score:** [Assign a value from 0-100 based only on the EVIDENCE above.]

        **Explanation:**  
        [Summarize why the claim is accurate or inaccurate, based ONLY on the provided EVIDENCE.]

        ## Evidence from the Web
        [List at least three unique URLs from EVIDENCE above. For each, quote a key sentence that supports or refutes the claim. If fewer than three, state: "Insufficient evidence to fact-check this claim."]

        ## References
        [List all URLs used in 'Evidence from the Web' above.]

        ---
        *Fact-checking report generated by FactCheckAI*
        *Date: {current_date}*
    """))

    today = datetime.now().strftime("%Y-%m-%d")
    all_reports = [None] * len(claims_list)

    # Parallel fact-check for each claim
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                process_single_claim,
                claim, llm, exa_tool, rephrase_prompt, factcheck_prompt, exa_results, today, verbose, idx
            ): idx for idx, claim in enumerate(claims_list)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                result = future.result()
                all_reports[idx] = result
            except Exception as e:
                all_reports[idx] = f"Error processing claim: {e}"

    if output == "console":
        for idx, report in enumerate(all_reports, 1):
            print(f"\n=== Fact-Check Report #{idx} ===\n")
            print(report)
            print("\n")
        print("End of Report\n")

    elif output == "pretty_print":
        console = Console()
        for idx, report in enumerate(all_reports, 1):
            console.rule(f"[bold cyan]Fact-Check Report #{idx}")
            console.print(Markdown(report))
            console.print("\n")
        console.rule("[green]End of Report")

    else:
        ensure_dir(output)
        fname = timestamp_filename(prefix="fact_check", extension=".md")
        file_path = Path(output) / fname
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n\n---\n\n".join(all_reports))
        print(f"Saved report to {file_path}")

    # Print timing
    elapsed = time.time() - start_time
    if verbose:
        print(f"\n[INFO] Processed {len(claims_list)} claim(s) in {elapsed:.2f} seconds.\n")
    else:
        print(f"\nProcessed {len(claims_list)} claim(s) in {elapsed:.2f} seconds.")

    return all_reports


def pretty_print(reports):
    """
    Pretty-print a list of Markdown reports to the terminal using rich.
    
    Args:
        reports (list[str]): List of Markdown-formatted report strings.
    """
    console = Console()
    for idx, report in enumerate(reports, 1):
        console.rule(f"[bold cyan]Fact-Check Report #{idx}")
        console.print(Markdown(report))
        console.print("\n")
    console.rule("[green]End of Report")

# %%
