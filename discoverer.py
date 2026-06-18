import os
import requests
from dotenv import load_dotenv
from scraper import scrape_article

# Load environment
load_dotenv()

def discover_rallies(candidate_name: str):
    """
    Queries Tavily Search API directly via REST with SSL verification disabled
    to find recent news articles covering political rallies for a candidate.
    """
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        return {"error": "Tavily API key is not configured in .env file."}
        
    try:
        # Formulate optimal search query for logistics/campaign details
        query = f"{candidate_name} campaign rally crowd size transportation buses vehicles Nigeria news"
        print(f"Running Tavily search via REST for query: {query}")
        
        # REST Endpoint & Payload
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": tavily_key,
            "query": query,
            "max_results": 3,
            "include_raw_content": True
        }
        
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Execute POST request with SSL verification disabled
        response = requests.post(url, json=payload, timeout=12, verify=False)
        
        if response.status_code != 200:
            return {"error": f"Tavily search API returned status {response.status_code}: {response.text}"}
            
        data = response.json()
        results = data.get("results", [])
        if not results:
            return {"error": f"No recent campaign news found for candidate {candidate_name}."}

        # Process results
        discovered_items = []
        for res in results:
            article_url = res.get("url")
            # Run the parser directly on the URL
            parsed = scrape_article(article_url)
            if "error" not in parsed:
                discovered_items.append(parsed)

        if not discovered_items:
            return {"error": "Failed to parse campaign details from search results."}

        return {
            "candidate": candidate_name,
            "results": discovered_items
        }

    except Exception as e:
        return {"error": f"Tavily search execution failed: {str(e)}"}
