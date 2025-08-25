import json
import urllib.request
from enum import Enum


def get_location_from_ip():
    """
    Get estimated latitude and longitude based on user's IP address.
    Returns tuple of (latitude, longitude) or None if unable to determine.
    """
    try:
        # Try multiple free IP geolocation services
        services = [
            "http://ip-api.com/json/?fields=status,lat,lon",
            "https://ipapi.co/json/",
            "https://geolocation-db.com/json/"
        ]

        for service_url in services:
            try:
                req = urllib.request.Request(service_url, headers={
                    'User-Agent': 'CityJSON Creator/1.0'
                })

                with urllib.request.urlopen(req, timeout=3) as response:
                    data = json.loads(response.read().decode('utf-8'))

                # Parse response based on service
                if 'ip-api.com' in service_url:
                    if data.get('status') == 'success':
                        return data.get('lat'), data.get('lon')

                elif 'ipapi.co' in service_url:
                    lat = data.get('latitude')
                    lon = data.get('longitude')
                    if lat and lon:
                        return lat, lon

                elif 'geolocation-db.com' in service_url:
                    lat = data.get('latitude')
                    lon = data.get('longitude')
                    if lat and lon and lat != "Not found":
                        return lat, lon

            except Exception as e:
                print(f"Failed to get location from {service_url}: {e}")
                continue

        # If all services fail, return None
        return None

    except Exception as e:
        print(f"Error getting IP location: {e}")
        return None


def get_location_with_fallback():
    """
    Get user location from IP with fallback to default location.
    Returns (latitude, longitude) tuple.
    """
    location = get_location_from_ip()

    if location and location[0] and location[1]:
        print(f"Detected location: {location[0]:.4f}, {location[1]:.4f}")
        return location
    else:
        # Fallback to default location (Camous II, Uni Trier, Germany)
        print("Could not detect location, using default")
        return (49.74795,6.67412)


class MapProvider(Enum):
    NONE = "None"
    OSM = "OpenStreetMap"
    SATELLITE = "Satellite"
    TERRAIN = "Terrain"
