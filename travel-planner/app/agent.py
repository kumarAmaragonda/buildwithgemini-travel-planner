# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import os
import re
import uuid
from zoneinfo import ZoneInfo

from app.a2ui.basic_catalog.provider import BasicCatalog
from app.a2ui.schema.manager import A2uiSchemaManager
from app.a2ui_utils import a2ui_callback
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.tools.tool_context import ToolContext
from google.cloud import storage
from google.genai import types


# WRITE: after each turn, send the session to Memory Bank for extraction.
async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None


MODEL = "gemini-3.8-flash"


from app.firestore_service import (
    get_destination_details,
    list_saved_itineraries,
    save_itinerary,
    search_destinations,
)


import json
import urllib.parse
import urllib.request


def get_live_weather_and_packing_tips(destination: str) -> dict:
    """Fetches real-time live weather and provides packing advice for any destination city.

    Args:
        destination: City or destination name (e.g., 'Kyoto', 'Paris', 'Cape Town', 'Banff').

    Returns:
        A dictionary with live temperature, conditions, wind, precipitation, and packing advice.
    """
    try:
        geo_query = urllib.parse.quote(destination)
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={geo_query}&count=1"
        req = urllib.request.Request(geo_url, headers={"User-Agent": "TravelPlannerAgent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            geo_data = json.loads(resp.read().decode())

        if not geo_data.get("results"):
            return {"error": f"Could not find coordinates for '{destination}'."}

        place = geo_data["results"][0]
        lat, lon = place["latitude"], place["longitude"]
        city_name = place.get("name", destination)
        country = place.get("country", "")

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
            f"&temperature_unit=celsius"
        )
        w_req = urllib.request.Request(weather_url, headers={"User-Agent": "TravelPlannerAgent/1.0"})
        with urllib.request.urlopen(w_req, timeout=5) as w_resp:
            weather_data = json.loads(w_resp.read().decode())

        current = weather_data.get("current", {})
        temp_c = current.get("temperature_2m")
        temp_f = round(temp_c * 9 / 5 + 32, 1) if temp_c is not None else None
        precip = current.get("precipitation", 0.0)
        code = current.get("weather_code", 0)

        # Basic WMO weather code descriptions
        if code == 0:
            condition = "Clear sky"
        elif code in (1, 2, 3):
            condition = "Mainly clear or partly cloudy"
        elif code in (45, 48):
            condition = "Foggy"
        elif code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
            condition = "Rain / Showers"
        elif code in (71, 73, 75, 77, 85, 86):
            condition = "Snow"
        elif code >= 95:
            condition = "Thunderstorm"
        else:
            condition = "Overcast"

        packing = []
        if precip > 0 or "Rain" in condition or "Snow" in condition:
            packing.append("Waterproof jacket or umbrella")
        if temp_c is not None:
            if temp_c < 10:
                packing.extend(["Warm insulated coat", "Gloves / beanie", "Warm layers"])
            elif temp_c < 20:
                packing.extend(["Light jacket or sweater", "Comfortable walking shoes"])
            else:
                packing.extend(["Breathable light clothing", "Sunglasses", "Sunscreen"])

        return {
            "destination": f"{city_name}, {country}".strip(", "),
            "temperature_celsius": temp_c,
            "temperature_fahrenheit": temp_f,
            "condition": condition,
            "precipitation_mm": precip,
            "relative_humidity_pct": current.get("relative_humidity_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "recommended_packing": packing,
        }
    except Exception as e:
        return {"error": f"Failed to fetch live weather: {str(e)}"}


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    q = query.lower()
    if "sf" in q or "san francisco" in q:
        tz_identifier = "America/Los_Angeles"
    elif "kyoto" in q or "tokyo" in q or "japan" in q:
        tz_identifier = "Asia/Tokyo"
    elif "paris" in q or "france" in q:
        tz_identifier = "Europe/Paris"
    elif "florence" in q or "italy" in q or "rome" in q:
        tz_identifier = "Europe/Rome"
    elif "banff" in q or "calgary" in q:
        tz_identifier = "America/Edmonton"
    elif "cape town" in q or "south africa" in q:
        tz_identifier = "Africa/Johannesburg"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


def convert_currency(amount: float, from_currency: str = "USD", to_currency: str = "EUR") -> dict:
    """Converts travel budget or expenses between world currencies using live exchange rates.

    Args:
        amount: The numerical amount of money to convert.
        from_currency: 3-letter currency code to convert from (e.g., 'USD', 'EUR', 'GBP', 'CAD', 'JPY').
        to_currency: 3-letter currency code to convert to (e.g., 'JPY', 'EUR', 'CAD', 'ZAR', 'USD').

    Returns:
        A dictionary with the original amount, converted amount, and exchange rate.
    """
    from_curr = from_currency.upper().strip()
    to_curr = to_currency.upper().strip()

    try:
        url = f"https://open.er-api.com/v6/latest/{from_curr}"
        req = urllib.request.Request(url, headers={"User-Agent": "TravelPlannerAgent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        if data.get("result") != "success":
            return {"error": f"Failed to fetch exchange rates for currency: {from_curr}"}

        rates = data.get("rates", {})
        if to_curr not in rates:
            return {"error": f"Target currency '{to_curr}' not supported."}

        rate = rates[to_curr]
        converted = round(amount * rate, 2)
        return {
            "from_currency": from_curr,
            "to_currency": to_curr,
            "original_amount": amount,
            "exchange_rate": rate,
            "converted_amount": converted,
            "formatted_result": f"{amount:,.2f} {from_curr} = {converted:,.2f} {to_curr} (Rate: {rate:,.4f})",
        }
    except Exception as e:
        return {"error": f"Currency conversion failed: {str(e)}"}


def geocode_address(address: str) -> dict:
    """Converts a street address or location name into geographic coordinates using Google Maps Geocoding API.

    Args:
        address: The address or place name to geocode (e.g. 'Eiffel Tower, Paris' or 'Kinkaku-ji, Kyoto').

    Returns:
        Dictionary containing formatted address, latitude, and longitude.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return {"error": "GOOGLE_MAPS_API_KEY is not configured in environment or .env."}

    try:
        encoded_addr = urllib.parse.quote(address)
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_addr}&key={api_key}"
        req = urllib.request.Request(url, headers={"User-Agent": "TravelPlanner/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())

        if data.get("status") != "OK" or not data.get("results"):
            return {"error": f"Geocoding failed with status: {data.get('status', 'ZERO_RESULTS')}"}

        result = data["results"][0]
        loc = result["geometry"]["location"]
        return {
            "formatted_address": result.get("formatted_address"),
            "location": {
                "latitude": loc["lat"],
                "longitude": loc["lng"],
            },
            "place_id": result.get("place_id"),
        }
    except Exception as e:
        return {"error": f"Geocoding request failed: {str(e)}"}


def find_nearby_places(latitude: float, longitude: float, place_type: str = "restaurant", radius_meters: float = 1000.0) -> dict:
    """Finds nearby points of interest (restaurants, cafes, museums, tourist attractions) using Google Places API (New).

    Args:
        latitude: Latitude coordinate of the center point.
        longitude: Longitude coordinate of the center point.
        place_type: Type of place to look for (e.g., 'restaurant', 'cafe', 'museum', 'tourist_attraction', 'bakery', 'lodging').
        radius_meters: Radius in meters around the location (default: 1000m).

    Returns:
        Dictionary with a list of nearby places containing name, formatted address, and location coordinates.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return {"error": "GOOGLE_MAPS_API_KEY is not configured in environment or .env."}

    try:
        url = "https://places.googleapis.com/v1/places:searchNearby"
        payload = {
            "includedTypes": [place_type],
            "maxResultCount": 10,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    "radius": radius_meters,
                }
            },
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types",
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())

        places = []
        for p in data.get("places", []):
            display_name = p.get("displayName", {}).get("text", "")
            places.append({
                "name": display_name,
                "address": p.get("formattedAddress"),
                "location": p.get("location"),
                "types": p.get("types", []),
            })

        return {
            "search_type": place_type,
            "count": len(places),
            "places": places,
        }
    except Exception as e:
        return {"error": f"Places Nearby search failed: {str(e)}"}


PUBLIC_STORAGE_BUCKET = "qwiklabs-gcp-04-4a6cf1dba233-travel-planner-assets"
_storage_client = None


def get_storage_client() -> storage.Client:
    """Return a Google Cloud Storage client instance."""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project="qwiklabs-gcp-04-4a6cf1dba233")
    return _storage_client


async def generate_and_store_destination_image(
    prompt: str,
    tool_context: ToolContext,
    destination_name: str = "destination",
) -> dict:
    """Generates a scenic visual illustration for a travel destination using Gemini, saves it as an ADK artifact, and uploads it to the public Cloud Storage bucket.

    Args:
        prompt: Detailed description of the image to generate (e.g. 'A vibrant watercolor illustration of Kyoto Golden Pavilion surrounded by autumn red maple trees').
        tool_context: The ADK ToolContext used to save the artifact for the session and UI.
        destination_name: Short name or slug of the destination (e.g. 'kyoto', 'paris').

    Returns:
        Dictionary containing the public Cloud Storage image URL, artifact filename, and status.
    """
    try:
        # 1. Generate image using gemini-3.1-flash-lite-image in global region
        genai_client = genai.Client(
            vertexai=True,
            project="qwiklabs-gcp-04-4a6cf1dba233",
            location="global",
        )
        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=f"Generate an illustration of: {prompt}",
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        image_bytes = None
        mime_type = "image/jpeg"
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    if part.inline_data.mime_type:
                        mime_type = part.inline_data.mime_type
                    break

        if not image_bytes:
            return {"error": "No image data was generated by the model."}

        # 2. Determine file extension and object name
        ext = "png" if "png" in mime_type else "jpg"
        clean_name = re.sub(r"[^a-zA-Z0-9_-]", "_", destination_name.lower())
        unique_id = uuid.uuid4().hex[:8]
        filename = f"{clean_name}_{unique_id}.{ext}"

        # 3. Save as ADK artifact so it appears in the Playground's Artifacts panel
        try:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)
        except Exception as artifact_err:
            print(f"Warning: could not save artifact to tool_context: {artifact_err}")

        # 4. Upload image bytes to public Cloud Storage bucket without writing to local disk
        gcs = get_storage_client()
        bucket = gcs.bucket(PUBLIC_STORAGE_BUCKET)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{PUBLIC_STORAGE_BUCKET}/{filename}"

        return {
            "status": "success",
            "destination": destination_name,
            "filename": filename,
            "public_url": public_url,
            "mime_type": mime_type,
            "message": f"Image successfully generated, saved as artifact '{filename}', and published to {public_url}",
        }
    except Exception as e:
        return {"error": f"Image generation and upload failed: {str(e)}"}


