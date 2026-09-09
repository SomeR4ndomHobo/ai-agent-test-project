import json
from pathlib import Path

from dotenv import load_dotenv

from pydantic_multiagent import run_agent_pydantic
from crewai_multiagent import run_agent_crewai
from langraph_multiagent import run_agent_langraph
from openai_multiagent import run_agent_openai

from ocr import identify_card, print_ocr_results

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

def save_report(
    data,
    filename="results/card_report.json"
):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )

def main():

    image_path = input("Please input the card's file path. Say 'bye' to quit out.\n")
    print()
    while(image_path != "bye"):
        try:
            card_result = identify_card(
                image_path
            )

            print_ocr_results(card_result)

            print()
            print("OCR CARD RESULT")

            print(
                json.dumps(
                    card_result,
                    indent=2,
                )
            )

            print()

            ai_model = input("Please input the AI model to use (crewai, psydantic, langraph, openai)\n Say 'bye' to quit out.\n")
            while(ai_model != "bye"):
                print("RESEARCHING PLAYER + CARD")

                if(ai_model == "crewai"):
                    research_result = run_agent_crewai(
                        card_result["raw_ocr"],
                        image_path
                    )

                elif(ai_model == "psydantic"):
                    research_result = run_agent_pydantic(
                        card_result["raw_ocr"],
                        image_path
                    )

                elif(ai_model == "langraph"):
                    research_result = run_agent_langraph(
                        card_result["raw_ocr"],
                        image_path
                    )

                elif(ai_model == "openai"):
                    research_result = run_agent_openai(
                        card_result["raw_ocr"],
                        image_path
                    )
                else:
                    print("Invalid AI model specified. Please choose from crewai, psydantic, langraph, or openai.")
                    continue

                ai_model = ""
                ai_model = input("Please input the AI model to use (crewai, psydantic, langraph, openai)\n Say 'bye' to quit out.\n")

            image_path = ""
            image_path = input("Please input the card's file path. Say 'bye' to quit out.\n")

        except Exception as error:

            print()
            print("ERROR")

            print(error)

            print()

            raise


    print("Goodbye!")
if __name__ == "__main__":
    main()