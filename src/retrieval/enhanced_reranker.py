# retrieval/enhanced_reranker.py
"""
Enhanced Retrieval Pipeline:
    Question
        │
        ▼
    HybridRetriever  (Vector 70% + BM25 30%)
        │   Top 20 candidates
        ▼
    CrossEncoderReranker  (ms-marco-MiniLM-L-6-v2, local)
        │   Score = 0.6 * CE_sigmoid + 0.4 * retrieval_score
        ▼
    Filter (threshold=0.35, keep ≥ 1)
        │   Top 5 context
        ▼
    LLM (Gemini)

Log minh bạch ở mỗi bước:
    [RETRIEVAL] doc_i  vector_score=X  bm25_score=Y  hybrid_score=Z
    [RERANK]    doc_i  ce_score=X  retrieval_score=Y  final_score=Z  → KEPT/DROPPED
    [CONTEXT]   Final N docs selected for LLM
"""

import math
import re
import os
import time
from typing import List, Tuple, Optional, Dict, Any
from langchain_core.documents import Document


# ── Constants ─────────────────────────────────────────────────────────────────
RETRIEVE_K      = 20    # số candidates từ HybridRetriever
RERANK_TOP_K    = 5     # số docs truyền vào LLM
RERANK_THRESHOLD = 0.35 # ngưỡng tối thiểu sau rerank
CE_WEIGHT       = 0.6   # trọng số cross-encoder score
RETRIEVAL_WEIGHT = 0.4  # trọng số retrieval score


# ── Cross-encoder singleton ───────────────────────────────────────────────────
_ce_model = None
_ce_load_attempted = False


def _load_cross_encoder():
    """Load cross-encoder lazily, chỉ 1 lần. Trả về None nếu thất bại."""
    global _ce_model, _ce_load_attempted
    if _ce_load_attempted:
        return _ce_model
    _ce_load_attempted = True
    try:
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "0")
        from sentence_transformers import CrossEncoder
        _ce_model = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            max_length=512,
        )
        print("✅ [Reranker] cross-encoder/ms-marco-MiniLM-L-6-v2 loaded")
    except Exception as e:
        print(f"⚠️  [Reranker] CrossEncoder load failed: {e}. Using heuristic fallback.")
        _ce_model = None
    return _ce_model


# ── Heuristic scorer (fallback) ───────────────────────────────────────────────
_VI_STOPWORDS = {
    'là', 'của', 'và', 'có', 'được', 'trong', 'với', 'cho', 'về',
    'một', 'các', 'những', 'này', 'đó', 'khi', 'như', 'từ', 'hay',
    'the', 'a', 'an', 'and', 'or', 'in', 'of', 'to', 'for',
}

_SYLLABUS_KEYWORDS = {
    'đề cương', 'tín chỉ', 'học phần', 'giảng viên', 'kiểm tra cuối kỳ',
    'syllabus', 'credit', 'course outline', 'thi trắc nghiệm', 'mshp',
}

_TECH_KEYWORDS = {
    'code', 'python', 'sklearn', 'scikit', 'numpy', 'pandas', 'matplotlib',
    'algorithm', 'function', 'implement', 'confusion', 'roc', 'auc',
    'thuật toán', 'lập trình', 'thư viện', 'hàm', 'mã nguồn',
}


def _tokenize(text: str) -> set:
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    return {w for w in text.split() if len(w) > 1 and w not in _VI_STOPWORDS}