async def generate_and_store_destination_video(
    prompt: str,
    tool_context: ToolContext,
    destination_name: str = "destination",
    duration_seconds: int = 5,
    aspect_ratio: str = "16:9",
) -> dict:
    """Generates a short scenic video preview for a travel destination or attraction using Google's Omni model (gemini-omni-flash-preview) in the global region.
    Saves the video as an ADK artifact (so it appears in the Playground Artifacts panel) and uploads it to the public Cloud Storage bucket.

    Args:
        prompt: Visual description of the short video scene (e.g. 'A smooth cinematic drone pan over the golden sand beaches and turquoise waters of Maui at sunset').
        tool_context: The ADK ToolContext used to save the artifact for the session and UI.
        destination_name: Short name or slug of the destination/item (e.g. 'maui', 'tokyo').
        duration_seconds: Length of the video in seconds (between 3 and 10, default: 5).
        aspect_ratio: Video aspect ratio ('16:9' or '9:16', default: '16:9').

    Returns:
        Dictionary containing the public Cloud Storage video URL, filename, and status.
    """
    try:
        import base64
        import google.auth
        import google.auth.transport.requests
        import requests

        # 1. Obtain Google Cloud credentials and refresh token
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        creds.refresh(google.auth.transport.requests.Request())

        # Clamp duration between 3s and 10s as required by gemini-omni-flash-preview
        duration_val = max(3, min(10, duration_seconds))
        duration_str = f"{duration_val}s"
        ar = aspect_ratio if aspect_ratio in ["16:9", "9:16"] else "16:9"

        url = "https://aiplatform.googleapis.com/v1beta1/projects/qwiklabs-gcp-04-4a6cf1dba233/locations/global/interactions"
        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
        }
        body = {
            "model": "gemini-omni-flash-preview",
            "input": [
                {
                    "type": "text",
                    "text": prompt,
                }
            ],
            "response_format": [
                {
                    "type": "video",
                    "aspect_ratio": ar,
                    "resolution": "720p",
                    "duration": duration_str,
                }
            ],
            "generation_config": {
                "video_config": {
                    "task": "text_to_video",
                }
            },
        }

        # Synchronous stateless interaction call
        resp = requests.post(url, headers=headers, json=body, timeout=180)
        if resp.status_code != 200:
            return {"error": f"Interactions API returned status {resp.status_code}: {resp.text}"}

        data = resp.json()
        video_bytes = None
        mime_type = "video/mp4"

        for step in data.get("steps", []):
            if step.get("type") == "model_output":
                for item in step.get("content", []):
                    if item.get("type") == "video" and item.get("data"):
                        video_bytes = base64.b64decode(item["data"])
                        if item.get("mime_type"):
                            mime_type = item["mime_type"]
                        break

        if not video_bytes:
            return {"error": "No video content returned by gemini-omni-flash-preview."}

        # 2. Determine filename
        clean_name = re.sub(r"[^a-zA-Z0-9_-]", "_", destination_name.lower())
        unique_id = uuid.uuid4().hex[:8]
        filename = f"{clean_name}_{unique_id}.mp4"

        # 3. Save as ADK artifact so it shows up in the Playground's Artifacts panel
        try:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)
        except Exception as artifact_err:
            print(f"Warning: could not save video artifact to tool_context: {artifact_err}")

        # 4. Upload video bytes to public Cloud Storage bucket without writing to local disk
        gcs = get_storage_client()
        bucket = gcs.bucket(PUBLIC_STORAGE_BUCKET)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{PUBLIC_STORAGE_BUCKET}/{filename}"

        return {
            "status": "success",
            "destination": destination_name,
            "filename": filename,
            "public_url": public_url,
            "mime_type": mime_type,
            "message": f"Short video successfully generated, saved as artifact '{filename}', and published to {public_url}",
        }
    except Exception as e:
        return {"error": f"Video generation and upload failed: {str(e)}"}


