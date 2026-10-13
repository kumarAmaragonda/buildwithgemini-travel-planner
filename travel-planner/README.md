# ✈️ Travel Planner Agent

An agentic AI Travel Planner built on Google Cloud's Agent Development Kit (ADK) and Gemini. The agent assists travelers with personalized itinerary planning, real-time weather and packing advice, live currency conversions, geographical landmark searches, destination visual concepts, short video generation, and persistent memory across conversations.

<div align="center">
  <img src="assets/demo.gif" alt="Travel Planner Agent Demo" width="720px" />
</div>

---

## 🌟 What This Agent Does

The agent is powered by **Gemini 2.5 Flash** (`gemini-2.5-flash`), with code execution enabled via **Agent Engine Code Sandbox**, long-term memory via **Vertex AI Memory Bank**, and custom visual rendering with **A2UI** v0.8.

### Real Wired Tools & Capabilities

- 🧠 **Cross-Session Memory Bank (Vertex AI)**:
  - Automatically loads and preserves traveler preferences across sessions using `PreloadMemoryTool` and `add_session_to_memory`.
  - Configured with managed topics plus a specialized topic for remembering user allergies and dietary restrictions (`user_allergies_and_dietary_restrictions`).
- 🗄️ **Curated Travel Database (Google Cloud Firestore)**:
  - `search_destinations`: Filters curated world destinations by city, country, and travel vibe (cultural, adventure, romantic, foodie).
  - `get_destination_details`: Retrieves deep insights, key attractions, best seasons, and local tips from Firestore.
  - `save_itinerary`: Persists multi-day user itineraries directly to Firestore.
  - `list_saved_itineraries`: Retrieves saved itineraries for the traveler.
- 🎨 **Visual Concept Generation (Nano Banana 2 Lite / `gemini-3.1-flash-lite-image`)**:
  - `generate_and_store_destination_image`: Generates destination concept art and postcards in the `global` region, saves them as ADK session artifacts, and uploads the bytes directly to a public Cloud Storage bucket.
- 🎬 **Video Generation (Google Omni / `gemini-omni-flash-preview`)**:
  - `generate_and_store_destination_video`: Generates short cinematic video clips of destinations using Vertex AI Interactions API, saves them as ADK session artifacts, and uploads them to Cloud Storage.
- 🗺️ **Google Maps & Places APIs**:
  - `geocode_address`: Converts addresses or landmarks into exact latitude and longitude coordinates via the Google Maps Geocoding API.
  - `find_nearby_places`: Finds nearby attractions, restaurants, museums, and cafes using the Google Places API (New).
- ⛅ **Real-Time Weather & Packing Tips**:
  - `get_live_weather_and_packing_tips`: Queries current weather data via Open-Meteo and provides tailored clothing packing tips.
- 💱 **Live Currency Converter**:
  - `convert_currency`: Converts travel budgets between international currencies using live exchange rates.
- 🧪 **Code Sandbox Execution (Agent Platform)**:
  - Runs safe numerical calculations, date math, and budget modeling in an isolated `AgentEngineSandboxCodeExecutor`.
- 🪟 **Agent-to-User Interface (A2UI)**:
  - Renders structured response cards, columns, rows, text hierarchy, and inline images using A2UI v0.8 Basic Catalog.

---

## 🏗️ Architecture

```
Browser (Chat UI)
       │
       ▼
FastAPI Proxy (A2A Protocol Client)
       │
       ▼
Agent Runtime / Agent Platform (ADK Agent)
 ├── LLM: Gemini 2.5 Flash
 ├── Memory: Vertex AI Memory Bank
 ├── Sandbox: Agent Engine Sandbox Code Executor
 ├── Data: Cloud Firestore
 ├── Storage: Google Cloud Storage
 ├── Maps: Google Maps Geocoding & Places (New) APIs
 ├── Media Gen: gemini-3.1-flash-lite-image & gemini-omni-flash-preview
 └── UI: A2UI v0.8 Schema
```

---

## 🚀 Setup & Local Execution

### 1. Prerequisites
- Python 3.12+
- `uv` package manager
- `gcloud` CLI authenticated with Application Default Credentials:
  ```bash
  gcloud auth login
  gcloud auth application-default login
  ```

### 2. Configure Environment
Create a `.env` file in the project directory:
```bash
GOOGLE_MAPS_API_KEY="your-key-here"
```

### 3. Run Agent Development Playground
To start the ADK playground locally with the Vertex AI Memory Bank wired in:
```bash
uv run adk web . --port 8080 --reload_agents --memory_service_uri=agentengine://<AGENT_ENGINE_ID>
```

### 4. Run the Web Frontend Locally
The repository includes a minimal FastAPI proxy and plain chat UI in `frontend/`:
```bash
cd frontend
export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_ID>/locations/<LOCATION>/reasoningEngines/<REASONING_ENGINE_ID>"
export AGENT_DIRECTORY="app"
export PORT="8080"
python main.py
```
Open a browser to port 8080 to test the agent.

---

## 📦 Project Structure

```
travel-planner/
├── app/
│   ├── agent.py                 # Core ADK agent, tools, and A2UI prompt
│   ├── firestore_service.py     # Firestore destination & itinerary storage
│   ├── fast_api_app.py          # Backend server wiring Runner & Memory Service
│   ├── a2ui_utils.py            # A2UI callback handler
│   └── a2ui/                    # A2UI schema manager & 0.8 catalog definitions
├── frontend/
│   ├── main.py                  # FastAPI A2A proxy server
│   ├── requirements.txt         # Frontend dependencies
│   ├── Dockerfile               # Container spec for Cloud Run deployment
│   └── static/
│       └── index.html           # Plain chat UI with native A2UI card renderer
├── assets/
│   └── demo.gif                 # Looping demo recording
├── agents-cli-manifest.yaml     # Agent deployment metadata
├── pyproject.toml               # Project dependencies
└── README.md
```
