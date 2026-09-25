import hashlib,math,re
class DeterministicEmbeddingProvider:
    name='mock-hash-embedding'; is_mock=True
    def embed(self,text):
        v=[0.0]*64
        for w in re.findall(r'\w+',text.lower(),re.UNICODE): v[int(hashlib.sha256(w.encode()).hexdigest(),16)%64]+=1
        n=math.sqrt(sum(x*x for x in v)) or 1
        return [x/n for x in v]