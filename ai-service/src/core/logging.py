import json,logging,re
_SECRET=re.compile(r'(api[_-]?key|token|password|authorization|secret)',re.I)
def redact(v):
    if isinstance(v,dict): return {k:('***REDACTED***' if _SECRET.search(k) else redact(x)) for k,x in v.items()}
    if isinstance(v,list): return [redact(x) for x in v]
    return v
class JsonFormatter(logging.Formatter):
    def format(self,r):
        return json.dumps(redact({'level':r.levelname,'message':r.getMessage(),'request_id':getattr(r,'request_id',None),'student_id':getattr(r,'student_id',None),'session_id':getattr(r,'session_id',None),'pipeline_stage':getattr(r,'pipeline_stage',None)}),ensure_ascii=False)
def get_logger(name='academic_ai'):
    l=logging.getLogger(name)
    if not l.handlers:
        h=logging.StreamHandler(); h.setFormatter(JsonFormatter()); l.addHandler(h); l.setLevel(logging.INFO)
    return l