SANDBOX_RESOURCE_NAME = "projects/652319619327/locations/us-central1/reasoningEngines/3766918315545460736/sandboxEnvironments/4943414723841359872"


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description="""You are an expert AI Travel Planner.
You assist travelers in discovering world destinations, building tailored itineraries, and planning their dream trips.

Capabilities:
- Search and explore curated destinations using `search_destinations` (filter by city, country, or travel style like 'cultural', 'adventure', 'romantic', 'foodie').
- Retrieve full destination insights, attractions, and seasonal advice via `get_destination_details`.
- Save customized multi-day itineraries for users using `save_itinerary`.
- Retrieve previously saved user itineraries with `list_saved_itineraries`.
- Fetch real-time live weather and tailored packing tips with `get_live_weather_and_packing_tips`.
- Convert trip budgets and calculate expense estimates using real-time exchange rates via `convert_currency`.
- Geocode addresses and landmarks into exact coordinates with `geocode_address`.
- Discover nearby attractions, cafes, restaurants, and museums with `find_nearby_places`.
- Generate custom visual postcards or scenic illustrations for destinations with `generate_and_store_destination_image`, which saves artifacts and provides public image URLs.
- Generate short cinematic preview videos for travel destinations or highlights using `generate_and_store_destination_video` (powered by Google Omni gemini-omni-flash-preview), which saves artifacts and provides public video URLs.
- Safely execute Python code in the Agent Engine Sandbox environment to perform accurate numerical travel calculations, budget modeling, flight or travel route optimization, and dates math.
- Check current local time and timezones using `get_current_time`.
- Personalization & Safety: Remember, record, and actively account for all user allergies (food allergies, environmental, medical, etc.) and dietary restrictions across conversations. Never recommend dining, activities, or destinations that conflict with the traveler's stated allergies without clear safety warnings.""",
    workflow_description="Analyze the traveler's request, call tools to gather facts, and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=AgentEngineSandboxCodeExecutor(
        sandbox_resource_name=SANDBOX_RESOURCE_NAME,
    ),
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
    tools=[
        PreloadMemoryTool(),
        search_destinations,
        get_destination_details,
        save_itinerary,
        list_saved_itineraries,
        get_live_weather_and_packing_tips,
        convert_currency,
        geocode_address,
        find_nearby_places,
        generate_and_store_destination_image,
        generate_and_store_destination_video,
        get_current_time,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)

