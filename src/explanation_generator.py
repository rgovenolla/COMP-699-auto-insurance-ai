import os
from typing import Dict, List, Optional
from openai import OpenAI
import json
from src.utils.cache import TokenCache

class ExplanationGenerator:
    """Generates natural language explanations for classification results."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise EnvironmentError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=self.api_key)

        # Templates for different explanation types
        self.templates = {
            "classification": "The incident has been classified as a {category} scenario with {confidence:.0%} confidence. This classification is based on {reasoning}.",
            "policy": "Based on this classification, the primary applicable policy is {primary_policy}, which {policy_description}. {gap_explanation}",
            "risk": "The risk level for this scenario is assessed as {risk_level} with a score of {risk_score:.2f}. {risk_explanation}",
            "financial": "The estimated financial impact ranges from ${low_estimate:,.2f} to ${high_estimate:,.2f}, with a median estimate of ${median_estimate:,.2f}."
        }

        # Load cache
        self.cache = TokenCache()

    async def generate_explanation(self, classification: Dict,
                              policy_analysis: Dict,
                              risk_assessment: Dict) -> Dict:
        """
        Generate a natural language explanation for results.

        Args:
            classification: Scenario classification results
            policy_analysis: Policy analysis results
            risk_assessment: Risk assessment results

        Returns:
            Dict with various explanation components
        """
        # Create cache key
        cache_key = json.dumps({
            "classification": classification.get("category"),
            "policy": policy_analysis.get("primary_coverage"),
            "risk": risk_assessment.get("risk_level")
        })

        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # Generate individual explanation components
        classification_explanation = self._generate_classification_explanation(classification)
        policy_explanation = self._generate_policy_explanation(policy_analysis)
        risk_explanation = self._generate_risk_explanation(risk_assessment)
        financial_explanation = self._generate_financial_explanation(risk_assessment)

        # For complex scenarios, use AI to generate more natural explanations
        if classification.get("confidence", 0) < 0.7 or risk_assessment.get("risk_level") == "high":
            detailed_explanation = await self._generate_ai_explanation(
                classification, policy_analysis, risk_assessment)
            complex_scenario = True
        else:
            detailed_explanation = "\n\n".join([
                classification_explanation,
                policy_explanation,
                risk_explanation,
                financial_explanation
            ])
            complex_scenario = False

        # Generate concise summary
        summary = await self._generate_summary(
            classification, policy_analysis, risk_assessment)

        result = {
            "summary": summary,
            "classification_explanation": classification_explanation,
            "policy_explanation": policy_explanation,
            "risk_explanation": risk_explanation,
            "financial_explanation": financial_explanation,
            "detailed_explanation": detailed_explanation,
            "complex_scenario": complex_scenario
        }

        # Cache result
        self.cache.store(cache_key, result)

        return result

    def _generate_classification_explanation(self, classification: Dict) -> str:
        """Generate explanation for classification results."""
        category = classification.get("category", "unknown")
        confidence = classification.get("confidence", 0)
        reasoning = classification.get("reasoning", "the elements described in the scenario")

        return self.templates["classification"].format(
            category=category.replace("_", " "),
            confidence=confidence,
            reasoning=reasoning
        )

    def _generate_policy_explanation(self, policy_analysis: Dict) -> str:
        """Generate explanation for policy analysis."""
        primary = policy_analysis.get("primary_coverage")
        if not primary:
            return "No applicable insurance policies were identified for this scenario."

        policy_details = policy_analysis.get("policy_details", {}).get(primary, {})
        policy_description = policy_details.get("description", "provides relevant coverage")

        gaps = policy_analysis.get("coverage_gaps", [])
        gap_explanation = ""
        if gaps:
            gap_explanation = "However, there may be coverage gaps: " + ", ".join(
                [gap.get("description", "") for gap in gaps])

        return self.templates["policy"].format(
            primary_policy=primary.replace("_", " "),
            policy_description=policy_description,
            gap_explanation=gap_explanation
        )

    def _generate_risk_explanation(self, risk_assessment: Dict) -> str:
        """Generate explanation for risk assessment."""
        risk_level = risk_assessment.get("risk_level", "moderate")
        risk_score = risk_assessment.get("risk_score", 0.5)

        concerns = risk_assessment.get("primary_concerns", [])
        risk_explanation = ""
        if concerns:
            risk_explanation = "Key concerns include: " + ", ".join(concerns)

        return self.templates["risk"].format(
            risk_level=risk_level,
            risk_score=risk_score,
            risk_explanation=risk_explanation
        )

    def _generate_financial_explanation(self, risk_assessment: Dict) -> str:
        """Generate explanation for financial impact."""
        financial_impact = risk_assessment.get("financial_impact_estimate", {})
        if not financial_impact:
            return ""

        return self.templates["financial"].format(
            low_estimate=financial_impact.get("low_estimate", 0),
            median_estimate=financial_impact.get("median_estimate", 0),
            high_estimate=financial_impact.get("high_estimate", 0)
        )

    async def _generate_ai_explanation(self, classification: Dict,
                                 policy_analysis: Dict,
                                 risk_assessment: Dict) -> str:
        """Generate more natural explanation using AI."""
        # Prepare context for AI
        context = {
            "classification": {
                "category": classification.get("category", ""),
                "confidence": classification.get("confidence", 0),
                "reasoning": classification.get("reasoning", "")
            },
            "policy_analysis": {
                "primary_coverage": policy_analysis.get("primary_coverage", ""),
                "coverage_gaps": [gap.get("description", "") for gap in policy_analysis.get("coverage_gaps", [])]
            },
            "risk_assessment": {
                "risk_level": risk_assessment.get("risk_level", ""),
                "risk_score": risk_assessment.get("risk_score", 0),
                "primary_concerns": risk_assessment.get("primary_concerns", []),
                "financial_impact": risk_assessment.get("financial_impact_estimate", {})
            }
        }

        try:
            completion = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """You are an insurance expert assistant.
                     Generate a natural, cohesive explanation of the insurance scenario analysis
                     provided. Explain the classification, policy implications, risk assessment,
                     and financial impact in a clear, professional, and informative way.
                     Keep your explanation concise but comprehensive (3-4 paragraphs)."""},
                    {"role": "user", "content": f"Generate an explanation based on this analysis: {json.dumps(context)}"}
                ],
                temperature=0.3,
                max_tokens=400
            )

            return completion.choices[0].message.content.strip()
        except Exception as e:
            # Fallback to template-based explanation
            return "\n\n".join([
                self._generate_classification_explanation(classification),
                self._generate_policy_explanation(policy_analysis),
                self._generate_risk_explanation(risk_assessment),
                self._generate_financial_explanation(risk_assessment)
            ])

    async def _generate_summary(self, classification: Dict,
                          policy_analysis: Dict,
                          risk_assessment: Dict) -> str:
        """Generate a concise summary of the analysis."""
        category = classification.get("category", "unknown").replace("_", " ")
        risk_level = risk_assessment.get("risk_level", "moderate")
        primary_policy = policy_analysis.get("primary_coverage", "unknown").replace("_", " ")

        # Simple template-based summary
        return f"This {category} incident has a {risk_level} risk level. Primary coverage: {primary_policy}."
