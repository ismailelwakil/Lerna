from __future__ import annotations
import html
import ipaddress
import os
import re
import socket
import urllib.parse
from html.parser import HTMLParser

REGISTRY = {
    # Official Technical Documentation & Standards
    'docs.python.org': ('official_documentation', 0.99),
    'developer.mozilla.org': ('official_documentation', 0.97),
    'pytorch.org': ('official_documentation', 0.99),
    'tensorflow.org': ('official_documentation', 0.99),
    'docs.microsoft.com': ('official_documentation', 0.96),
    'learn.microsoft.com': ('official_documentation', 0.96),
    'quantum.cloud.ibm.com': ('official_documentation', 0.96),
    'w3.org': ('standards', 0.99),
    'ietf.org': ('standards', 0.99),
    'rfc-editor.org': ('standards', 0.99),
    'iso.org': ('standards', 0.98),
    'nist.gov': ('standards', 0.99),
    'ansi.org': ('standards', 0.98),

    # Universities (Tier A)
    'mit.edu': ('university', 0.98),
    'stanford.edu': ('university', 0.98),
    'berkeley.edu': ('university', 0.98),
    'cmu.edu': ('university', 0.98),
    'harvard.edu': ('university', 0.98),
    'ox.ac.uk': ('university', 0.98),
    'cam.ac.uk': ('university', 0.98),
    'caltech.edu': ('university', 0.98),
    'princeton.edu': ('university', 0.98),
    'columbia.edu': ('university', 0.97),
    'cornell.edu': ('university', 0.97),
    'ethz.ch': ('university', 0.98),

    # Peer-reviewed Research & Professional Organizations (Tier A)
    'acm.org': ('professional_research', 0.98),
    'dl.acm.org': ('professional_research', 0.98),
    'ieee.org': ('professional_research', 0.98),
    'ieeexplore.ieee.org': ('professional_research', 0.98),
    'nature.com': ('peer_reviewed', 0.98),
    'science.org': ('peer_reviewed', 0.98),
    'cell.com': ('peer_reviewed', 0.97),
    'sciencedirect.com': ('peer_reviewed', 0.96),
    'springer.com': ('peer_reviewed', 0.95),
    'arxiv.org': ('research_preprint', 0.84),

    # Medicine & Healthcare (Tier A)
    'who.int': ('recognized_medical_org', 0.99),
    'cdc.gov': ('government_science', 0.99),
    'nih.gov': ('government_science', 0.99),
    'ncbi.nlm.nih.gov': ('peer_reviewed', 0.99),
    'pubmed.ncbi.nlm.nih.gov': ('peer_reviewed', 0.99),
    'fda.gov': ('government', 0.98),
    'nice.org.uk': ('recognized_medical_org', 0.98),
    'thelancet.com': ('peer_reviewed', 0.98),
    'nejm.org': ('peer_reviewed', 0.98),

    # Science & Space (Tier A)
    'nasa.gov': ('government_science', 0.98),
    'noaa.gov': ('government_science', 0.98),
    'cern.ch': ('government_science', 0.98),

    # Economics, Policy & International Organizations (Tier A)
    'worldbank.org': ('recognized_economic_org', 0.98),
    'imf.org': ('recognized_economic_org', 0.98),
    'oecd.org': ('recognized_economic_org', 0.98),
    'federalreserve.gov': ('government', 0.98),
    'ecb.europa.eu': ('government', 0.98),
    'bankofengland.co.uk': ('government', 0.98),

    # Recognized Technical Organizations (Tier B)
    'ibm.com': ('recognized_technical_org', 0.88),

    # Encyclopedias & General Reference (Tier C: Low-priority fallback)
    'wikipedia.org': ('encyclopedia_fallback', 0.45),
    'en.wikipedia.org': ('encyclopedia_fallback', 0.45),
}

HIGH_STAKES_DOMAINS = {'medicine', 'clinical', 'health', 'pharmacology', 'medical', 'toxicology'}

