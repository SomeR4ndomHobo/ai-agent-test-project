from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import WebsiteSearchTool
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

llm = LLM(
    model="openai/gpt-5-mini"
)

webSearchTool = WebsiteSearchTool()

finderAgent = Agent(
    role="Sports Card Finder Agent",
    goal="Find whether the sports card exists.",
    backstory=finderInstructions,
    tools=[
        webSearchTool
    ],
    llm=llm
)

researchAgent = Agent(
    role="Sports Card Research Agent",
    goal="Research the sports card and its market value.",
    backstory=researchInstructions,
    tools=[
        webSearchTool
    ],
    llm=llm
)

playerResearchAgent = Agent(
    role="Sports Card Player Research Agent",
    goal="Research the player associated with the sports card.",
    backstory=playerResearchInstructions,
    tools=[
        webSearchTool
    ],
    llm=llm
)

def run_agent_crewai(ocr_text, card_filename=""):
    finderTask = Task(
        description=f"""
        {ocr_text}
        """,
        expected_output='Return only "Yes" or "No".',
        agent=finderAgent
    )

    finderCrew = Crew(
        agents=[finderAgent],
        tasks=[finderTask],
        process=Process.sequential
    )

    finder_output = str(finderCrew.kickoff()).strip()

    if finder_output.lower().strip().rstrip(".!") != "yes":
        save_output(
            finder_output,
            f"results/crewai/{card_filename}/output.txt"
        )
        return finder_output
    
    researchTask = Task(
        description=f"""
        {ocr_text}
        """,
        expected_output="A complete sports-card market research report.",
        agent=researchAgent
    )

    playerResearchTask = Task(
        description=f"""
        {ocr_text}
        """,
        expected_output="A complete player research report.",
        agent=playerResearchAgent
    )

    crew = Crew(
        agents=[
            researchAgent,
            playerResearchAgent
        ],
        tasks=[
            researchTask,
            playerResearchTask
        ],
        process=Process.sequential
    )

    output = crew.kickoff()
    output = str(finder_output) + "\n" + str(output)

    print(output)
    save_output(output, f"results/crewai/{card_filename}/output.txt")
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
