from typing import Dict, List, Optional

class PolicyAnalyzer:
    """Analyzes insurance policies relevant to classified scenarios."""

    def __init__(self):
        # Load policy definitions
        self.policies = {
            "liability": {
                "description": "Covers damage you cause to others",
                "subtypes": ["bodily_injury", "property_damage"],
                "typical_limits": ["$25,000/$50,000/$25,000", "$50,000/$100,000/$50,000"],
                "required": True,
                "coverage_details": "Liability coverage helps pay for the costs of the other driver's property and bodily injuries if you're found at fault in an accident."
            },
            "collision": {
                "description": "Covers damage to your vehicle from a collision",
                "subtypes": ["standard", "broad_form"],
                "typical_deductibles": ["$250", "$500", "$1000"],
                "required": False,
                "coverage_details": "Collision coverage helps pay for damage to your vehicle after an accident, regardless of who is at fault."
            },
            "comprehensive": {
                "description": "Covers non-collision damage to your vehicle",
                "subtypes": ["standard", "named_perils"],
                "typical_deductibles": ["$0", "$250", "$500", "$1000"],
                "required": False,
                "coverage_details": "Comprehensive coverage helps pay for damage to your car caused by events other than collision, such as theft, vandalism, or natural disasters."
            },
            "medical_payments": {
                "description": "Covers medical expenses regardless of fault",
                "typical_limits": ["$1,000", "$5,000", "$10,000"],
                "required": False,
                "coverage_details": "Medical payments coverage helps pay for medical expenses for you and your passengers after an accident, regardless of who is at fault."
            },
            "personal_injury_protection": {
                "description": "Covers medical expenses, lost wages, and other costs",
                "typical_limits": ["$10,000", "$25,000", "$50,000"],
                "required": False,
                "coverage_details": "Personal injury protection (PIP) helps cover medical expenses, lost wages, and other costs associated with injuries sustained in an accident, regardless of fault."
            }
        }

        # Load scenario-policy mappings
        self.scenario_policies = {
            "collision": ["liability", "collision", "medical_payments"],
            "parking_damage": ["comprehensive", "collision"],
            "weather_damage": ["comprehensive"],
            "theft": ["comprehensive"],
            "vandalism": ["comprehensive"],
            "medical": ["medical_payments", "personal_injury_protection"]
        }

    def analyze_policies(self, classification: Dict, user_policy: Dict = None) -> Dict:
        """
        Analyze policies based on scenario classification.

        Args:
            classification: Dictionary containing scenario classification
            user_policy: Optional dictionary with user's current policy details

        Returns:
            Dict with policy analysis information
        """
        relevant_policies = classification.get("relevant_policies", [])
        category = classification.get("category", "")

        # If category exists in our mappings but relevant_policies is empty,
        # use our predefined mappings
        if category in self.scenario_policies and not relevant_policies:
            relevant_policies = self.scenario_policies[category]

        policy_analysis = {
            "primary_coverage": None,
            "secondary_coverage": [],
            "policy_details": {},
            "coverage_gaps": [],
            "recommendations": []
        }

        # Determine primary coverage
        if relevant_policies:
            policy_analysis["primary_coverage"] = relevant_policies[0]
            policy_analysis["secondary_coverage"] = relevant_policies[1:] if len(relevant_policies) > 1 else []

        # Add policy details
        for policy in relevant_policies:
            if policy in self.policies:
                policy_analysis["policy_details"][policy] = self.policies[policy]

        # Identify potential coverage gaps
        self._identify_coverage_gaps(policy_analysis, category, user_policy)

        # Generate recommendations
        self._generate_recommendations(policy_analysis, category, classification.get("confidence", 0.5))

        return policy_analysis

    def _identify_coverage_gaps(self, policy_analysis: Dict, category: str, user_policy: Dict = None) -> None:
        """Identify potential coverage gaps based on scenario category."""
        # Without user policy, identify standard gaps based on category
        if category == "collision":
            if "collision" not in policy_analysis["policy_details"]:
                policy_analysis["coverage_gaps"].append({
                    "type": "missing_coverage",
                    "policy": "collision",
                    "description": "Collision coverage not present but recommended for collision scenarios",
                    "severity": "high"
                })
        elif category in ["weather_damage", "theft", "vandalism"]:
            if "comprehensive" not in policy_analysis["policy_details"]:
                policy_analysis["coverage_gaps"].append({
                    "type": "missing_coverage",
                    "policy": "comprehensive",
                    "description": f"Comprehensive coverage not present but recommended for {category.replace('_', ' ')}",
                    "severity": "high"
                })
        elif category == "medical":
            if "medical_payments" not in policy_analysis["policy_details"] and "personal_injury_protection" not in policy_analysis["policy_details"]:
                policy_analysis["coverage_gaps"].append({
                    "type": "missing_coverage",
                    "policy": "medical_payments",
                    "description": "Medical payments or personal injury protection coverage not present but recommended for medical expenses",
                    "severity": "high"
                })

    def _generate_recommendations(self, policy_analysis: Dict, category: str, confidence: float) -> None:
        """Generate policy recommendations based on analysis."""
        # Process coverage gaps first
        for gap in policy_analysis["coverage_gaps"]:
            if gap["type"] == "missing_coverage":
                policy_analysis["recommendations"].append({
                    "action": "add_coverage",
                    "coverage": gap["policy"],
                    "description": gap["description"],
                    "priority": gap["severity"],
                    "confidence": confidence
                })
