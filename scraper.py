import re
import os
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load API keys from environment
load_dotenv()

# Try loading YouTube Transcript API
HAS_YT_API = False
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    HAS_YT_API = True
except ImportError:
    pass

def extract_youtube_video_id(url: str):
    """
    Extracts the 11-character video ID from a YouTube URL.
    """
    # e.g., https://www.youtube.com/watch?v=dQw4w9WgXcQ
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    # e.g., https://youtu.be/dQw4w9WgXcQ
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return None

def get_youtube_transcript(video_url: str):
    """
    Uses youtube-transcript-api to download the video transcript text.
    """
    if not HAS_YT_API:
        print("youtube-transcript-api is not installed.")
        return None
        
    video_id = extract_youtube_video_id(video_url)
    if not video_id:
        return None
    try:
        # Fetch transcript (tries English by default, supports auto-generated)
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([t['text'] for t in transcript_list])
        return transcript_text
    except Exception as e:
        print(f"Error fetching YouTube transcript for {video_id}: {e}")
        return None

def run_heuristics_fallback(combined_text):
    """
    Standard regex-based pattern matching fallback if AI API is unavailable or fails.
    """
    candidate_matches = {
        "Asiwaju Bola Tinubu": ["tinubu", "bola tinubu", "asiwaju"],
        "Atiku Abubakar": ["atiku", "abubakar", "atiku abubakar"],
        "Peter Obi": ["peter obi", "obi", "obidient"],
        "Babajide Sanwo-Olu": ["sanwo-olu", "sanwoolu", "babajide"],
        "Seyi Makinde": ["makinde", "seyi makinde"],
        "Abdulrahman Abdulrazaq": ["abdulrazaq", "kwara governor"],
        "Adams Oshiomhole": ["oshiomhole", "adams oshiomhole"]
    }
    
    detected_candidate = None
    for cand_name, aliases in candidate_matches.items():
        if any(alias in combined_text.lower() for alias in aliases):
            detected_candidate = cand_name
            break

    states = ["Lagos", "Kano", "Rivers", "Kaduna", "Oyo", "Enugu", "Anambra", "FCT", "Kwara", "Edo", "Delta", "Ogun", "Ondo", "Abia", "Borno", "Plateau", "Bauchi", "Sokoto", "Benue", "Kogi", "Imo", "Taraba", "Adamawa", "Yobe", "Gombe", "Jigawa", "Katsina", "Kebbi", "Zamfara", "Nasarawa", "Niger", "Ekiti", "Osun", "Bayelsa", "Cross River", "Akwa Ibom"]
    detected_state = "FCT"
    for state in states:
        if state.lower() in combined_text.lower():
            detected_state = state
            break

    bus_match = re.search(r'(\d{1,4})\s*(?:coaster\s*)?buses', combined_text, re.IGNORECASE)
    buses = int(bus_match.group(1)) if bus_match else 150

    suv_match = re.search(r'(\d{1,3})\s*(?:suvs|suv|vehicles in convoy|convoy cars|cars)', combined_text, re.IGNORECASE)
    suvs = int(suv_match.group(1)) if suv_match else 25

    delegate_match = re.search(r'(\d{1,3}(?:,\d{3})+|\d{3,6})\s*(?:delegates|supporters|supporters packed|crowd|youths|people|attendees)', combined_text, re.IGNORECASE)
    if delegate_match:
        delegates_str = delegate_match.group(1).replace(',', '')
        delegates = int(delegates_str)
    else:
        delegates = 8000

    return {
        "candidate": detected_candidate,
        "state": detected_state,
        "buses": buses,
        "suvs": suvs,
        "delegates": delegates,
        "venue_cost": 5000000.0,
        "publicity_cost": 15000000.0
    }

