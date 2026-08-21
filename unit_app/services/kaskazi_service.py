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

    def _handle_response(self, response):
        print("KASKAZI STATUS:",response.status_code)
        print("KASKAZI RESPONSE:", response.text)

        try:
            data = (response.json())

        except Exception:
            data = {"message": response.text}

        if not response.ok:
            raise Exception(
            data.get("error") or data.get("message") or f"Kaskazi returned HTTP {response.status_code}")

        return data

        
    def get_applications(self,booking_id):
        response = requests.get(f"{self.base_url}/integrations/unit/bookings/{booking_id}/applications/", headers=self.headers, timeout=30)

        return self._handle_response(response)

    def get_messages(self, booking_id):
        response = requests.get(f"{self.base_url}/integrations/unit/bookings/{booking_id}/messages/", headers=self.headers, timeout=30)

        return self._handle_response(response)


    def send_message(self, booking_id, text,):
        response = requests.post(f"{self.base_url}/integrations/unit/bookings/{booking_id}/messages/send/", headers=self.headers, json={"text": text},timeout=30,)

        return self._handle_response(response)


    def verify_worker(self, booking_id, qr_value):
        response = requests.post(f"{self.base_url}/integrations/unit/bookings/{booking_id}/verify-worker/",headers=self.headers,json={"qr_value":qr_value,},timeout=30,)

        return self._handle_response(response)

    def select_worker(self, booking_id, application_id,):
        response = requests.post((f"{self.base_url}" f"/integrations/unit/bookings/" f"{booking_id}/select-worker/"),headers=self.headers, json={"application_id":application_id,},timeout=30,)

        return self._handle_response(response)

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