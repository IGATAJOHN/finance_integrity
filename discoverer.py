import os
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from scraper import scrape_article, get_youtube_transcript

# Load environment
load_dotenv()

def discover_rallies(candidate_name: str):
    """
    Queries Tavily Search API directly via REST to get top 3 search results.
    Downloads the text (or transcripts if YouTube links).
    Sends all consolidated sources to OpenAI to compute a consensus estimate.
    """
    tavily_key = os.environ.get("TAVILY_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not tavily_key:
        return {"error": "Tavily API key is not configured in .env file."}
    if not openai_key:
        return {"error": "OpenAI API key is not configured in .env file."}
        
    try:
        # Query formulated for logistics, transportation, and delegate metrics
        query = f"{candidate_name} campaign rally crowd size transportation buses vehicles Nigeria news"
        print(f"Running Tavily consensus search for query: {query}")
        
        # REST Tavily call
        url_tavily = "https://api.tavily.com/search"
        payload_tavily = {
            "api_key": tavily_key,
            "query": query,
            "max_results": 3,
            "include_raw_content": True
        }
        
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        tav_res = requests.post(url_tavily, json=payload_tavily, timeout=12, verify=False)
        if tav_res.status_code != 200:
            return {"error": f"Tavily search API returned status {tav_res.status_code}"}
            
        data = tav_res.json()
        results = data.get("results", [])
        if not results:
            return {"error": f"No recent campaign news found for candidate {candidate_name}."}

        # Fetch contents for all 3 results
        articles_texts = []
        sources_meta = []
        
        for idx, res in enumerate(results):
            art_url = res.get("url")
            art_title = res.get("title", "News Source")
            content = ""
            
            is_youtube = "youtube.com" in art_url or "youtu.be" in art_url
            if is_youtube:
                transcript = get_youtube_transcript(art_url)
                if transcript:
                    content = f"Source {idx+1} (YouTube Video Transcript): {transcript}"
                else:
                    content = f"Source {idx+1} (YouTube Video Title/Desc): {art_title}. {res.get('content', '')}"
            else:
                # Standard HTML page extraction (try scraping, fallback to Tavily snippet)
                try:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    html_res = requests.get(art_url, headers=headers, timeout=8, verify=False)
                    if html_res.status_code == 200:
                        soup = BeautifulSoup(html_res.text, 'html.parser')
                        paragraphs = soup.find_all('p')
                        body_text = " ".join([p.get_text() for p in paragraphs])
                        content = f"Source {idx+1} (Article Text): {art_title}. {body_text}"
                    else:
                        content = f"Source {idx+1} (Snippet): {art_title}. {res.get('content', '')}"
                except Exception:
                    content = f"Source {idx+1} (Snippet): {art_title}. {res.get('content', '')}"
                    
            articles_texts.append(content[:4000]) # Cap source length to prevent token bloat
            sources_meta.append({"title": art_title, "url": art_url})

        # Compile OpenAI prompt for consensus calculation
        compiled_sources_text = "\n\n=== SOURCE BUNDLE ===\n\n".join(articles_texts)
        
        openai_endpoint = "https://api.openai.com/v1/chat/completions"
        headers_openai = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai_key}"
        }
        
        prompt = f"""
        You are a campaign finance auditor. Below are up to 3 different news/media sources covering campaign activities for "{candidate_name}" in Nigeria.
        Analyze and compare the texts. Resolve any discrepancies and calculate a balanced, consensus-driven estimate of the logistics variables:

        Extract the following metrics:
        - candidate: Name of the candidate (must match: "Asiwaju Bola Tinubu", "Atiku Abubakar", "Peter Obi", "Babajide Sanwo-Olu", "Seyi Makinde", "Abdulrahman Abdulrazaq", "Adams Oshiomhole", or null).
        - state: The location/state of the rally.
        - buses: Number of buses hired. (Compare estimates across sources. If conflicting, output a logical average. Default: 100).
        - suvs: Number of VIP convoy vehicles. (Default: 20).
        - delegates: Number of mobilized attendees. (If numbers differ e.g., one source says 5,000 another says 10,000, calculate a logical average like 7500. Default: 5000).
        - venue_cost: Stadium/arena hire. (Default: 5000000).
        - publicity_cost: Media ads/billboards cost. (Default: 15000000).

        Provide your answer STRICTLY as a raw JSON object with keys:
        "candidate", "state", "buses", "suvs", "delegates", "venue_cost", "publicity_cost"

        SOURCES:
        {compiled_sources_text}
        """
        
        payload_openai = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "response_format": { "type": "json_object" },
            "temperature": 0.2
        }

        # Query OpenAI REST endpoint
        openai_res = requests.post(openai_endpoint, json=payload_openai, headers=headers_openai, timeout=18, verify=False)
        if openai_res.status_code != 200:
            return {"error": f"OpenAI API returned status code {openai_res.status_code}"}
            
        resp_json = openai_res.json()
        text_out = resp_json["choices"][0]["message"]["content"].strip()
        parsed_data = json.loads(text_out)
        
        # Logistics averages
        bus_hire_cost = 60000.0
        fuel_liters = 50.0
        fuel_price = 1200.0
        allowance = 10000.0

        buses = parsed_data.get("buses", 100)
        suvs = parsed_data.get("suvs", 20)
        delegates = parsed_data.get("delegates", 5000)
        venue_cost = parsed_data.get("venue_cost", 5000000.0)
        publicity_cost = parsed_data.get("publicity_cost", 15000000.0)

        # Calculations
        bus_total = buses * bus_hire_cost
        fuel_total = (buses + suvs) * fuel_liters * fuel_price
        delegate_total = delegates * allowance
        venue_pub_total = venue_cost + publicity_cost
        total_rally_cost = bus_total + fuel_total + delegate_total + venue_pub_total

        primary_match = sources_meta[0]

        return {
            "candidate": parsed_data.get("candidate") or candidate_name,
            "results": [{
                "candidate": parsed_data.get("candidate") or candidate_name,
                "state": parsed_data.get("state") or "FCT",
                "buses": buses,
                "bus_hire_cost": bus_hire_cost,
                "suvs": suvs,
                "fuel_liters": fuel_liters,
                "fuel_price": fuel_price,
                "delegates": delegates,
                "allowance": allowance,
                "venue_cost": venue_cost,
                "publicity_cost": publicity_cost,
                "total_rally_cost": total_rally_cost,
                "source_url": primary_match["url"],
                "title": f"Consensus Audit: {primary_match['title']}",
                "parsed_via": "OpenAI API (gpt-4o-mini)"
            }]
        }
        
    except Exception as e:
        return {"error": f"Error running consensus discovery: {str(e)}"}
