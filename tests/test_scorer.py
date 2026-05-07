from unmet_demand.score.scorer import score_opportunity


def test_score_opportunity_weighting():
    score = score_opportunity(
        frequency_score=5,
        pain_score=4,
        urgency_score=3,
        monetization_score=5,
        feasibility_score=4,
        novelty_score=3,
    )

    assert score == 4.2


def test_frequency_moves_score_up():
    low = score_opportunity(1, 3, 3, 3, 3, 3)
    high = score_opportunity(5, 3, 3, 3, 3, 3)

    assert high > low
