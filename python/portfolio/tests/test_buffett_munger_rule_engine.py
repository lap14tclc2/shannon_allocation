import pytest
from portfolio.value_engine.archetypes import ArchetypeClassifier, EconomicArchetype
from portfolio.value_engine.quality_scorer import QualityScorer, QualityTier
from portfolio.value_engine.margin_of_safety import MarginOfSafetyEngine

def test_archetype_classification():
    # MBB -> COMMERCIAL_BANK
    mbb_prof = ArchetypeClassifier.classify("MBB")
    assert mbb_prof.archetype == EconomicArchetype.COMMERCIAL_BANK
    assert mbb_prof.recommended_model == "RESIDUAL_INCOME_MODEL"
    assert mbb_prof.base_required_mos == 0.25

    # FPT -> TECHNOLOGY_SERVICES
    fpt_prof = ArchetypeClassifier.classify("FPT")
    assert mbb_prof.archetype != fpt_prof.archetype
    assert fpt_prof.archetype == EconomicArchetype.TECHNOLOGY_SERVICES

    # HPG -> BASIC_MATERIALS_METALS
    hpg_prof = ArchetypeClassifier.classify("HPG")
    assert hpg_prof.archetype == EconomicArchetype.BASIC_MATERIALS_METALS
    assert hpg_prof.base_required_mos >= 0.40

def test_quality_scorer_and_dynamic_mos():
    fpt_prof = ArchetypeClassifier.classify("FPT")
    scorecard = QualityScorer.evaluate(
        archetype_prof=fpt_prof,
        financial_history_10y=[{"net_profit": 1}, {"net_profit": 2}, {"net_profit": 3}, {"net_profit": 4}, {"net_profit": 5}],
        five_year_avg_roe=24.0,
        five_year_avg_cash_conversion=92.0,
        net_debt_vnd=0.0,
        latest_cfo=10e12,
        true_dilution_5y_pct=0.0,
    )
    
    assert scorecard.total_score >= 80
    assert scorecard.tier in (QualityTier.EXCEPTIONAL, QualityTier.HIGH_QUALITY)
    
    # Calculate MOS with 30% actual MOS
    mos_res = MarginOfSafetyEngine.calculate(
        archetype_prof=fpt_prof,
        quality_tier=scorecard.tier,
        actual_base_mos=30.0,
    )
    
    assert mos_res.required_mos_pct <= 25.0
    assert mos_res.mos_satisfied is True
    assert mos_res.verdict_status == "HIGH_CONVICTION_VALUE"
