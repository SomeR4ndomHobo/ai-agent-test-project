from http import client
import json
import os
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parent

ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY was not found.\n"
        f"Expected .env file at: {ENV_FILE}"
    )

client = OpenAI(
    api_key=OPENAI_API_KEY
)

def research_card(raw_ocr):
    """
    Research a graded trading card using only the raw OCR
    extracted from the slab label.
    """

    ocr_lines = []

    for item in raw_ocr:
        text = item.get("text", "").strip()
        confidence = item.get("confidence")

        if not text:
            continue

        if confidence is not None:
            ocr_lines.append(
                f"{text} [OCR confidence: {confidence:.2%}]"
            )
        else:
            ocr_lines.append(text)

    ocr_text = "\n".join(ocr_lines)

    prompt = f"""
You are a sports trading-card research agent.

The following text was extracted directly from the label
of a graded trading card using OCR.

RAW OCR:

{ocr_text}


Your job is to determine what card this is using ONLY the
OCR above as the initial identification evidence.

Then use live web research to verify the identification
and research the player and exact card.


============================================================
1. IDENTIFY THE CARD
============================================================

Determine:

- player name
- sport
- manufacturer
- exact set/product
- card number
- insert name
- parallel or variation, if applicable
- year/season
- grader
- grade
- certification number
- whether this is a true rookie card

Do not blindly trust the OCR.

OCR may contain spelling mistakes or incorrectly recognized
characters.

Use web research to verify the identity.

If multiple cards could match, report the uncertainty rather
than guessing.


============================================================
2. PLAYER STATISTICS
============================================================

Once the player is identified, research current player
statistics.

Prefer authoritative sources such as:

- NHL.com
- MLB.com
- NBA.com
- NFL.com
- ESPN
- Hockey Reference
- Baseball Reference
- Basketball Reference
- Pro Football Reference

State your sources and provide links to the statistics.

For hockey include:

- current team
- position
- season
- games played
- goals
- assists
- points
- career games
- career goals
- career assists
- career points

For another sport, return the most relevant statistics
for that sport.

Include if the player is retired or active.

Find age and birthdate.

Find if they are alive or deceased.


============================================================
3. CARD STATISTICS
============================================================

Research the EXACT card identified from the slab.

Try to find:

- PSA total population
- PSA population at this exact grade
- population higher
- approximate raw market value
- approximate graded market value
- recent completed sales
- sale dates
- sale prices
- currency
- whether sales data is sparse
- any market notes or trends
- Whether prices of this card are rising, falling, or stable
- The URL of the card on a reputable card marketplace or price guide


Prefer sources such as:

- PSA
- Beckett
- CGC
- SportsCardsPro / PriceCharting
- Card Ladder
- eBay sold/completed listings
- reputable card checklists


============================================================
IMPORTANT
============================================================

Do not confuse this card with another card belonging to
the same player.

Do not confuse an insert, tribute, reprint, or renewed card
with the player's original rookie card.

Do not invent population numbers.

Do not invent sale prices.

Do not treat an asking price as a completed sale.

A source must mention the card.

Do not bring up unrelated sources or players.

If information cannot be verified, use null.

If sources disagree, explain the disagreement.

Return ONLY valid JSON.


Use this structure:

{{
    "identification": {{
        "player": null,
        "sport": null,
        "manufacturer": null,
        "set": null,
        "card_number": null,
        "insert": null,
        "parallel": null,
        "year": null,
        "rookie_card": null,
        "grader": null,
        "grade": null,
        "certification_number": null,
        "source:" null
    }},

    "player_statistics": {{
        "season": null,
        "team": null,
        "position": null,
        "season_stats": {{}},
        "career_stats": {{}},
        "source:" null,
        "player_url:" null,
        "age": null,
        "birthdate": null,
        "alive": null
    }},

    "card_statistics": {{
        "psa_total_population": null,
        "psa_grade_population": null,
        "population_higher": null,
        "raw_market_value": null,
        "graded_market_value": null,
        "recent_sales": [],
        "sales_data_sparse": null,
        "market_notes": null,
        "price_trend": null,
        "source:" null,
        "card_url:" null
    }},
    "research_notes": []
}}
"""

    response = client.responses.create(
        model="gpt-5",
        tools=[
            {
                "type": "web_search"
            }
        ],
        input=prompt,
    )

    text = response.output_text.strip()

    # Remove markdown code fences if the model returns them.
    if text.startswith("```json"):
        text = text[7:]

    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    try:
        return json.loads(text)

    except json.JSONDecodeError:

        print()
        print("WARNING: Research response was not valid JSON.")
        print()
        print("RAW RESPONSE:")
        print(text)

        return {
            "error": "Research returned invalid JSON",
            "raw_response": text,
        }
