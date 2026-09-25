from __future__ import annotations
class SentenceTransformerEmbeddings:
    name='sentence-transformers'
    is_mock=False
    def __init__(self,model_name='intfloat/multilingual-e5-small'):
        from sentence_transformers import SentenceTransformer
        self.model_name=model_name; self.model=SentenceTransformer(model_name)
    def embed(self,text): return self.model.encode('query: '+text,normalize_embeddings=True).tolist()
    def embed_document(self,text): return self.model.encode('passage: '+text,normalize_embeddings=True).tolist()