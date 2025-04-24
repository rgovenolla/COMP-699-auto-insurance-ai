from typing import Dict, List, Optional

class RiskAssessor:
    """Risk assessment system for auto insurance scenarios."""

    def __init__(self):
        # Risk factors and weights
        self.risk_factors = {
            "collision": {
                "at_fault": 0.8,
                "multiple_vehicles": 0.6,
                "injuries": 0.9,
                "weather_conditions": 0.5,
                "vehicle_speed": 0.7
            },
            "parking_damage": {
                "secured_location": 0.4,
                "extent_of_damage": 0.6,
                "frequency": 0.5
            },
            "weather_damage": {
                "severe_weather": 0.7,
                "extent_of_damage": 0.8,
                "vehicle_storage": 0.5
            },
            "theft": {
                "high_crime_area": 0.8,
                "vehicle_type": 0.7,
                "security_measures": 0.6
            },
            "vandalism": {
                "high_crime_area": 0.7,
                "extent_of_damage": 0.5,
                "secured_location": 0.5
            },
            "medical": {
                "severity_of_injury": 0.9,
                "number_of_injured": 0.7,
                "treatment_required": 0.8
            }
        }

        # Base risk scores for each category
        self.base_risk_scores = {
            "collision": 0.6,
            "parking_damage": 0.4,
            "weather_damage": 0.5,
            "theft": 0.7,
            "vandalism": 0.5,
            "medical": 0.8,
            "general_incident": 0.5
        }

    async def assess_risk(self, classification: Dict, scenario_text: str) -> Dict:
        """
        Assess risk level for a classified scenario.

        Args:
            classification: Dictionary with scenario classification
            scenario_text: Original scenario text

        Returns:
            Dict with risk assessment information
        """
        category = classification.get("category", "general_incident")

        # Extract risk factors from scenario text using simple rules
        risk_factors = self._extract_risk_factors(category, scenario_text)

        # Calculate base risk score
        base_risk_score = self._calculate_base_risk(category)

        # Apply risk factor modifiers
        modified_risk_score = self._apply_risk_modifiers(base_risk_score, category, risk_factors)

        # Determine risk level
        risk_level = self._determine_risk_level(modified_risk_score)

        # Identify primary concerns
        primary_concerns = self._identify_primary_concerns(category, risk_factors)

        # Calculate financial impact estimate
        financial_impact = self._estimate_financial_impact(category, modified_risk_score)

        return {
            "risk_score": round(modified_risk_score, 2),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "identified_factors": list(filter(lambda f: risk_factors.get(f, False), risk_factors.keys())),
            "confidence": classification.get("confidence", 0.5),
            "primary_concerns": primary_concerns,
            "financial_impact_estimate": financial_impact
        }

    def _extract_risk_factors(self, category: str, scenario_text: str) -> Dict:
        """Extract risk factors from scenario text using simple rules."""
        extracted_factors = {}
        text_lower = scenario_text.lower()

        # Common factors across categories
        if any(word in text_lower for word in ["fault", "responsible", "caused", "my fault"]):
            extracted_factors["at_fault"] = True

        if any(word in text_lower for word in ["multiple", "several", "many", "two", "three"]) and any(word in text_lower for word in ["vehicles", "cars", "trucks"]):
            extracted_factors["multiple_vehicles"] = True

        if any(word in text_lower for word in ["injury", "injuries", "hurt", "pain", "hospital"]):
            extracted_factors["injuries"] = True

        # Category-specific factors
        if category == "collision":
            if any(word in text_lower for word in ["fast", "speed", "speeding"]):
                extracted_factors["vehicle_speed"] = True

            if any(word in text_lower for word in ["rain", "snow", "ice", "wet"]):
                extracted_factors["weather_conditions"] = True

        elif category == "parking_damage":
            if any(word in text_lower for word in ["secure", "garage", "private"]):
                extracted_factors["secured_location"] = False  # Note the negation
            else:
                extracted_factors["secured_location"] = True

            if any(word in text_lower for word in ["significant", "extensive", "substantial"]):
                extracted_factors["extent_of_damage"] = True

        elif category == "weather_damage":
            if any(word in text_lower for word in ["severe", "major", "strong", "hurricane"]):
                extracted_factors["severe_weather"] = True

        elif category in ["theft", "vandalism"]:
            if any(word in text_lower for word in ["high crime", "dangerous", "unsafe"]):
                extracted_factors["high_crime_area"] = True

        return extracted_factors

    def _calculate_base_risk(self, category: str) -> float:
        """Calculate base risk score for category."""
        return self.base_risk_scores.get(category, 0.5)

    def _apply_risk_modifiers(self, base_score: float, category: str,
                             risk_factors: Dict) -> float:
        """Apply risk modifiers based on identified factors."""
        score = base_score
        category_weights = self.risk_factors.get(category, {})

        # Apply identified risk factors
        for factor, present in risk_factors.items():
            if present and factor in category_weights:
                score += category_weights[factor] * 0.1

        # Normalize to 0-1 range
        return min(max(score, 0.0), 1.0)

    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level based on score."""
        if risk_score < 0.3:
            return "low"
        elif risk_score < 0.6:
            return "moderate"
        elif risk_score < 0.8:
            return "high"
        else:
            return "very_high"

    def _identify_primary_concerns(self, category: str, risk_factors: Dict) -> List[str]:
        """Identify primary risk concerns."""
        concerns = []

        # Category-specific concerns
        if category == "collision":
            if risk_factors.get("at_fault", False):
                concerns.append("Potential liability for damages")
            if risk_factors.get("injuries", False):
                concerns.append("Potential medical claims")
            if risk_factors.get("multiple_vehicles", False):
                concerns.append("Multiple vehicle involvement increases complexity")

        elif category == "parking_damage":
            if risk_factors.get("secured_location", False):
                concerns.append("Unsecured location increases risk of recurrence")

        elif category == "weather_damage":
            if risk_factors.get("severe_weather", False):
                concerns.append("Severe weather caused extensive damage")

        elif category == "theft":
            if risk_factors.get("high_crime_area", False):
                concerns.append("High crime area increases risk of future theft")

        # If no specific concerns identified, add a general one
        if not concerns:
            concerns.append(f"Standard {category.replace('_', ' ')} risk assessment")

        return concerns

    def _estimate_financial_impact(self, category: str, risk_score: float) -> Dict:
        """Estimate financial impact of the incident."""
        # Base costs by category (in USD)
        base_costs = {
            "collision": 3500,
            "parking_damage": 1200,
            "weather_damage": 2800,
            "theft": 8000,
            "vandalism": 1800,
            "medical": 5000,
            "general_incident": 2500
        }

        # Get base cost for this category
        base_cost = base_costs.get(category, 2500)

        # Apply severity multiplier based on risk score
        severity_multiplier = 0.5 + (risk_score * 2.5)

        # Calculate range values
        median_estimate = base_cost * severity_multiplier
        low_estimate = median_estimate * 0.7
        high_estimate = median_estimate * 1.3

        return {
            "low_estimate": round(low_estimate, 2),
            "median_estimate": round(median_estimate, 2),
            "high_estimate": round(high_estimate, 2),
            "currency": "USD"
        }
