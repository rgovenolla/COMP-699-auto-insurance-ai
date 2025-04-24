from typing import Any, Dict, Optional
from pydantic import BaseModel, validator

class ScenarioInput(BaseModel):
    """Validation model for scenario input data."""
    scenario_text: str

    @validator('scenario_text')
    def validate_scenario_text(cls, v):
        if not v.strip():
            raise ValueError("Scenario text cannot be empty")
        if len(v) < 10:
            raise ValueError("Scenario text too short")
        if len(v) > 5000:
            raise ValueError("Scenario text too long")
        return v

class DataValidator:
    """Handles validation of input data for the classification system."""

    def validate(self, scenario_text: str) -> str:
        """
        Validates scenario text input.

        Args:
            scenario_text (str): Raw scenario text

        Returns:
            str: Validated and cleaned scenario text
        """
        # Validate using pydantic model
        validated = ScenarioInput(scenario_text=scenario_text)

        # Clean and normalize text
        cleaned_text = self._clean_text(validated.scenario_text)

        return cleaned_text

    def _clean_text(self, text: str) -> str:
        """Clean and normalize input text."""
        # Remove extra whitespace
        text = " ".join(text.split())
        # Additional cleaning logic will go here
        return text