def _heuristic_score(query: str, doc: Document) -> float:
    """Keyword overlap + position bonus. Range [0,1]."""
    q_tokens = _tokenize(query)
    d_tokens = _tokenize(doc.page_content)
    if not q_tokens:
        return 0.0

    overlap = len(q_tokens & d_tokens) / len(q_tokens)

    # Position bonus: keywords xuất hiện ở 1/3 đầu document
    first_third = doc.page_content[:len(doc.page_content) // 3].lower()
    pos_bonus = sum(0.05 for t in q_tokens if t in first_third)
    pos_bonus = min(pos_bonus, 0.2)

    # Section title bonus
    section = doc.metadata.get("section_title", doc.metadata.get("section", "")).lower()
    title_bonus = 0.15 if any(t in section for t in q_tokens) else 0.0

    # Syllabus penalty for technical queries
    is_tech = any(kw in query.lower() for kw in _TECH_KEYWORDS)
    d_lower = doc.page_content.lower()
    syl_penalty = 0.5 if is_tech and any(kw in d_lower for kw in _SYLLABUS_KEYWORDS) else 1.0

    return min(1.0, (overlap + pos_bonus + title_bonus)) * syl_penalty


# ── Main reranker class ───────────────────────────────────────────────────────
class EnhancedReranker:
    """
    Cross-Encoder Reranker với logging minh bạch.

    Scoring pipeline per document:
        retrieval_score   = score từ HybridRetriever (RRF/weighted)
        ce_score          = sigmoid(cross_encoder_logit)     ∈ [0,1]
        heuristic_score   = keyword overlap + bonuses        ∈ [0,1]
        base_score        = CE_WEIGHT * ce_score + (1-CE_WEIGHT) * heuristic_score
        final_score       = RETRIEVAL_WEIGHT * retrieval_score + (1-RETRIEVAL_WEIGHT) * base_score
    """

    def __init__(self):
        self._ce = None   # lazy load

    def _get_ce(self):
        if self._ce is None:
            self._ce = _load_cross_encoder()
        return self._ce

    def _ce_scores(self, query: str, docs: List[Document]) -> List[float]:
        """Batch predict cross-encoder scores. Fallback to 0.5 if model unavailable."""
        ce = self._get_ce()
        if ce is None:
            return [0.5] * len(docs)
        try:
            pairs = [(query, doc.page_content[:512]) for doc in docs]
            logits = ce.predict(pairs)
            return [1.0 / (1.0 + math.exp(-float(l))) for l in logits]
        except Exception as e:
            print(f"⚠️  [Reranker] CE predict error: {e}. Using 0.5 fallback.")
            return [0.5] * len(docs)

    def rerank(
        self,
       s
cs, scoredourn ]

    rete"scorval_["retrie"] = sdeval_scoreretritadata["c.me      doore"]
  = sd["ce_scce_score"] ["tadata doc.me       ]
_score"= sd["final] "ance_score"relevata[  doc.metad
      ults):cs, resp(do in zinal, sd)_, fior doc, (
    f dùngm có thểnstreaadata để dowetre vào m final_sco   # Inject

 results]d in _, _, sd for ores = [s]
    sc results d, _, _ in= [d for    docs  verbose)
hreshold,k, t top_with_scores,ery, docs_.rerank(quer = rerankults)
    resnker(t_rera = ge  reranker"""
  ts)
    s, score_dicdoc  (selected_ns:
       Return.

   ioctvenience fun-level conTop"""
    t]]]:
    t[str, floa[Dicistument], Le[List[Doc Tupl
) -> = True,e: bool  verbosESHOLD,
  = RERANK_THRat floeshold:     thrK,
 RERANK_TOP_ int =k:p_ to   float]],
