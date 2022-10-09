"""
Copyright 2022 Eugene Davis

This file is part of hashicorp-bitwarden-vault-scripts.

hashicorp-bitwarden-vault-scripts is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
hashicorp-bitwarden-vault-scripts is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with hashicorp-bitwarden-vault-scripts. If not, see <https://www.gnu.org/licenses/>. 
"""

"""
Simple library for interfacing with the BitWarden CLI's API server.
Only provides the features required for scripts in this library, not currently striving to be a standalone interface.
"""

import logging
import requests


class bitwarden:
    def __init__(self, url_base):
        self.url_base = url_base
        self.check_server_status()

    def check_server_status(self):
        try:
            response = requests.get(f"{self.url_base}/status")
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(
                "Bitwarden client API server not running, start and rerun this command"
            )

        status = response.json()

        if not status.get("success"):
            raise RuntimeError(
                "Bitwarden client API server not running, start and rerun this command"
            )

        if status.get("data").get("status") == "locked":
            raise RuntimeError(
                "Bitwarden client not unlocked, please unlock and set BW_SESSION"
            )

    def get_secret(self, name):
        logging.info("Searching for %s in BitWarden", name)
        items = requests.get(
            f"{self.url_base}/list/object/items",
            params={"search": name},
        )
        logging.debug(items.json())
        for secret in items.json()["data"]["data"]:
            if secret["name"] == name:
                return secret
