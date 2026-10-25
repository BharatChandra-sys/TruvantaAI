"""Key-term queries and relevance scoring used by evidence search (no network)."""
from app.analysis.search import Relevance, key_terms, keyword_query, verdict_without_model

AWACS = ('Yes, India moved forward with acquiring the R-37M (RVV-BD) very-long-range '
         'air-to-air missile from Russia, widely known as the "AWACS killer".')


def test_query_keeps_codes_names_and_quoted_phrases_and_drops_filler():
    q = keyword_query(AWACS)
    for term in ("R-37M", "RVV-BD", "India", "Russia", '"AWACS killer"'):
        assert term in q
    for filler in ("Yes", "moved", "forward", "widely"):
        assert filler not in q.split()


def test_weights():
    weights = {t: w for t, w, _ in key_terms(AWACS)}
    assert weights["R-37M"] == 3 and weights["AWACS killer"] == 3
    assert weights["India"] == 2 and weights["Russia"] == 2


def test_relevant_headline_scores_high_and_unrelated_low():
    rel = Relevance(AWACS)
    assert rel("India Buys the AWACS Killer: 300 Russian Super-Missiles") >= 0.4
    assert rel("India beat Australia in the second Test at Chennai") < 0.3


def test_word_forms_match():
    rel = Relevance("Russia sells missiles to India")
    assert rel("Russian missile export to India approved") > 0.6


def test_no_sources_never_guesses():
    verdict, conf, why = verdict_without_model([], [])
    assert verdict == "uncertain" and conf == 0.5 and "couldn't find" in why


def test_fact_check_can_decide_without_a_model():
    articles = [{"kind": "fact_check", "stance": "contradict", "source": "Snopes", "rating": "False"}]
    verdict, conf, why = verdict_without_model([{}], articles)
    assert verdict == "fake" and "Snopes" in why


def test_low_trust_results_need_more_relevance():
    from app.analysis.search import _keep
    rel = Relevance("The Great Wall of China is visible from the Moon")
    item = {"kind": "web", "title": "Great Wall of China facts", "text": "", "low_trust": True}
    assert not _keep(rel, item)                       # 'Great Wall China' alone isn't enough when low trust
    assert _keep(rel, dict(item, low_trust=False))    # the same text passes from a normal source


def test_low_trust_sources_cannot_settle_a_verdict_alone():
    from app.analysis.search import reconcile
    weak = [{"model_stance": "contradict", "low_trust": True}] * 3
    assert reconcile("uncertain", 0.5, weak) == ("uncertain", 0.5)
    strong = [{"model_stance": "contradict"}] * 2
    assert reconcile("uncertain", 0.5, strong)[0] == "fake"


def test_firm_verdict_that_its_own_sources_refute_is_flipped():
    # Seen in the evaluation: every source judged "contradict", verdict "real".
    from app.analysis.search import reconcile
    refuting = [{"kind": "fact_check", "stance": "contradict", "model_stance": "contradict"}] * 4
    refuting += [{"kind": "news", "stance": "neutral", "model_stance": "neutral"}]
    assert reconcile("real", 0.97, refuting) == ("fake", 0.8)


def test_relevant_fact_check_rated_against_the_verdict_makes_it_uncertain():
    # Seen in the evaluation: Snopes rated the claim False, the model answered "real".
    from app.analysis.search import reconcile
    arts = [{"kind": "fact_check", "stance": "contradict", "model_stance": "support"},
            {"kind": "news", "stance": "support", "model_stance": "support"},
            {"kind": "reference", "stance": "support", "model_stance": "support"}]
    assert reconcile("real", 0.8, arts) == ("uncertain", 0.5)
    # A fact-check the model judged unrelated doesn't count.
    unrelated = [dict(arts[0], model_stance="neutral")] + arts[1:]
    assert reconcile("real", 0.8, unrelated) == ("real", 0.8)


def test_firm_verdict_backed_by_its_sources_is_kept():
    from app.analysis.search import reconcile
    arts = [{"kind": "fact_check", "stance": "contradict", "model_stance": "contradict"},
            {"kind": "news", "stance": "contradict", "model_stance": "contradict"}]
    assert reconcile("fake", 0.93, arts) == ("fake", 0.93)
