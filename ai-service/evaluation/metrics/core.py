def precision_at_k(retrieved,relevant,k): return len(set(retrieved[:k])&set(relevant))/max(1,k)
def recall_at_k(retrieved,relevant,k): return len(set(retrieved[:k])&set(relevant))/max(1,len(relevant))
def hit_at_k(retrieved,relevant,k): return float(bool(set(retrieved[:k])&set(relevant)))
def mrr(retrieved,relevant):
    for i,x in enumerate(retrieved,1):
        if x in relevant:return 1/i
    return 0.0
def citation_validity(citations,evidence_sources): return sum(any(s in c for s in evidence_sources) for c in citations)/max(1,len(citations))