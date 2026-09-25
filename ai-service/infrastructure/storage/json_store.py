import json,threading,os,tempfile
from pathlib import Path
from src.contracts.models import Student,StudentProfile
class JsonProfileStore:
    def __init__(self,root='data/profiles'):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True); self.lock=threading.Lock()
    def _path(self,student_id):
        safe=''.join(c for c in student_id if c.isalnum() or c in ('-','_','.'))
        if not safe or safe!=student_id: raise ValueError('Invalid student_id')
        return self.root/f'{safe}.json'
    def save(self,p:StudentProfile):
        target=self._path(p.student.student_id)
        with self.lock:
            fd,tmp=tempfile.mkstemp(prefix=target.name+'.',suffix='.tmp',dir=str(self.root)); os.close(fd)
            Path(tmp).write_text(p.model_dump_json(indent=2),encoding='utf-8'); os.replace(tmp,target)
    def load(self,student_id:str):
        f=self._path(student_id)
        return StudentProfile.model_validate_json(f.read_text(encoding='utf-8')) if f.exists() else None
    def get_or_create(self,s:Student):
        p=self.load(s.student_id)
        if p is None: p=StudentProfile(student=s); self.save(p)
        elif p.student != s:
            p.student=s; self.save(p)
        return p