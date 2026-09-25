from __future__ import annotations
from src.contracts.models import RoutingDecision
LANG_FIT={'gemini':{'en':1,'ar':.95,'fr':.95,'sw':.84,'ha':.76,'am':.74,'so':.76,'yo':.72,'ig':.72,'zu':.80},'openai':{'en':1,'ar':.96,'fr':.97,'sw':.86,'ha':.78,'am':.76,'so':.78,'yo':.76,'ig':.76,'zu':.82},'anthropic':{'en':1,'ar':.93,'fr':.96,'sw':.82,'ha':.72,'am':.70,'so':.72,'yo':.70,'ig':.70,'zu':.77},'groq':{'en':.96,'ar':.88,'fr':.90,'sw':.78,'ha':.68,'am':.64,'so':.68,'yo':.66,'ig':.66,'zu':.72},'mock':{'en':.5,'ar':.5,'fr':.5,'sw':.5,'ha':.5,'am':.5,'so':.5,'yo':.5,'ig':.5,'zu':.5}}
TASK_FIT={'explanation':{'openai':1.0,'gemini':.98,'anthropic':.98,'groq':.90,'mock':.4},'code':{'openai':1.0,'gemini':.99,'anthropic':.96,'groq':.93,'mock':.4},'quiz':{'openai':.97,'gemini':.98,'anthropic':.98,'groq':.88,'mock':.4},'summary':{'openai':.96,'gemini':.98,'anthropic':.99,'groq':.90,'mock':.4},'notes':{'openai':.97,'gemini':.98,'anthropic':.99,'groq':.90,'mock':.4},'flashcards':{'openai':.96,'gemini':.98,'anthropic':.97,'groq':.90,'mock':.4},'diagram':{'openai':.90,'gemini':.94,'anthropic':.88,'groq':.82,'mock':.4},'presentation':{'openai':.95,'gemini':.97,'anthropic':.94,'groq':.85,'mock':.4}}
class ModelRouter:
    def __init__(self,providers): self.providers=providers if isinstance(providers,dict) else {getattr(providers,'provider','unconfigured'):providers}
    def route(self,tasks,language='en'):
        decisions=[]
        for task in tasks:
            best=None
            for name,llm in self.providers.items():
                lang=LANG_FIT.get(name,{}).get(language,.5); taskfit=TASK_FIT.get(task,{}).get(name,.75); score=.60*taskfit+.35*lang+.05; candidate=(score,name,llm,lang)
                if best is None or candidate[0]>best[0]: best=candidate
            if best:
                score,name,llm,lang=best; decisions.append(RoutingDecision(task=task,capability=task,provider=name,model=getattr(llm,'model','unknown'),routing_score=round(score,3),fallback=False,validation_state='configured',language_fit=lang))
            else: decisions.append(RoutingDecision(task=task,capability=task,provider='unconfigured',model='none',routing_score=0,fallback=False,validation_state='unavailable',language_fit=0))
        return decisions
    def status(self):
        active=[k for k,v in self.providers.items() if k!='unconfigured' and not getattr(v,'is_mock',False)]
        mocks=[k for k,v in self.providers.items() if getattr(v,'is_mock',False)]
        return {'active_providers':active,'mock_providers':mocks,'multi_provider_mode':len(active)>=2}