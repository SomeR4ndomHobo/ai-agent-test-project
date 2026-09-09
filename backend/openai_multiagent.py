from agents import Agent, Runner, WebSearchTool
from os import makedirs
from pathlib import Path

finderInstructions = """
You are a sports-card finder.
You will receive raw OCR text extracted from a graded sports card label.

Search online for the exact card based on the OCR text and return only "Yes" or "No" if the card exists. 
"""


researchInstructions = """
You are a sports-card research agent.

You will receive raw OCR text extracted from a graded sports card label.

Your job is to:

1. Identify the exact graded card from the OCR text.
2. Research the card's current economic value.
3. Assess whether the card's value is more likely to rise, fall, or remain stable.

If the card does not have a player on it, deny the request and explain that you cannot research non-player cards.

CARD RESEARCH

Determine, when possible:

- Player name
- Card year
- Manufacturer
- Set/product
- Card number
- Insert or parallel
- Grading company
- Grade
- Certification number

Research:

- Recent confirmed sales of the exact card
- Approximate current market value
- Population at the exact grade, if available
- Total graded population, if available
- Whether sales data is sparse or liquid

Prefer completed sales over asking prices.

Never present an asking price as a completed sale.

Do not invent sales, prices, population reports, or grading data.

If exact-card market information cannot be verified, say so.

Classify the card's likely near-to-medium-term value direction as:

- RISE
- FALL
- STABLE
- UNCERTAIN

Base the assessment on evidence such as:

- recent sale trends
- player performance
- career stage
- awards/accomplishments
- collector demand
- scarcity/population
- whether the card is a true rookie, insert, parallel, reprint, or tribute

Do not make strong predictions when evidence is weak.

Clearly distinguish facts from your assessment.

SOURCES

Provide reputable sources for factual claims.

Prefer:

- official league websites
- official team websites
- Baseball Reference / Hockey Reference / Basketball Reference / Pro Football Reference
- reputable card-market sources
- confirmed marketplace sales

Do not rely on a single source if better corroboration is available.


OUTPUT FORMAT

Return these sections:

CARD IDENTIFICATION

MARKET VALUE

RECENT SALES

VALUE OUTLOOK

SOURCES
"""

playerResearchInstructions = """
You are a sports-card player research agent. 
You will receive raw OCR text extracted from a graded sports card label.

Find the sports player associated with the card and research their statistics, biographical information, and major accomplishments.

Find the following:
- Full name
- Date of birth
- Age
- Sport
- Position or role
- Current team
- Previous notable teams
- Whether the player is still active
- Major accomplishments
- Relevant career and recent-season statistics

Prefer official league/team sources and reputable statistical databases.
"""

finderAgent = Agent(name="Sports Card Finder Agent", 
            instructions= finderInstructions,
            tools=[
                WebSearchTool(
                    search_context_size="medium"
                    )
                ]
            )

researchAgent = Agent(name="Sports Card Research Agent", 
            instructions= researchInstructions,
            tools=[
                WebSearchTool(
                    search_context_size="medium"
                    )
                ]
            )

playerResearchAgent = Agent(name="Sports Card Player Research Agent", 
            instructions= playerResearchInstructions,
            tools=[
                WebSearchTool(
                    search_context_size="medium"
                    )
                ]
            )

def run_single_agent(agent: Agent, input_text: str):
    try:
        result = Runner.run_sync(
            agent,
            input_text
        )

        return result.final_output

    except Exception as e:
        print(f"Error running {agent.name}: {e}")
        return None

def run_agent_openai(ocr_text, card_filename=""):
    finder_output = Runner.run_sync(
        finderAgent,
        [{
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": str(ocr_text)
                }
            ],
            "type": "message"
        }]
    ).final_output

    if finder_output.lower().strip().rstrip(".!") != "yes":
        output = finder_output
        print(output)
        save_output(output, f"results/openai/{card_filename}/output.txt")
        return output

    output = finder_output + "\n"

    output += Runner.run_sync(
        researchAgent,
        [{
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": str(ocr_text)
                }
            ],
            "type": "message"
        }]
    ).final_output

    output += Runner.run_sync(
        playerResearchAgent,
        [{
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": str(ocr_text)
                }
            ],
            "type": "message"
        }]
    ).final_output

    print(output)
    save_output(output, f"results/openai/{card_filename}/output.txt")
    return output

def save_output(
    data,
    filename
):
    makedirs(
        Path(filename).parent,
        exist_ok=True
    )
    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:
        print(data, file=file)