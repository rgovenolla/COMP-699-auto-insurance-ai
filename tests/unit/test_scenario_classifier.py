import pytest
from src.classifiers.scenario_classifier import ScenarioClassifier, ClassificationError

@pytest.fixture
def classifier():
    return ScenarioClassifier()

@pytest.mark.asyncio
async def test_basic_classification(classifier):
    scenario = """
    A driver rear-ended my car at a stop light. There was visible damage 
    to my rear bumper. The incident occurred on a clear day with good visibility.
    """
    
    result = await classifier.classify_scenario(scenario)
    
    assert isinstance(result, dict)
    assert "category" in result
    assert "confidence" in result
    assert "relevant_policies" in result
    assert isinstance(result["confidence"], float)
    assert 0 <= result["confidence"] <= 1
    assert isinstance(result["relevant_policies"], list)

@pytest.mark.asyncio
async def test_empty_scenario(classifier):
    with pytest.raises(ValueError):
        await classifier.classify_scenario("")

@pytest.mark.asyncio
async def test_parking_scenario(classifier):
    scenario = """
    While parked at the mall, someone scratched my car's paint.
    """
    result = await classifier.classify_scenario(scenario)
    assert "parking_damage" in result["category"].lower()
    assert "comprehensive" in result["relevant_policies"]

@pytest.mark.asyncio
async def test_weather_scenario(classifier):
    scenario = """
    My car was damaged in a hail storm.
    """
    result = await classifier.classify_scenario(scenario)
    assert "weather" in result["category"].lower()
    assert "comprehensive" in result["relevant_policies"]