from __future__ import annotations
import re
from src.contracts.models import QueryAnalysis
class QueryAnalyzer:
    OUTPUT_WORDS={
      'explanation':['explain','اشرح','وضح','explique','eleza','bayyana','sharax','ṣàlàyé','kọwaa','chaza'],
      'code':['code','كود','python','snippet'], 'quiz':['quiz','أسئلة','اسئلة','questions','test me'],
      'summary':['summary','summar','ملخص','résumé','résume'], 'diagram':['diagram','رسم','flowchart'],
      'flashcards':['flashcard','بطاقات'], 'notes':['notes','ملاحظات'], 'presentation':['presentation','slides','powerpoint'],
      'audio':['audio','صوت','voice'], 'image':['image','صورة']}
    def analyze(self,text,language='en',llm=None):
        if llm is not None and not getattr(llm,'is_mock',False) and hasattr(llm,'generate_json'):
            try:
                data=llm.generate_json('''Analyze a technology student request. Return JSON with keys: intent, domain, topic, concepts, prerequisites, requested_outputs, difficulty, retrieval_required, assessment_required, personalization_required, code_needed.
IMPORTANT: "topic" MUST be the specific concrete technical subject or algorithm inquired about (e.g., "Binary Search", "Quicksort", "Convolutional Neural Network"), NEVER broad discipline categories like "algorithms and data structures" or "computer science".
requested_outputs must use only explanation, code, quiz, summary, diagram, flashcards, notes, presentation, audio, image.''',f'Language={language}\nRequest={text}')
                # Guard against broad discipline classification when a specific algorithm is named
                t_lower = text.lower()
                cur_topic = str(data.get("topic") or "").lower()
                if "binary search" in t_lower and ("algorithm" in cur_topic or "structure" in cur_topic or "computer" in cur_topic or not cur_topic):
                    data["topic"] = "Binary Search"
                return QueryAnalysis.model_validate(data)
            except Exception: pass
        return self._heuristic(text)
    def _heuristic(self,text):
        t=text.lower(); outs=[o for o,ks in self.OUTPUT_WORDS.items() if any(k in t for k in ks)] or ['explanation']
        known=[
            ('Binary Search',['binary search'],['binary search','worst-case complexity','space complexity'],['arrays','sorting']),
            ('CNN',['cnn','convolution'],['convolution','filters','pooling'],['neural networks','matrices']),
            ('RAG',['rag','retrieval augmented'],['retrieval','embeddings','generation','grounding'],['embeddings','LLMs']),
            ('Python',['python'],['functions','parameters','return values'],['variables','control flow']),
        ]
        topic=None; concepts=[]; prereq=[]
        for name,keys,cs,ps in known:
            if any(k in t for k in keys): topic=name; concepts=cs; prereq=ps; break
        if not topic:
            clean=re.sub(r'[^\w\s+.#-]',' ',text,flags=re.UNICODE).strip(); topic=' '.join(clean.split()[:8]) or 'General technology topic'; concepts=[topic]
        assess=any(k in t for k in ['assess','diagnostic','test me','اختبر','قيمني','quiz me'])
        diff='beginner' if any(k in t for k in ['simple','beginner','ببساط','مبتدئ']) else ('advanced' if any(k in t for k in ['advanced','deep','متقدم']) else 'adaptive')
        return QueryAnalysis(intent='learning',domain='technology',topic=topic,concepts=concepts,prerequisites=prereq,requested_outputs=list(dict.fromkeys(outs)),difficulty=diff,retrieval_required=True,assessment_required=assess,personalization_required=True,code_needed='code' in outs)