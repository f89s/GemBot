import datetime
import hashlib
import json
import os
import time
from unittest import result
import configparser

import jwt
import requests
from requests import options


class SoybooruAuth:
    AUTH_URL = "https://soybooru.com/api/Auth/"
    POW_URL = "https://soybooru.com/api/pow/"

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('bot-settings.cfg')

        self.username = "Dailyjak"
        self.password = config.get('BotSettings', 'BOORU_PASSWORD', fallback='')
        self.ua_agent = config.get('BotSettings', 'UA_AGENT')

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.ua_agent
        })

        self.token = None
        self.refresh_token = None
        self.expires_at = None

        self.load_tokens()

    def load_tokens(self):
        if not os.path.exists("tokens.json"):
            return

        with open("tokens.json", "r") as f:
            data = json.load(f)

        self.token = data.get("token")
        self.refresh_token = data.get("refreshToken")
        self.expires_at = data.get("expiresAt")

    def save_tokens(self):
        with open("tokens.json", "w") as f:
            json.dump({
                "token": self.token,
                "refreshToken": self.refresh_token,
                "expiresAt": self.expires_at
            }, f)

    def token_expired(self):
        if not self.token or not self.expires_at:
            return True

        try:
            expires = datetime.datetime.fromisoformat(
                self.expires_at.replace("Z", "+00:00")
            )

            return datetime.datetime.now(datetime.timezone.utc) >= expires

        except Exception as e:
            print(f"[!] Could not parse expiresAt: {e}")
            return True

    def has_leading_zero_bits(self, digest: bytes, difficulty: int):

        full_bytes = difficulty // 8
        remaining_bytes = difficulty % 8

        for i in range(full_bytes):
            if digest[i] != 0:
                return False

        if remaining_bytes:
            mask = (0xff << (8 - remaining_bytes)) & 0xFF
            return (digest[full_bytes] & mask) == 0

        return True

    def solve_pow(self, challenge: str, diffictulty: int) -> str:
        nonce = 0

        while True:
            candidate = challenge + format(nonce, "x")
            digest = hashlib.sha256(candidate.encode("utf-8")).digest()

            if self.has_leading_zero_bits(digest, diffictulty):
                return format(nonce, "x")

            nonce += 1

    def complete_pow(self):
        print("[*] Getting SoyBooru PoW challenge")

        r = self.session.get(self.POW_URL + "challenge")
        r.raise_for_status()
        data = r.json()

        challenge_id = data["id"]
        challenge = data["challenge"]
        difficulty = int(data["difficulty"])

        print(f"[*] Solving SoyBooru PoW difficulty {difficulty}")

        nonce = self.solve_pow(challenge, difficulty)
        print(f"[*] Verifying SoyBooru PoW nonce {nonce}")

        r = self.session.post(self.POW_URL + "verify", json={
                "challengeId": challenge_id,
                "challenge": challenge,
                "nonce": nonce
            })
        r.raise_for_status()
        result = r.json()

        if not result.get("success"):
            raise RuntimeError(f"PoW verification failed: {result}")

        print("[*] SoyBooru PoW verified")

    def login(self):
        print("[*] Logging into SoyBooru")
        self.complete_pow()

        r = self.session.post(self.AUTH_URL + "login", headers={"User-Agent": self.ua_agent}, json={
            "username": self.username,
            "password": self.password
        })

        r.raise_for_status()
        data = r.json()

        self.refresh_token = data["refreshToken"]

        self.refresh()

    def refresh(self):
        print("[*] Refreshing SoyBooru authorization token")

        r = self.session.post(
            self.AUTH_URL + "refresh",
            json={
                "refreshToken": self.refresh_token
            }
        )

        r.raise_for_status()
        data = r.json()

        self.token = data["token"]
        self.refresh_token = data["refreshToken"]
        self.expires_at = data["expiresAt"]

        self.save_tokens()

    def ensure_token(self):
        if not self.token:
            self.login()
            return

        if not self.token_expired():
            return

        try:
            self.refresh()
        except Exception:
            print("[!] Refresh failed, doing full login")
            self.login()

    def request(self, method, url, **kwargs):
        last_error = None

        for attempt in range(2):
            try:
                self.ensure_token()

                headers = {
                    "User-Agent": self.ua_agent,
                    "Authorization": f"Bearer {self.token}"
                }

                r = self.session.request(
                    method,
                    url,
                    headers=headers,
                    **kwargs
                )

                if r.status_code == 449:
                    self.complete_pow()

                    r = self.session.request(
                        method,
                        url,
                        headers=headers,
                        **kwargs
                    )

                r.raise_for_status()
                return r

            except requests.RequestException as exc:
                last_error = exc

                if attempt == 1:
                    raise

                status = (
                    exc.response.status_code
                    if exc.response is not None
                    else "no response"
                )

                print(
                    f"[!] SoyBooru API request failed, retrying... "
                    f"({status}): {exc}"
                )

                time.sleep(2)

        raise last_error

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, json=None, **kwargs):
        return self.request("POST", url, json=json, **kwargs)

    def put(self, url, json=None, **kwargs):
        return self.request("PUT", url, json=json, **kwargs)