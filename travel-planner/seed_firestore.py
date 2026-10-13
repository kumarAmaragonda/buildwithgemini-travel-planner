"""Seed Firestore with initial destinations for the Travel Planner agent."""

import sys
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-4a6cf1dba233"

DESTINATIONS = [
    {
        "id": "kyoto-japan",
        "name": "Kyoto Ancient Temples & Bamboo Groves",
        "city": "Kyoto",
        "country": "Japan",
        "description": "Historic capital renowned for classical Buddhist temples, gardens, imperial palaces, Shinto shrines, and traditional wooden houses.",
        "best_season": "Spring (Cherry Blossoms) or Autumn (Foliage)",
        "avg_daily_budget_usd": 140,
        "travel_styles": ["cultural", "foodie", "relaxed", "photography"],
        "top_attractions": [
            "Fushimi Inari-taisha Shinto shrine",
            "Arashiyama Bamboo Grove",
            "Kinkaku-ji (Golden Pavilion)",
            "Gion Historic Geisha District",
            "Nishiki Food Market",
        ],
        "image_prompt": "Watercolor illustration of Kyoto's Golden Pavilion reflecting on a serene pond surrounded by vibrant autumn maple trees.",
    },
    {
        "id": "paris-france",
        "name": "Paris Art, Architecture & Cafés",
        "city": "Paris",
        "country": "France",
        "description": "The City of Light famed for haute cuisine, world-class museums, iconic romantic landmarks, and picturesque cobblestone streets.",
        "best_season": "Spring (April–May) or Autumn (September–October)",
        "avg_daily_budget_usd": 180,
        "travel_styles": ["romantic", "cultural", "foodie", "city-break"],
        "top_attractions": [
            "Eiffel Tower & Champ de Mars",
            "Louvre Museum & Glass Pyramid",
            "Montmartre & Sacré-Cœur Basilica",
            "Musée d'Orsay",
            "Seine River Cruise",
        ],
        "image_prompt": "Impressionist oil painting of a cozy Parisian street café with the Eiffel Tower in the golden hour background.",
    },
    {
        "id": "banff-canada",
        "name": "Banff National Park & Rocky Mountains",
        "city": "Banff",
        "country": "Canada",
        "description": "Majestic turquoise glacial lakes, soaring Canadian Rockies peaks, pristine alpine hiking trails, and abundant wildlife.",
        "best_season": "Summer (June–August) for hiking, Winter for skiing",
        "avg_daily_budget_usd": 160,
        "travel_styles": ["adventure", "nature", "photography", "outdoors"],
        "top_attractions": [
            "Lake Louise turquoise glacial waters",
            "Moraine Lake & Valley of the Ten Peaks",
            "Banff Gondola & Sulphur Mountain",
            "Icefields Parkway scenic drive",
            "Johnston Canyon waterfall hike",
        ],
        "image_prompt": "Scenic landscape photography of turquoise Lake Louise reflecting snow-dusted Canadian Rocky Mountains under crisp blue skies.",
    },
    {
        "id": "florence-italy",
        "name": "Florence Renaissance Cradle & Tuscan Delights",
        "city": "Florence",
        "country": "Italy",
        "description": "Birthplace of the Renaissance, home to masterworks by Michelangelo and Botticelli, terracotta-tiled Duomo, and rich Tuscan gastronomy.",
        "best_season": "Spring (May) or Autumn (September–October)",
        "avg_daily_budget_usd": 150,
        "travel_styles": ["cultural", "foodie", "art", "romantic"],
        "top_attractions": [
            "Duomo (Cathedral of Santa Maria del Fiore)",
            "Uffizi Gallery",
            "Ponte Vecchio medieval bridge",
            "Piazzale Michelangelo sunset panoramic viewpoint",
            "Galleria dell'Accademia (David statue)",
        ],
        "image_prompt": "Warm golden-hour watercolor of Florence's Duomo and the Arno River with Ponte Vecchio reflecting glowing sunset lights.",
    },
    {
        "id": "cape-town-south-africa",
        "name": "Cape Town Oceans, Peaks & Vineyards",
        "city": "Cape Town",
        "country": "South Africa",
        "description": "Dramatic coastal city framed by flat-topped Table Mountain, penguin beaches, scenic coastal drives, and world-class Cape Winelands.",
        "best_season": "Southern Hemisphere Summer (November–March)",
        "avg_daily_budget_usd": 110,
        "travel_styles": ["adventure", "nature", "foodie", "photography"],
        "top_attractions": [
            "Table Mountain Cableway & Summit",
            "Boulders Beach African Penguin Colony",
            "Cape of Good Hope Nature Reserve",
            "Kirstenbosch National Botanical Garden",
            "V&A Waterfront",
        ],
        "image_prompt": "Vibrant landscape illustration of Cape Town with Table Mountain rising majestically above the turquoise Atlantic coastline.",
    },
]


def seed_destinations():
    print(f"Connecting to Firestore for project: '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    collection = db.collection("destinations")

    for dest in DESTINATIONS:
        doc_id = dest["id"]
        data = {k: v for k, v in dest.items() if k != "id"}
        collection.document(doc_id).set(data)
        print(f"✓ Seeded destination: {doc_id} -> {dest['name']}")

    print("\nFirestore seeding complete! 5 destinations loaded.")


if __name__ == "__main__":
    seed_destinations()
