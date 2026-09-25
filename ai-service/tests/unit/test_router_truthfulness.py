from src.model_routing.service import ModelRouter
class P:
    is_mock=False
    def __init__(self,provider,model):self.provider=provider;self.model=model

def test_multi_provider_status_is_truthful():
    r=ModelRouter({'openai':P('openai','o'),'anthropic':P('anthropic','a')})
    assert r.status()['multi_provider_mode'] is True
    assert set(r.status()['active_providers'])=={'openai','anthropic'}