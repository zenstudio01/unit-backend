import requests

from django.conf import settings
import os


class KaskaziService:
    def __init__(self):
        self.base_url = (
            os.environ.get("KASKAZI_API_URL")
            .rstrip("/")
        )

        self.headers = {
            "X-Client-ID": os.environ.get("KASKAZI_CLIENT_ID"),
            "X-API-Key": os.environ.get("KASKAZI_API_KEY"),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def get_services(
        self,
        category=None,
    ):
        params = {}

        if category:
            params["category"] = (
                category
            )

        response = requests.get(
            f"{self.base_url}/integrations/unit/services/",
            headers=self.headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    def create_booking(
        self,
        payload,
    ):
        response = requests.post(
            f"{self.base_url}/integrations/unit/bookings/",
            headers=self.headers,
            json=payload,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    def get_booking(
        self,
        booking_id,
    ):
        response = requests.get(
            f"{self.base_url}/integrations/unit/bookings/{booking_id}/",
            headers=self.headers,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    def cancel_booking(
        self,
        booking_id,
    ):
        response = requests.post(
            f"{self.base_url}/integrations/unit/bookings/{booking_id}/cancel/",
            headers=self.headers,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()