nt, [Documest[Tupleres: Licoh_s  docs_wit str,
  query:
    ments(k_docueran


def rer_rerankurn _global    ret
anker()hancedRer= Ennker eraobal_r  _gl   s None:
   r irankef _global_re   iker
 l_reran_globabal 
    gloe."""ker instancton reran"""Single    eranker:
 EnhancedRr() ->keget_reranf ne


deNoer] = cedRerankhanional[EnOptker: _reran
_global────────────────────────────────────────────────ions ─────e funct─ Convenienc]


# ─sults_ in redoc, score, ) for re, scodocrn [(      retu)
  ld, verbose, threshocores, top_kith_sry, docs_wnk(que = self.rera     results]
   ents documr doc inc)) fo do(query,ic_scoreristdoc, _heu[(= res _with_sco       docse proxy
 ieval scoretrm ric làheuristùng # D    ""
        ")].
     final_scoret[(Document,ề Lis v   Trảres.
     rieval sco có retkhôngi khace terf inlifiedmp       Si  """
 ]:
      float]ument, uple[Doc[T   ) -> List= True,
 se: bool bo       verRESHOLD,
  = RERANK_TH: floatshold  thre      K_TOP_K,
ERANnt = Rp_k: i to
       ument],st[Docments: Licu  do    y: str,
        querlf,
        semple(
  erank_si  def r
  ction
l_selereturn fina       \n")

 60}{'─'*int(f" pr          ")
 sec} {[{src}]3f}  nal={score:.#{i}: fiext nt(f"  Cont      pri          )[:50]
ion", "")"sectdata.get(etae", doc.m_titl("sectionta.getada= doc.metec          s
        "?")ce_file",a.get("sourdattac = doc.me       sr
         on, 1):_selectinalmerate(fin enue, sd) i, scorr i, (doc        fo
    ms)")0f}000:. {elapsed*1rerank took"( f                "
   selected n)} docsioect_selnalXT]  {len(fiONTEf"\n[Crint(  p
          e:  if verbos
      e() - t0= time.timpsed 
        elap_k]
tot[:ection = kepnal_sel  fip-K
            # Tot

   besys keep# alwa  results[0]]    kept = [  
      :eptt k if no]
        threshold>=if s n results  s, sd isd) for d, [(d, s, t =
        kep, keep ≥ 1resholdthFilter by       # 

  ")sec}[{src}] {"{status}    f                      "
ore']:.3f})stic_scurih={sd['he        f"         "
      } .3fscore']:sd['ce_    f"ce={           "
       .3f}  ]:e'rieval_scort={sd['ret     f"(re            "
     nal:.3f}  ={fid}  final"  #{i:02     print(f       DROP"
      else "🗑ld l >= thresho fina and <= top_k" if i= "✅ KEPT    status          :35]
   ", ""))[t("sectionta.gemetadaoc._title", dion"sectget(c.metadata. sec = do               ")
 "?",urce_fileget("sooc.metadata.   src = d            s, 1):
 (resultenumeraten d) ial, s(doc, fin for i,       
     EIGHT}")EVAL_Weight={RETRIal_w retriev_WEIGHT} t={CEghei f"ce_w        
         L-6-v2  "co-MiniLM-el=ms-marmodn[RERANK]  t(f"\prin           
 if verbose:   
     ue)
=Tr], reverse x: x[1mbda.sort(key=lasults
        reescending Sort d
        #re_dict))
sco final, ppend((doc,  results.a       }
          
     d(final, 4),   roun  e":orsc "final_             se, 4),
      round(baore":  se_scba    "            h, 4),
ound(e": rscor"heuristic_               4),
  ce, round(     :  re"_sco      "ce          ,
r_score, 4)nd(: roucore""retrieval_s       
         re_dict = {   sco       

   * base_WEIGHT)ALRETRIEVe + (1 - * r_scorAL_WEIGHT al = RETRIEVin           f * h
 CE_WEIGHT)- 1 e + (EIGHT * cCE_W= e      bas    
   res):s, h_scos, ce_scoreeval_scoreetriip(docs, r, ce, h in zre r_scoc,   for do
     esults = []       rs
 re Final sco    #

    ocs]for doc in d, doc) _score(querystic= [_heurih_scores     res
    co Heuristic s     #   ocs)

y, des(quercor_ce_sself.ce_scores =         er scores
oss-encod   # Cr    

 {sec}")rc}] .3f}  [{se:{r_scorl=va  retrie"  #{i:02d} print(f      
         0], ""))[:4on"t("sectia.gemetadat, doc.tle"ection_tita.get("sadamet sec = doc.           ")
    file", "?rce_get("souoc.metadata.c = d         sr  
     s, 1):re_with_scoe(docsn enumerat i, r_score), (doc       for i"")
     [:60]}\"{query\for query: es idatocs)} cand(dRIEVAL] {len[RETint(f"          pr
  60}")"\n{'─'*  print(f     se:
      verbo   if
     ]
th_scoresdocs_wiin  for _, s _scores = [strieval  reres]
      with_scoocs_ _ in dor d,d f   docs = [     me.time()
 ti t0 =   
    []
 return 
           es:_scorcs_with do not
        if"    ""re}
    al_score, finc_scoe, heuristire, ce_scoral_scoetrievdict = {r      score_)]
       score_dictscore,, final_[(Document  List
          eturns:    Rog

    bug l   in deose:           verb   
     ối thiểuinal_score t    ngưỡng freshold:       th      
   docs trả về     số p_k:               toore)]
    etrieval_scDocument, r List[(ores:s_with_scdoc           
 ùngngười d hỏi câu             query:         s:
    Arg
      n.
eakdowe bror full scocs witherank d      R """
      ]:
   tr, float]]ict[st, Dent, floaple[Docum List[Tu,
    ) -> = Truebose: bool
        verESHOLD,RANK_THRoat = REld: fl   thresho_K,
     RERANK_TOPop_k: int = 
        t, float]],entumle[Doc[Tup: Listres_with_sco       docsstr,
  query: 