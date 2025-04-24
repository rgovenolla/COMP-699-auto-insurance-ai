import os
from typing import Dict, List, Optional, Tuple
import json
import asyncio
from src.utils.cache import TokenCache

class RecommendationEngine:
    """Advanced recommendation engine for insurance scenarios."""

    def __init__(self, db_connector=None):
        # Connect to database for historical data if provided
        self.db_connector = db_connector

        # Load recommendation rules
        self._load_recommendation_rules()

        # Initialize cache
        self.cache = TokenCache()

    def _load_recommendation_rules(self):
        """Load rule-based recommendation logic."""
        self.rules = {
            "collision": {
                "high_risk": [
                    {"action": "increase_coverage", "policy": "liability", "min_amount": "$100,000/$300,000",
                     "reason": "Higher liability limits provide better protection in serious collision scenarios"},
                    {"action": "add_coverage", "policy": "uninsured_motorist", "condition": "not_present",
                     "reason": "Uninsured motorist coverage protects you when the at-fault driver has no insurance"}
                ],
                "moderate_risk": [
                    {"action": "review_deductible", "policy": "collision", "suggestion": "evaluate_optimal",
                     "reason": "Optimizing your deductible can balance premium costs with out-of-pocket expenses"},
                    {"action": "consider_coverage", "policy": "medical_payments", "condition": "not_present",
                     "reason": "Medical payments coverage provides additional protection for injury expenses"}
                ],
                "low_risk": [
                    {"action": "maintain_coverage", "policy": "liability",
                     "reason": "Your current liability coverage appears appropriate for this risk level"}
                ]
            },
            "parking_damage": {
                "high_risk": [
                    {"action": "add_coverage", "policy": "comprehensive", "condition": "not_present",
                     "reason": "Comprehensive coverage would protect against future parking damage incidents"},
                    {"action": "decrease_deductible", "policy": "comprehensive", "max_amount": "$250",
                     "reason": "A lower deductible reduces out-of-pocket expenses for frequent claims"}
                ],
                "moderate_risk": [
                    {"action": "add_coverage", "policy": "comprehensive", "condition": "not_present",
                     "reason": "Comprehensive coverage protects against damage while parked"},
                    {"action": "review_deductible", "policy": "comprehensive", "suggestion": "evaluate_optimal",
                     "reason": "Consider your deductible based on the frequency of claims and premium costs"}
                ]
            },
            "weather_damage": {
                "high_risk": [
                    {"action": "add_coverage", "policy": "comprehensive", "condition": "not_present",
                     "reason": "Comprehensive coverage is essential for weather-related damage protection"},
                    {"action": "review_coverage_limits", "policy": "comprehensive", "suggestion": "increase",
                     "reason": "Higher coverage limits provide better protection against severe weather damage"}
                ],
                "moderate_risk": [
                    {"action": "add_coverage", "policy": "comprehensive", "condition": "not_present",
                     "reason": "Comprehensive coverage protects against weather damage to your vehicle"},
                    {"action": "consider_coverage", "policy": "roadside_assistance", "condition": "not_present",
                     "reason": "Roadside assistance can help in weather-related breakdown situations"}
                ]
            },
            "theft": {
                "high_risk": [
                    {"action": "add_coverage", "policy": "comprehensive", "condition": "not_present",
                     "reason": "Comprehensive coverage is essential for theft protection"},
                    {"action": "consider_coverage", "policy": "rental_reimbursement", "condition": "not_present",
                     "reason": "Rental reimbursement provides transportation while your vehicle is being replaced"}
                ],
                "moderate_risk": [
                    {"action": "add_coverage", "policy": "comprehensive", "condition": "not_present",
                     "reason": "Comprehensive coverage includes theft protection"}
                ]
            },
            "vandalism": {
                "high_risk": [
                    {"action": "add_coverage", "policy": "comprehensive", "condition": "not_present",
                     "reason": "Comprehensive coverage protects against vandalism damage"},
                    {"action": "decrease_deductible", "policy": "comprehensive", "max_amount": "$500",
                     "reason": "A lower deductible reduces out-of-pocket expenses for vandalism claims"}
                ],
                "moderate_risk": [
                    {"action": "add_coverage", "policy": "comprehensive", "condition": "not_present",
                     "reason": "Comprehensive coverage includes protection against vandalism"}
                ]
            },
            "medical": {
                "high_risk": [
                    {"action": "increase_coverage", "policy": "medical_payments", "min_amount": "$10,000",
                     "reason": "Higher medical payments limits provide better protection for serious injuries"},
                    {"action": "add_coverage", "policy": "personal_injury_protection", "condition": "not_present",
                     "reason": "Personal injury protection provides broader medical coverage and lost wages"}
                ],
                "moderate_risk": [
                    {"action": "review_coverage_limits", "policy": "medical_payments", "suggestion": "evaluate",
                     "reason": "Ensure your medical coverage limits match potential medical expenses"}
                ]
            }
        }

        # Global rules that apply across categories
        self.global_rules = [
            {"condition": "high_value_vehicle",
             "action": "consider_coverage",
             "policy": "gap_insurance",
             "reason": "Gap insurance covers the difference between your car's value and what you owe if it's totaled"},
            {"condition": "multiple_claims",
             "action": "review_deductible",
             "policy": "all",
             "reason": "With multiple claims, optimizing your deductible can reduce overall costs"}
        ]

    async def generate_recommendations(self, classification: Dict,
                                 policy_analysis: Dict,
                                 risk_assessment: Dict,
                                 user_profile: Dict = None) -> List[Dict]:
        """
        Generate tailored recommendations based on scenario analysis.

        Args:
            classification: Scenario classification
            policy_analysis: Policy analysis results
            risk_assessment: Risk assessment results
            user_profile: Optional user profile with policy history

        Returns:
            List of recommendation objects
        """
        # Create cache key
        cache_key = f"recommendation_{classification.get('category')}_{risk_assessment.get('risk_level')}"
        if user_profile:
            cache_key += f"_{user_profile.get('id', 'no_id')}"

        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        recommendations = []

        # Get basic rule-based recommendations
        rule_recommendations = self._get_rule_based_recommendations(
            classification, policy_analysis, risk_assessment)
        recommendations.extend(rule_recommendations)

        # If historical data is available, enhance with data-driven recommendations
        if self.db_connector:
            data_recommendations = await self._get_data_driven_recommendations(
                classification, risk_assessment)
            recommendations.extend(data_recommendations)

        # Add personalized recommendations if user profile is available
        if user_profile:
            personalized_recommendations = self._get_personalized_recommendations(
                classification, risk_assessment, user_profile)
            recommendations.extend(personalized_recommendations)

        # Remove duplicates and prioritize
        unique_recommendations = self._deduplicate_recommendations(recommendations)
        prioritized_recommendations = self._prioritize_recommendations(unique_recommendations)

        # Add tracking IDs to recommendations
        for i, rec in enumerate(prioritized_recommendations):
            rec["id"] = f"REC-{classification.get('category', 'general')}-{i+1}"

        # Store in cache
        self.cache.store(cache_key, prioritized_recommendations)

        return prioritized_recommendations

    def _get_rule_based_recommendations(self, classification: Dict,
                                       policy_analysis: Dict,
                                       risk_assessment: Dict) -> List[Dict]:
        """
        Get recommendations based on predefined rules.

        Args:
            classification: Scenario classification
            policy_analysis: Policy analysis results
            risk_assessment: Risk assessment results

        Returns:
            List of rule-based recommendations
        """
        category = classification.get("category", "general_incident")
        risk_level = risk_assessment.get("risk_level", "moderate")

        # Get applicable rules
        category_rules = self.rules.get(category, {})
        applicable_rules = category_rules.get(risk_level, [])

        recommendations = []
        for rule in applicable_rules:
            # Check if rule conditions are met
            if self._check_rule_conditions(rule, policy_analysis):
                recommendations.append({
                    "type": "rule_based",
                    "action": rule.get("action"),
                    "policy": rule.get("policy"),
                    "reason": rule.get("reason", "Based on standard industry recommendations"),
                    "details": {k: v for k, v in rule.items()
                              if k not in ["action", "policy", "condition", "reason"]},
                    "priority": self._get_rule_priority(rule, risk_level),
                    "confidence": 0.85
                })

        # Add applicable global rules
        for rule in self.global_rules:
            if self._check_global_rule_condition(rule, classification, risk_assessment):
                recommendations.append({
                    "type": "global_rule",
                    "action": rule.get("action"),
                    "policy": rule.get("policy"),
                    "reason": rule.get("reason", "Based on your overall risk profile"),
                    "details": {k: v for k, v in rule.items()
                              if k not in ["action", "policy", "condition", "reason"]},
                    "priority": "medium",
                    "confidence": 0.75
                })

        return recommendations

    async def _get_data_driven_recommendations(self, classification: Dict,
                                        risk_assessment: Dict) -> List[Dict]:
        """
        Get recommendations based on historical data analysis.

        Args:
            classification: Scenario classification
            risk_assessment: Risk assessment results

        Returns:
            List of data-driven recommendations
        """
        # This would connect to a database or analytics service in production
        # Simplified implementation for demonstration purposes
        category = classification.get("category", "general_incident")
        risk_level = risk_assessment.get("risk_level", "moderate")

        # Simulate data-driven recommendations
        recommendations = []

        if category == "collision" and risk_level in ["high", "very_high"]:
            recommendations.append({
                "type": "data_driven",
                "action": "consider_umbrella_policy",
                "policy": "umbrella",
                "reason": "70% of similar high-risk collision claims exceeded standard liability limits",
                "details": {
                    "supporting_data": "Analysis of 2,500 similar claims",
                    "suggested_coverage": "$1,000,000"
                },
                "priority": "medium",
                "confidence": 0.82
            })

        if category == "theft" and "high_crime_area" in risk_assessment.get("identified_factors", []):
            recommendations.append({
                "type": "data_driven",
                "action": "consider_security_system",
                "policy": "security_discount",
                "reason": "Vehicles with security systems in high-crime areas show 60% lower theft rates",
                "details": {
                    "supporting_data": "Analysis of theft claims in similar areas",
                    "potential_discount": "10-15% on comprehensive premium"
                },
                "priority": "high",
                "confidence": 0.88
            })

        return recommendations

    def _get_personalized_recommendations(self, classification: Dict,
                                        risk_assessment: Dict,
                                        user_profile: Dict) -> List[Dict]:
        """
        Generate personalized recommendations based on user profile.

        Args:
            classification: Scenario classification
            risk_assessment: Risk assessment results
            user_profile: User profile data

        Returns:
            List of personalized recommendations
        """
        recommendations = []

        # Check for bundling opportunities
        if "home_insurance" not in user_profile.get("other_policies", []):
            recommendations.append({
                "type": "personalized",
                "action": "consider_bundling",
                "policy": "home_and_auto",
                "reason": "Bundling home and auto insurance typically saves 10-15% on premiums",
                "details": {
                    "estimated_savings": "10-15%",
                    "additional_benefits": "Simplified claims process, single deductible options"
                },
                "priority": "medium",
                "confidence": 0.75
            })

        # Check for loyalty benefits
        if user_profile.get("years_as_customer", 0) >= 3:
            recommendations.append({
                "type": "personalized",
                "action": "review_loyalty_benefits",
                "policy": "all",
                "reason": f"As a {user_profile.get('years_as_customer', 0)}-year customer, you may qualify for additional loyalty discounts",
                "details": {
                    "estimated_savings": "5-10%",
                    "qualification": "Based on customer tenure"
                },
                "priority": "low",
                "confidence": 0.9
            })

        # Safe driver recommendations
        if user_profile.get("driving_record", {}).get("accidents", 0) == 0 and \
           user_profile.get("driving_record", {}).get("violations", 0) == 0:
            recommendations.append({
                "type": "personalized",
                "action": "consider_program",
                "policy": "safe_driver_discount",
                "reason": "Your clean driving record qualifies you for safe driver discounts",
                "details": {
                    "estimated_savings": "Up to 20%",
                    "qualification": "Based on driving history"
                },
                "priority": "medium",
                "confidence": 0.85
            })

        return recommendations

    def _check_rule_conditions(self, rule: Dict, policy_analysis: Dict) -> bool:
        """
        Check if conditions for a recommendation rule are met.

        Args:
            rule: Recommendation rule
            policy_analysis: Policy analysis results

        Returns:
            True if conditions are met, False otherwise
        """
        condition = rule.get("condition")
        policy = rule.get("policy")

        if condition == "not_present":
            current_policies = [p for p in policy_analysis.get("policy_details", {})]
            return policy not in current_policies

        # Default to True if no conditions or unknown condition
        return True

    def _check_global_rule_condition(self, rule: Dict, classification: Dict,
                                   risk_assessment: Dict) -> bool:
        """
        Check if conditions for a global rule are met.

        Args:
            rule: Global recommendation rule
            classification: Scenario classification
            risk_assessment: Risk assessment results

        Returns:
            True if conditions are met, False otherwise
        """
        condition = rule.get("condition")

        if condition == "high_value_vehicle":
            return "vehicle_value" in risk_assessment.get("identified_factors", [])

        if condition == "multiple_claims":
            return "frequency" in risk_assessment.get("identified_factors", [])

        # Default to False for global rules with unknown conditions
        return False

    def _get_rule_priority(self, rule: Dict, risk_level: str) -> str:
        """
        Determine priority of a recommendation based on rule and risk.

        Args:
            rule: Recommendation rule
            risk_level: Assessed risk level

        Returns:
            Priority level (high, medium, low)
        """
        action = rule.get("action", "")

        if risk_level in ["high", "very_high"]:
            if action in ["add_coverage", "increase_coverage"]:
                return "high"
            return "medium"

        if risk_level == "moderate":
            if action in ["add_coverage"]:
                return "medium"
            return "low"

        return "low"

    def _deduplicate_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
        """
        Remove duplicate recommendations.

        Args:
            recommendations: List of recommendations

        Returns:
            List with duplicates removed
        """
        unique_recs = {}
        for rec in recommendations:
            key = f"{rec.get('action')}-{rec.get('policy')}"
            # Keep higher priority recommendation if duplicate
            if key not in unique_recs or self._priority_value(rec.get('priority')) > self._priority_value(unique_recs[key].get('priority')):
                unique_recs[key] = rec

        return list(unique_recs.values())

    def _prioritize_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
        """
        Sort recommendations by priority.

        Args:
            recommendations: List of recommendations

        Returns:
            Sorted list of recommendations
        """
        # Sort first by priority, then by confidence
        return sorted(recommendations,
                     key=lambda x: (self._priority_value(x.get('priority', 'low')),
                                   x.get('confidence', 0)),
                     reverse=True)

    def _priority_value(self, priority: str) -> int:
        """
        Convert priority string to numeric value for sorting.

        Args:
            priority: Priority string

        Returns:
            Numeric priority value
        """
        values = {"high": 3, "medium": 2, "low": 1}
        return values.get(priority, 0)

    async def get_effectiveness_metrics(self) -> Dict:
        """
        Get effectiveness metrics for recommendations.

        Returns:
            Dict with effectiveness metrics
        """
        # In production, this would query a database for actual metrics
        # Returning mock data for demonstration
        return {
            "implemented_rate": 0.65,
            "by_category": {
                "add_coverage": 0.72,
                "increase_coverage": 0.58,
                "review_deductible": 0.45,
                "consider_coverage": 0.38
            },
            "by_priority": {
                "high": 0.78,
                "medium": 0.62,
                "low": 0.35
            },
            "customer_satisfaction": 4.2,  # Out of 5
            "cost_savings": {
                "average": 12.5,  # Percentage
                "total": 850000   # Dollar amount
            }
        }
