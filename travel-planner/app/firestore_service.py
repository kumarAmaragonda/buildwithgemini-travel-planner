"""Firestore client and functions for destinations and custom itineraries."""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-4a6cf1dba233"

_db = None


def get_firestore_client() -> firestore.Client:
    """Return a Firestore client instance with the project ID explicitly specified."""
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def search_destinations(
    city: str | None = None,
    country: str | None = None,
    travel_style: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Search the destination catalog in Firestore.

    Args:
        city: Optional city name or substring to search for.
        country: Optional country name.
        travel_style: Optional travel style tag (e.g., 'cultural', 'adventure', 'romantic', 'family', 'foodie').
        limit: Max number of destinations to return.

    Returns:
        List of matching destination dictionaries.
    """
    db = get_firestore_client()
    query = db.collection("destinations")

    if country:
        query = query.where("country", "==", country)

    docs = query.limit(20).stream()
    results = []

    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id

        if city and city.lower() not in data.get("city", "").lower() and city.lower() not in data.get("name", "").lower():
            continue

        if travel_style and travel_style.lower() not in [s.lower() for s in data.get("travel_styles", [])]:
            continue

        results.append(data)
        if len(results) >= limit:
            break

    return results


def get_destination_details(destination_id: str) -> dict:
    """Fetch complete details for a specific destination by its ID.

    Args:
        destination_id: The document ID of the destination.

    Returns:
        The destination data dictionary or an error message.
    """
    db = get_firestore_client()
    doc = db.collection("destinations").document(destination_id).get()
    if not doc.exists:
        return {"error": f"Destination with ID '{destination_id}' not found."}
    data = doc.to_dict()
    data["id"] = doc.id
    return data


def save_itinerary(
    title: str,
    destination_city: str,
    days: int,
    itinerary_details: list[dict],
    user_id: str = "default_user",
) -> dict:
    """Save a planned itinerary into Firestore.

    Args:
        title: Title of the itinerary (e.g., '3-Day Cultural Weekend in Kyoto').
        destination_city: City name for the itinerary.
        days: Duration of the trip in days.
        itinerary_details: List of daily plans, e.g. [{"day": 1, "activities": ["Visit Fushimi Inari", "Tea ceremony"], "meals": "Ramen in Gion"}].
        user_id: User identifier.

    Returns:
        Confirmation dictionary with the saved itinerary ID.
    """
    db = get_firestore_client()
    doc_ref = db.collection("itineraries").document()
    payload = {
        "title": title,
        "destination_city": destination_city,
        "days": days,
        "itinerary_details": itinerary_details,
        "user_id": user_id,
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    doc_ref.set(payload)
    return {
        "status": "success",
        "itinerary_id": doc_ref.id,
        "message": f"Itinerary '{title}' successfully saved for {destination_city} ({days} days).",
    }


def list_saved_itineraries(user_id: str = "default_user", limit: int = 5) -> list[dict]:
    """Retrieve saved itineraries for a user.

    Args:
        user_id: User identifier.
        limit: Max number of itineraries to return.

    Returns:
        List of saved itineraries.
    """
    db = get_firestore_client()
    docs = db.collection("itineraries").where("user_id", "==", user_id).limit(limit).stream()
    itineraries = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        if "created_at" in data and data["created_at"]:
            data["created_at"] = str(data["created_at"])
        itineraries.append(data)
    return itineraries
