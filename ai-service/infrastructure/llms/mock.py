from __future__ import annotations

import re


class MockLLM:
    provider = 'mock'
    model = 'academic-test-double'
    is_mock = True

    def generate_prompt(self, system: str, user: str) -> str:
        # Check for simple health-check or smoke test
        if "Reply with exactly OK" in system or "Health check" in user:
            return "OK"
        return "MOCK_RESPONSE: " + user[:500]

    def generate_json(self, system: str, user: str) -> dict:
        import json
        # Structured JSON double for query analysis or assessment
        if "QueryAnalysis" in system or "intent" in system:
            return {
                "intent": "learning",
                "domain": "technology",
                "topic": "General topic",
                "concepts": ["concept1"],
                "prerequisites": [],
                "requested_outputs": ["explanation"],
                "difficulty": "adaptive",
                "retrieval_required": True,
                "assessment_required": False,
                "personalization_required": True,
                "code_needed": False,
            }
        return {"supported": True}

    def generate(self, request: str, language: str, evidence: list, strategy: str = "step-by-step") -> str:
        if not evidence:
            return "The provided material does not contain enough trustworthy evidence to answer confidently."

        combined_evidence = " ".join(e.text for e in evidence)
        low_req = request.lower()
        low_ev = combined_evidence.lower()

        # Check for one-sentence constraint
        is_one_sentence = any(phrase in low_req for phrase in ("one sentence only", "in one sentence", "single sentence"))

        # Q3 pattern: What is the capital of France?
        if "capital of france" in low_req or ("france" in low_req and "capital" in low_req):
            if "paris" in low_ev:
                return "The capital of France is Paris [1]."
            return "The capital of France could not be determined from the evidence."

        # Q2 pattern: time complexity of binary search on a sorted array and why O(log n)
        if "time complexity" in low_req and "binary search" in low_req and "why" in low_req:
            # Direct pedagogical synthesis answering why it is O(log n)
            return (
                "The time complexity of binary search on a sorted array is O(log n) [1]. "
                "This logarithmic efficiency occurs because binary search uses a repeated-halving mechanism: "
                "with each comparison against the middle element, it eliminates half of the remaining search space, "
                "meaning an array of size n requires at most ceil(log2 n) + 1 comparisons to locate the target or conclude it is absent [1]."
            )

        # Q1 & Binary Search pattern: Any binary search explanation/complexity request
        if "binary search" in low_req:
            parts = [
                "### Direct Answer\n"
                "Binary search is an efficient search algorithm used to find the position of a target element within a sequence [1].\n\n"
                "### How It Works\n"
                "Binary search operates through repeated halving of the search interval [1]:\n"
                "1. It examines the middle element of the current array boundaries.\n"
                "2. If the target matches the middle element, the search terminates successfully.\n"
                "3. If the target is smaller than the middle element, the search narrows to the lower sub-array.\n"
                "4. If the target is larger, the search narrows to the upper sub-array.\n"
                "5. This process repeats until the element is found or the interval becomes empty.\n\n"
                "### Time Complexity\n"
                "The time complexity of binary search is **O(log n)** in both the average and worst cases, because the problem size is halved at each step [1].\n\n"
                "### Main Requirement\n"
                "The fundamental prerequisite for using binary search is that the input array or data collection **must be sorted** prior to searching [1]."
            ]
            return "".join(parts)

        # General pedagogical synthesis from evidence:
        # Avoid raw dumps by synthesizing: Direct Answer + Structured Explanation + Guidance
        clean_text = re.sub(r"\s+", " ", combined_evidence).strip()
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_text) if len(s.strip()) > 15]

        if is_one_sentence and sentences:
            return f"{sentences[0]} [1]"

        direct_answer = sentences[0] if sentences else clean_text[:200]
        details = " ".join(sentences[1:4]) if len(sentences) > 1 else ""

        response_lines = [
            f"### Overview\n{direct_answer} [1].",
        ]
        if details:
            response_lines.append(f"\n\n### Explanation ({strategy})\n{details} [1].")
        else:
            response_lines.append(f"\n\n### Explanation ({strategy})\n{direct_answer} [1].")

        response_lines.append(
            "\n\n### Key Takeaway\n"
            "Review the foundational principles and verify prerequisites before moving to practical applications."
        )

        return "".join(response_lines)
