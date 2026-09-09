from langgraph.graph import StateGraph, START, END
from langchain.agents import create_agent
from langchain_tavily import TavilySearch
from os import makedirs
from pathlib import Path
from typing import TypedDict
from dotenv import load_dotenv

load_dotenv()

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

webSearchTool = TavilySearch(
    max_results=8
)

finderAgent = create_agent(
    model="openai:gpt-5-mini",
    tools=[
        webSearchTool
    ],
    system_prompt=finderInstructions
)

researchAgent = create_agent(
    model="openai:gpt-5-mini",
    tools=[
        webSearchTool
    ],
    system_prompt=researchInstructions
)

playerResearchAgent = create_agent(
    model="openai:gpt-5-mini",
    tools=[
        webSearchTool
    ],
    system_prompt=playerResearchInstructions
)

class CardState(TypedDict):
    ocr_text: str
    finder_output: str
    research_output: str
    player_output: str


def finder_node(state):
    result = finderAgent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": str(state["ocr_text"])
                }
            ]
        }
    )

    return {
        "finder_output": result["messages"][-1].content
    }


def research_node(state):
    result = researchAgent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": str(state["ocr_text"])
                }
            ]
        }
    )

    return {
        "research_output": result["messages"][-1].content
    }


def player_research_node(state):
    result = playerResearchAgent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": str(state["ocr_text"])
                }
            ]
        }
    )

    return {
        "player_output": result["messages"][-1].content
    }


def finder_route(state):
    result = state["finder_output"].lower().strip().rstrip(".!")

    if result == "yes":
        return "research"

    return END


graph = StateGraph(CardState)

graph.add_node(
    "finder",
    finder_node
)

graph.add_node(
    "research",
    research_node
)

graph.add_node(
    "playerResearch",
    player_research_node
)

graph.add_edge(
    START,
    "finder"
)

graph.add_conditional_edges(
    "finder",
    finder_route
)

graph.add_edge(
    "research",
    "playerResearch"
)

graph.add_edge(
    "playerResearch",
    END
)

cardGraph = graph.compile()


def run_agent_langraph(ocr_text, card_filename=""):
    result = cardGraph.invoke(
        {
            "ocr_text": str(ocr_text),
            "finder_output": "",
            "research_output": "",
            "player_output": ""
        }
    )

    output = result["finder_output"] + "\n"
    output += result["research_output"]
    output += result["player_output"]

    print(output)
    save_output(output, f"results/langgraph/{card_filename}/output.txt")
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