def is_wikipedia(url: str) -> bool:
    host = (urllib.parse.urlparse(url).hostname or '').lower()
    return 'wikipedia.org' in host

def trust(url: str) -> tuple[str, float]:
    host = (urllib.parse.urlparse(url).hostname or '').lower().removeprefix('www.')
    for d, (a, s) in REGISTRY.items():
        if host == d or host.endswith('.' + d):
            return a, s
    if host.endswith('.edu') or '.edu.' in host or host.endswith('.ac.uk') or '.ac.' in host:
        return 'university', 0.92
    if host.endswith('.gov') or '.gov.' in host:
        return 'government', 0.94
    if 'wikipedia.org' in host:
        return 'encyclopedia_fallback', 0.45
    return 'unverified', 0.25

def source_tier(authority: str) -> str:
    tier_a = {
        'official_documentation', 'standards', 'university', 'peer_reviewed',
        'professional_research', 'recognized_medical_org', 'recognized_economic_org',
        'government', 'government_science',
    }
    tier_b = {'recognized_technical_org', 'research_preprint'}
    if authority in tier_a:
        return 'A'
    if authority in tier_b:
        return 'B'
    if authority == 'encyclopedia_fallback':
        return 'C'
    return 'D'

def _public_host(host: str) -> bool:
    if not host or host in {'localhost', 'localhost.localdomain'}:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
                return False
        return True
    except Exception:
        return False

def validate_public_url(url: str) -> bool:
    p = urllib.parse.urlparse(url)
    if p.scheme not in {'http', 'https'} or p.username or p.password:
        return False
    return _public_host(p.hostname or '')

class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'noscript', 'svg'}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'noscript', 'svg'} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())

def clean_html(raw: str) -> str:
    p = _TextExtractor()
    p.feed(raw)
    text = ' '.join(p.parts)
    return re.sub(r'\s+', ' ', html.unescape(text)).strip()

class SafeWebFetcher:
    _cache: dict[str, dict] = {}

    def __init__(self, timeout=20, max_bytes=5_000_000):
        self.timeout = timeout
        self.max_bytes = max_bytes

    def fetch(self, url: str) -> dict:
        if not validate_public_url(url):
            raise RuntimeError('Rejected unsafe or non-public URL')
        if url in self._cache:
            return self._cache[url]
        import httpx
        with httpx.Client(follow_redirects=True, timeout=self.timeout, headers={'User-Agent': 'AcademicLearningBot/1.0'}) as client:
            last_err = None
            r = None
            for attempt in range(2):
                try:
                    r = client.get(url)
                    r.raise_for_status()
                    break
                except Exception as exc:
                    last_err = exc
                    if attempt == 1:
                        raise last_err
            if len(r.content) > self.max_bytes:
                raise RuntimeError('External source exceeds safe download limit')
            final = str(r.url)
            if not validate_public_url(final):
                raise RuntimeError('Redirected to unsafe URL')
            ctype = (r.headers.get('content-type') or '').lower()
            if 'text/html' in ctype or not ctype:
                text = clean_html(r.text)
                res = {'url': final, 'text': text, 'content_type': 'text/html'}
            elif 'text/plain' in ctype or 'text/markdown' in ctype:
                res = {'url': final, 'text': r.text, 'content_type': ctype}
            elif 'application/pdf' in ctype:
                from io import BytesIO
                from pypdf import PdfReader
                reader = PdfReader(BytesIO(r.content))
                text = '\n'.join((p.extract_text() or '') for p in reader.pages)
                res = {'url': final, 'text': text, 'content_type': 'application/pdf'}
            else:
                raise RuntimeError(f'Unsupported external MIME type: {ctype}')
            self._cache[url] = res
            return res

class NoWebSearch:
    is_mock = False
    available = False

    def search(self, topic, preferred_categories=None):
        return []

