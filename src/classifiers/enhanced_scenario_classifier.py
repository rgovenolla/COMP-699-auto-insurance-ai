import os
from typing import Dict, List, Optional
from openai import OpenAI
import json
import time
from src.utils.cache import TokenCache
from src.utils.validators import DataValidator
from src.config.settings import settings

class ClassificationError(Exception):
    """Custom exception for classification errors."""
    pass

class EnhancedScenarioClassifier:
    """Enhanced auto insurance scenario classifier with ML integration."""

    def __init__(self, use_cache=True):
        # Initialize OpenAI client
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise EnvironmentError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=self.api_key)

        # Initialize cache
        self.use_cache = use_cache
        if use_cache:
            self.cache = TokenCache()

        # Load scenario categories and rules
        self._load_classification_rules()

    def _load_classification_rules(self):
        """Load scenario classification rules."""
        self.categories = {
            "collision": {
                "keywords": ["rear-ended", "hit", "crash", "collision", "accident"],
                "policies": ["liability", "collision"]
            },
            "parking_damage": {
                "keywords": ["parked", "parking", "dent", "scratch"],
                "policies": ["comprehensive", "collision"]
            },
            "weather_damage": {
                "keywords": ["storm", "hail", "flood", "weather"],
                "policies": ["comprehensive"]
            },
            "theft": {
                "keywords": ["stolen", "theft", "break-in", "stole"],
                "policies": ["comprehensive"]
            },
            "vandalism": {
                "keywords": ["vandalized", "keyed", "graffiti", "damaged"],
                "policies": ["comprehensive"]
            },
            "medical": {
                "keywords": ["injury", "hurt", "hospital", "pain", "medical"],
                "policies": ["medical_payments", "personal_injury_protection"]
            }
        }

    async def classify_scenario(self, scenario_text: str) -> Dict:
        """
        Classify an auto insurance scenario using hybrid approach.

        Args:
            scenario_text: Text description of the insurance scenario

        Returns:
            Dict with classification results
        """
        # Start performance timing
        start_time = time.time()

        # Validate input
        validator = DataValidator()
        scenario_text = validator.validate(scenario_text)

        # Check cache
        if self.use_cache:
            cached_result = self.cache.get(scenario_text)
            if cached_result:
                return cached_result

        # Track whether we used rule-based fallback
        used_rule_based_fallback = False

        # Classification pipeline:
        # 1. Try ML classification first (OpenAI)
        # 2. Use rule-based as fallback
        try:
            ml_result = await self._ml_classification(scenario_text)
            confidence = ml_result.get("confidence", 0)

            # If ML confidence is high, use ML result
            if confidence > 0.7:
                result = ml_result
            else:
                # Get rule-based classification
                rule_result = self._rule_based_classification(scenario_text)

                # Choose higher confidence result
                if rule_result.get("confidence", 0) > confidence:
                    result = rule_result
                    used_rule_based_fallback = True
                else:
                    result = ml_result
        except Exception as e:
            # Fallback to rule-based
            result = self._rule_based_classification(scenario_text)
            used_rule_based_fallback = True

        # Validate and enhance result
        result = self._validate_classification(result)

        # Add metadata
        result["processing_time"] = time.time() - start_time
        result["rule_based_fallback"] = used_rule_based_fallback

        # Cache result
        if self.use_cache:
            self.cache.store(scenario_text, result)

        return result

    async def _ml_classification(self, scenario_text: str) -> Dict:
        """Classify scenario using ML approach with OpenAI."""
        try:
            completion = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """You are an auto insurance claims classifier.
                     Analyze the scenario and provide a JSON response with the following structure:
                     {"category": "collision|parking_damage|weather_damage|theft|vandalism|medical",
                      "confidence": 0.0-1.0,
                      "relevant_policies": ["policy_type1", "policy_type2"],
                      "reasoning": "Brief explanation of classification reasoning"}"""},
                    {"role": "user", "content": scenario_text}
                ],
                temperature=0.3,
                max_tokens=150
            )

            # Parse the response as JSON
            result = json.loads(completion.choices[0].message.content)
            return result
        except (json.JSONDecodeError, AttributeError) as e:
            raise ClassificationError(f"Failed to parse ML classification result: {str(e)}")

    def _rule_based_classification(self, scenario_text: str) -> Dict:
        """Rule-based classification system."""
        scenario_lower = scenario_text.lower()

        # Find matching category based on keywords
        max_matches = 0
        best_category = "general_incident"
        relevant_policies = ["liability"]

        for category, rules in self.categories.items():
            matches = sum(1 for keyword in rules["keywords"]
                         if keyword in scenario_lower)
            if matches > max_matches:
                max_matches = matches
                best_category = category
                relevant_policies = rules["policies"]

        # Calculate confidence based on number of matches
        match_confidence = min(0.9, 0.5 + (0.1 * max_matches))

        return {
            "category": best_category,
            "confidence": match_confidence if max_matches > 0 else 0.5,
            "relevant_policies": relevant_policies,
            "reasoning": f"Rule-based classification identified {max_matches} keyword matches for category '{best_category}'"
        }

    def _validate_classification(self, result: Dict) -> Dict:
        """Validate and normalize classification results."""
        required_keys = ["category", "confidence", "relevant_policies"]

        if not all(key in result for key in required_keys):
            raise ValueError("Invalid classification result structure")

        # Normalize confidence to 0-1 range
        result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))

        # Ensure relevant_policies is a list
        if isinstance(result["relevant_policies"], str):
            result["relevant_policies"] = [result["relevant_policies"]]

        # Ensure reasoning exists
        if "reasoning" not in result:
            result["reasoning"] = f"Classification based on scenario characteristics"

        return result
