import asyncio
import argparse
from src.classifiers.scenario_classifier import ScenarioClassifier

async def process_scenario(scenario_text: str):
    classifier = ScenarioClassifier()
    try:
        result = await classifier.classify_scenario(scenario_text)
        print("\nClassification Results:")
        print(f"Category: {result['category']}")
        print(f"Confidence: {result['confidence']:.2%}")
        print("Relevant Policies:", ", ".join(result["relevant_policies"]))
    except Exception as e:
        print(f"Error: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Auto Insurance Scenario Classifier')
    parser.add_argument('--scenario', type=str, help='Insurance scenario to classify')
    args = parser.parse_args()

    if args.scenario:
        asyncio.run(process_scenario(args.scenario))
    else:
        print("Please enter your insurance scenario (press Ctrl+D when finished):")
        scenario_lines = []
        try:
            while True:
                line = input()
                scenario_lines.append(line)
        except EOFError:
            scenario_text = "\n".join(scenario_lines)
            asyncio.run(process_scenario(scenario_text))

if __name__ == "__main__":
    main()