class TavilyTrustedSearch:
    is_mock = False
    available = True

    def __init__(self, api_key=None, trust_threshold=0.80):
        self.api_key = api_key or os.getenv('TAVILY_API_KEY')
        self.trust_threshold = trust_threshold
        self.fetcher = SafeWebFetcher()
        if not self.api_key:
            raise RuntimeError('TAVILY_API_KEY is required for live web discovery')

    def search(self, topic, preferred_categories=None):
        import httpx
        last_exc = None
        r = None
        for attempt in range(2):
            try:
                r = httpx.post(
                    'https://api.tavily.com/search',
                    json={
                        'api_key': self.api_key,
                        'query': topic,
                        'search_depth': 'advanced',
                        'max_results': 10,
                        'include_raw_content': False,
                    },
                    timeout=20,
                )
                r.raise_for_status()
                break
            except Exception as exc:
                last_exc = exc
                if attempt == 1:
                    raise last_exc
        out = []
        tier_a_found = False

        raw_results = r.json().get('results', [])
        for x in raw_results:
            url = x.get('url', '')
            authority, score = trust(url)
            if source_tier(authority) == 'A':
                tier_a_found = True

        for x in raw_results:
            url = x.get('url', '')
            authority, score = trust(url)

            # Wikipedia policy: if tier A exists, exclude Wikipedia completely
            if is_wikipedia(url) and tier_a_found:
                continue

            # Minimum trust threshold (Wikipedia allowed only if threshold permits and no tier A)
            if score < self.trust_threshold and not (is_wikipedia(url) and not tier_a_found):
                continue

            if preferred_categories and authority not in preferred_categories and source_tier(authority) != 'A':
                continue

            try:
                fetched = self.fetcher.fetch(url)
                text = fetched['text']
            except Exception:
                text = (x.get('content') or '').strip()
            if len(text) < 120:
                continue
            out.append({
                'title': x.get('title', ''),
                'url': url,
                'domain': urllib.parse.urlparse(url).hostname or '',
                'authority': authority,
                'trust_score': score,
                'text': text,
                'publisher': urllib.parse.urlparse(url).hostname or '',
            })
        return out