def scrape_article(url: str):
    try:
        title = "Scraped Report"
        combined_text = ""
        is_youtube = "youtube.com" in url or "youtu.be" in url

        if is_youtube:
            # Handle YouTube URL
            transcript = get_youtube_transcript(url)
            if transcript:
                combined_text = f"YouTube video transcript content: {transcript}"
                title = "YouTube Video Coverage Transcript"
            else:
                # If transcript fetching fails, get page metadata details
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                headers = {'User-Agent': 'Mozilla/5.0'}
                res = requests.get(url, headers=headers, timeout=10, verify=False)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    title = soup.title.string if soup.title else "YouTube Video"
                    meta_desc = soup.find('meta', attrs={'name': 'description'})
                    desc_text = meta_desc['content'] if meta_desc else ""
                    combined_text = f"YouTube Video Title: {title}. Video Description: {desc_text}"
        else:
            # Standard HTML webpage scraping
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            res = requests.get(url, headers=headers, timeout=10, verify=False)
            if res.status_code != 200:
                return {"error": f"Failed to fetch webpage (Status code: {res.status_code})"}
            
            soup = BeautifulSoup(res.text, 'html.parser')
            title = soup.title.string if soup.title else "News Article"
            paragraphs = soup.find_all('p')
            body_text = " ".join([p.get_text() for p in paragraphs])
            combined_text = f"{title} {body_text}"

        parsed_data = None
        openai_key = os.environ.get("OPENAI_API_KEY")
        used_openai = False

        # Call OpenAI Chat Completion via direct REST endpoint
        if openai_key and len(combined_text) > 50:
            try:
                endpoint = "https://api.openai.com/v1/chat/completions"
                headers_openai = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {openai_key}"
                }
                
                prompt = f"""
                You are a campaign finance auditor analyzing a news report of a political rally in Nigeria.
                Read the news article content below and extract the campaign parameters to estimate expenditure logs.
                
                Analyze the description to estimate:
                - candidate: Name of candidate (must match one of: "Asiwaju Bola Tinubu", "Atiku Abubakar", "Peter Obi", "Babajide Sanwo-Olu", "Seyi Makinde", "Abdulrahman Abdulrazaq", "Adams Oshiomhole", or null if not identified).
                - state: The Nigerian state or location where the event took place (e.g. "Lagos", "Kano", "Rivers", "Kaduna", "Oyo", "Enugu", "Anambra", "FCT").
                - buses: Number of buses hired for transportation. (If mentioned, use it. If vague like "hundreds of buses", estimate 150. Default if completely missing: 100).
                - suvs: Number of VIP vehicles/SUVs in the convoy. (If mentioned, use it. Default if missing: 20).
                - delegates: Number of mobilized attendees/delegates. (If text says e.g. "thousands of supporters", estimate 5000. If "tens of thousands", estimate 15000. Default if missing: 5000).
                - venue_cost: Cost of stadium/arena hire. (If it mentions a major stadium e.g. Teslim Balogun, National Stadium, estimate 10000000. For community halls, estimate 2000000. Default: 5000000).
                - publicity_cost: Cost of media/billboards/hype mentioned. (Default: 15000000).

                Provide your answer STRICTLY as a raw JSON object with keys:
                "candidate", "state", "buses", "suvs", "delegates", "venue_cost", "publicity_cost"

                Article Content:
                {combined_text[:5000]}
                """
                
                payload = {
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
                
                response = requests.post(endpoint, json=payload, headers=headers_openai, timeout=15, verify=False)
                if response.status_code == 200:
                    resp_json = response.json()
                    text_out = resp_json["choices"][0]["message"]["content"].strip()
                    parsed_data = json.loads(text_out)
                    used_openai = True
                else:
                    print(f"OpenAI REST API returned error status {response.status_code}: {response.text}")
            except Exception as ex:
                print(f"OpenAI REST API execution failed, falling back to heuristics: {ex}")
                parsed_data = None

        if not parsed_data:
            parsed_data = run_heuristics_fallback(combined_text)

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

        return {
            "candidate": parsed_data.get("candidate"),
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
            "source_url": url,
            "title": title[:100] + "..." if len(title) > 100 else title,
            "parsed_via": "OpenAI API (gpt-4o-mini)" if used_openai else "Rule heuristics"
        }
    except Exception as e:
        return {"error": f"Error scraping article: {str(e)}"}
