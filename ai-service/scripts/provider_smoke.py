from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from src.orchestration.factory import build_system


def main():
    ai = build_system(test_mode=False)

    real = [
        provider
        for provider in ai.llms.values()
        if not getattr(provider, "is_mock", False)
        and getattr(provider, "provider", "") != "unconfigured"
    ]

    if not real:
        print(
            "SKIPPED: no real LLM provider credentials configured"
        )
        return 2

    failed = 0

    for provider_instance in real:
        provider = getattr(
            provider_instance,
            "provider",
            "unknown",
        )

        model = getattr(
            provider_instance,
            "model",
            "unknown",
        )

        print("\n" + "=" * 70)
        print(f"Testing provider: {provider}")
        print(f"Model: {model}")
        print("=" * 70)

        try:
            result = provider_instance.smoke()
            print(result)

        except Exception as exc:
            failed += 1

            print(
                {
                    "provider": provider,
                    "model": model,
                    "success": False,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())