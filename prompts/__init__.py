"""
Prompts Package: YAML-based prompt templates for different goals and analysis types.
"""

import os
import yaml

_PROMPTS_DIR = os.path.dirname(__file__)


def load_prompts(filename: str) -> dict:
    """Load and return the parsed contents of a YAML prompt file."""
    path = os.path.join(_PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def get_prompt_for_goal(goal: str, domain: str = "youtube") -> dict:
    """
    Return the prompt block for *goal* from the appropriate domain YAML file.

    Supported domains: ``"youtube"`` (youtube_goals.yaml),
    ``"ecommerce"`` (ecommerce.yaml).
    """
    filename_map = {
        "youtube": "youtube_goals.yaml",
        "ecommerce": "ecommerce.yaml",
        "crm": "crm.yaml",
    }
    filename = filename_map.get(domain, f"{domain}.yaml")
    data = load_prompts(filename)
    prompts = data.get("prompts", data)
    if goal not in prompts:
        raise KeyError(f"Goal '{goal}' not found in domain '{domain}'")
    return prompts[goal]


__all__ = ["load_prompts", "get_prompt_for_goal"]
