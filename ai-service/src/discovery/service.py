from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any

@dataclass
class SourceStrategy:
    query: str
    domain: str
    preferred_categories: list[str]

DIRECTIVE_PATTERNS = [
    r'(?i)answer only from (?:relevant )?retrieved evidence[.,]?',
    r'(?i)ignore retrieved passages[^\n.!?]*[.,]?',
    r'(?i)if the retrieved evidence is insufficient[^\n.!?]*[.,]?',
    r'(?i)answer in one sentence only[.,]?',
    r'(?i)answer in a single sentence[.,]?',
    r'(?i)do not use (?:unrelated|external|general) (?:evidence|knowledge)[.,]?',
    r'(?i)do not mention (?:other )?algorithms[^\n.!?]*[.,]?',
    r'(?i)state (?:its|the) time complexity[^\n.!?]*[.,]?',
    r'(?i)mention the main requirement[^\n.!?]*[.,]?',
    r'(?i)explain how it works[.,]?',
]

def clean_query_for_search(text: str) -> str:
    cleaned = text
    for pattern in DIRECTIVE_PATTERNS:
        cleaned = re.sub(pattern, ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned or text

class SourceStrategyPlanner:
    def plan(self, query: str, topic: str, llm=None) -> SourceStrategy:
        clean_q = clean_query_for_search(query)
        if llm is not None and not getattr(llm, 'is_mock', False) and hasattr(llm, 'generate_json'):
            try:
                data = llm.generate_json(
                    'Plan trusted academic source discovery. Return JSON {"query":str,"domain":str,"preferred_categories":[str]}. Do not invent URLs. Use categories like official_documentation, standards, university, professional_research, peer_reviewed, recognized_medical_org, recognized_economic_org, government_science.',
                    f'Student question={clean_q}\nTopic={topic}'
                )
                q = str(data.get('query') or clean_q).strip()
                domain = str(data.get('domain') or 'technology').strip()
                cats = [str(x) for x in data.get('preferred_categories', []) if str(x).strip()]
                return SourceStrategy(q, domain, cats or ['university', 'professional_research', 'official_documentation'])
            except Exception:
                pass

        low = (clean_q + ' ' + (topic or '')).lower()
        if any(x in low for x in ['penicillin', 'antibiotic', 'medicine', 'clinical', 'health', 'disease', 'cell wall', 'pathogen']):
            cats = ['recognized_medical_org', 'peer_reviewed', 'university', 'government_science']
            domain = 'medicine and health'
        elif any(x in low for x in ['inflation', 'gdp', 'supply and demand', 'interest rate', 'central bank', 'purchasing power', 'economics']):
            cats = ['recognized_economic_org', 'government', 'university', 'peer_reviewed']
            domain = 'economics'
        elif any(x in low for x in ['photosynthesis', 'physics', 'quantum', 'chemistry', 'biology', 'light energy', 'glucose']):
            cats = ['peer_reviewed', 'university', 'government_science']
            domain = 'natural sciences'
        elif any(x in low for x in ['capital of', 'france', 'paris', 'geography', 'history']):
            cats = ['government', 'university', 'official_documentation']
            domain = 'general knowledge'
        elif any(x in low for x in ['tcp', 'http', 'network', 'congestion', 'protocol']):
            cats = ['standards', 'official_documentation', 'university']
            domain = 'computer networking'
        elif any(x in low for x in ['binary search', 'python', 'pytorch', 'tensorflow', 'sql', 'algorithm', 'cnn', 'rag']):
            cats = ['official_documentation', 'university', 'professional_research', 'standards']
            domain = 'computer science'
        else:
            cats = ['university', 'professional_research', 'official_documentation']
            domain = 'technology'
        return SourceStrategy(clean_q, domain, cats)

class TrustedDiscoveryService:
    def __init__(self, search_provider):
        self.search = search_provider
        self.planner = SourceStrategyPlanner()

    def discover(self, query: str, topic: str, llm=None) -> tuple[list[dict[str, Any]], str, SourceStrategy]:
        strategy = self.planner.plan(query, topic, llm)
        try:
            results = self.search.search(strategy.query, preferred_categories=strategy.preferred_categories)
        except TypeError:
            results = self.search.search(strategy.query)
        except Exception as exc:
            return [], f'unavailable:{type(exc).__name__}', strategy
        if not results:
            state = 'unavailable' if getattr(self.search, 'available', True) is False else 'no_trusted_results'
            return [], state, strategy
        return results, 'ready', strategy