class MockTrustedSearch:
    is_mock = True
    available = True

    # Multi-domain authoritative academic fixtures for tests and offline validation
    KNOWLEDGE = {
        # CS / Technology
        'binary search': (
            'Binary search is an efficient search algorithm that finds the position of a target value within a sorted array. '
            'It works by repeatedly dividing the search space in half: comparing the target value to the middle element of the array. '
            'If the target equals the middle element, its position is returned. If the target is smaller, search continues in the lower half; '
            'if larger, in the upper half. The time complexity of binary search is O(log n) because the problem size is halved at each step. '
            'The fundamental requirement that must be satisfied before using binary search is that the input array or sequence must be sorted in order.',
            'https://mit.edu/6.006/notes/binary-search.html',
            'university',
            0.98,
        ),
        'cnn': (
            'Convolutional neural networks apply learned kernels or filters over local receptive fields to extract spatial features. '
            'Pooling operations (such as max pooling or average pooling) downsample feature maps and reduce spatial resolution.',
            'https://pytorch.org/docs/stable/nn.html',
            'official_documentation',
            0.99,
        ),
        'python': (
            'Python functions are defined with def and can receive positional and keyword parameters and return values using the return statement.',
            'https://docs.python.org/3/tutorial/controlflow.html#defining-functions',
            'official_documentation',
            0.99,
        ),
        'rag': (
            'Retrieval-augmented generation (RAG) combines external evidence retrieval with generation to ground model outputs in retrieved context and reduce hallucinations.',
            'https://arxiv.org/abs/2005.11401',
            'research_preprint',
            0.84,
        ),
        # Physics
        'quantum teleportation': (
            'Quantum teleportation transfers an unknown quantum state between two parties using shared quantum entanglement and a classical communication channel; '
            'it transmits the quantum state information without transporting physical matter itself.',
            'https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/entanglement-in-action/quantum-teleportation',
            'official_documentation',
            0.96,
        ),
        'teleportation': (
            'Quantum teleportation transfers an unknown quantum state using shared entanglement and classical communication; it does not transport matter.',
            'https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/entanglement-in-action/quantum-teleportation',
            'official_documentation',
            0.96,
        ),
        # Medicine / Healthcare
        'penicillin': (
            'Penicillin is an antibiotic that inhibits bacterial cell wall peptidoglycan synthesis, causing bacterial cell lysis. It is used to treat susceptible bacterial infections and is completely ineffective against viruses.',
            'https://www.who.int/medicines/publications/essentialmedicines/penicillin.html',
            'recognized_medical_org',
            0.99,
        ),
        # Economics
        'inflation': (
            'Inflation is a general and sustained increase in the overall price level of goods and services over time, eroding the purchasing power of money. Central banks typically regulate inflation through monetary policy and interest rate benchmarks.',
            'https://www.imf.org/en/Publications/fandd/issues/Series/Back-to-Basics/Inflation',
            'recognized_economic_org',
            0.98,
        ),
        # General Science
        'photosynthesis': (
            'Photosynthesis is the photochemical process by which green plants, algae, and cyanobacteria convert light energy into chemical energy, synthesizing glucose from water and carbon dioxide while releasing oxygen as a byproduct.',
            'https://www.nature.com/subjects/photosynthesis',
            'peer_reviewed',
            0.98,
        ),
        # General Knowledge
        'capital of france': (
            'Paris is the official capital and largest city of France, situated along the Seine River in the north-central part of the country. It is the center of French government and culture.',
            'https://www.diplomatie.gouv.fr/en/discovering-france/paris/',
            'government',
            0.96,
        ),
        'france': (
            'Paris is the official capital and largest city of France, situated along the Seine River in the north-central part of the country. It is the center of French government and culture.',
            'https://www.diplomatie.gouv.fr/en/discovering-france/paris/',
            'government',
            0.96,
        ),
    }

    # Near-miss adversarial fixtures (to verify that "binary search" on arrays does not accept "binary search tree", "treap", etc.)
    NEAR_MISSES = {
        'binary search tree': (
            'A binary search tree (BST) is a pointer-based binary tree data structure where each node stores a key and left/right child pointers, satisfying the BST property. It is distinct from binary search on a contiguous array.',
            'https://mit.edu/6.006/notes/bst.html',
            'university',
            0.96,
        ),
        'treap': (
            'A treap is a randomized Cartesian tree combining binary search tree keys with binary max-heap priorities.',
            'https://stanford.edu/class/archive/cs/cs166/cs166.1166/lectures/01/Small01.pdf',
            'university',
            0.95,
        ),
        'heap sort': (
            'Heap sort is an in-place sorting algorithm using a binary heap tree structure with O(n log n) worst-case time complexity.',
            'https://cmu.edu/15-210/lectures/heapsort.html',
            'university',
            0.95,
        ),
        'red-black tree': (
            'A red-black tree is a self-balancing binary search tree where each node maintains an extra color bit to ensure logarithmic height.',
            'https://berkeley.edu/cs61b/notes/red-black.html',
            'university',
            0.95,
        ),
    }

    def search(self, topic, preferred_categories=None):
        low = topic.lower()

        # Check for exact multi-word keys first
        for key, (text, url, auth, scr) in self.KNOWLEDGE.items():
            if key in low:
                domain = urllib.parse.urlparse(url).hostname or ''
                return [{
                    'title': topic,
                    'url': url,
                    'domain': domain,
                    'authority': auth,
                    'trust_score': scr,
                    'text': text,
                    'publisher': domain,
                }]

        # Check word-level match for single topics
        words = set(re.findall(r'[a-zA-Z]+', low))
        for key, (text, url, auth, scr) in self.KNOWLEDGE.items():
            key_words = set(key.split())
            if key_words.issubset(words):
                domain = urllib.parse.urlparse(url).hostname or ''
                return [{
                    'title': topic,
                    'url': url,
                    'domain': domain,
                    'authority': auth,
                    'trust_score': scr,
                    'text': text,
                    'publisher': domain,
                }]

        return []
