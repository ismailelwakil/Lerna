from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from src.core.config import Settings
from infrastructure.search.trusted import TavilyTrustedSearch


def main():
    settings = Settings()

    if not settings.tavily_api_key:
        print(
            "SKIPPED: TAVILY_API_KEY not configured"
        )
        return 2

    search = TavilyTrustedSearch(
        settings.tavily_api_key,
        settings.trust_threshold,
    )

    results = search.search(
        "quantum teleportation university explanation",
        preferred_categories=[
            "university",
            "professional_research",
            "scientific_institute",
            "official_documentation",
        ],
    )

    if not results:
        print(
            "FAILED: no trusted results returned"
        )
        return 1

    for result in results[:3]:
        print(
            {
                "url": result["url"],
                "authority": result["authority"],
                "trust_score": result["trust_score"],
                "chars": len(result["text"]),
            }
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())