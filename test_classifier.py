import asyncio
import os
from dotenv import load_dotenv
from src.classifiers.scenario_classifier import ScenarioClassifier

async def main():
    # Load environment variables
    load_dotenv()
    
    # Ensure we have an API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not found in environment variables")
        return
        
    classifier = ScenarioClassifier()
    scenario = """
    A driver rear-ended my car at a stop light. There was visible damage 
    to my rear bumper. The incident occurred on a clear day with good visibility.
    """
    
    try:
        result = await classifier.classify_scenario(scenario)
        print("Classification Results:", result)
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())