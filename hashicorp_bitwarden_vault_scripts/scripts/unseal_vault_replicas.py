"""
Copyright 2022 Eugene Davis

This file is part of hashicorp-bitwarden-vault-scripts.

hashicorp-bitwarden-vault-scripts is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
hashicorp-bitwarden-vault-scripts is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with hashicorp-bitwarden-vault-scripts. If not, see <https://www.gnu.org/licenses/>. 
"""

"""
Unseals replicas of a HashiCorp Vault instance running in Kubernetes by sourcing the key from a BitWarden secret.
"""

import warnings
import logging
import argparse
from typing import List

import hvac
import requests

from hashicorp_bitwarden_vault_scripts.kubernetes.port_forward_monkeypatch import (
    monkey_patch_requests,
)
from hashicorp_bitwarden_vault_scripts.bitwarden.bitwarden import bitwarden

from kubernetes import config
from kubernetes.client import Configuration
from kubernetes.client.api import core_v1_api


def get_unseal_keys(
    secret_name: str,
    url: str,
    key_fields: List[str],
):
    bw = bitwarden(url)
    unseal_key = bw.get_secret(secret_name)

    unseal_keys = []
    for field in unseal_key["fields"]:
        if field["name"] in key_fields:
            unseal_keys.append(field["value"])

    return unseal_keys


def unseal_vault(
    unseal_keys: List[str],
    replica_count: int,
    namespace: str,
    pod_prefix: str,
    vault_url_template: str,
    use_kubectl_cert: bool,
):
    config.load_kube_config()
    c = Configuration.get_default_copy()
    c.assert_hostname = False
    Configuration.set_default(c)
    api_instance = core_v1_api.CoreV1Api()

    with monkey_patch_requests(api_instance):
        for replica in range(0, replica_count):
            name = f"{pod_prefix}{replica}"

            logging.info("Unsealing %s", name)

            if use_kubectl_cert:
                logging.debug("Using Kube Root CA")
                ca_cert = c.ssl_ca_cert
            else:
                logging.debug("Using default CA bundle")
                ca_cert = None
            logging.debug(
                "Connecting to %s",
                vault_url_template.format(name=name, namespace=namespace),
            )
            client = hvac.Client(
                url=vault_url_template.format(name=name, namespace=namespace),
                verify=ca_cert,
            )

            if use_kubectl_cert:
                rs = requests.Session()
                client.session = rs
                rs.verify = ca_cert
            if not client.sys.is_sealed():
                client.sys.submit_unseal_keys(keys=unseal_keys)
            else:
                logging.info("%s is already unsealed", name)
                continue
            if client.sys.is_sealed():
                warnings.warn(f"{name} is not unsealed")


def main(
    bw_url: str,
    secret_name: str,
    key_fields: List[str],
    namespace: str,
    replica_count: int,
    pod_prefix: str,
    vault_url_template: str,
    use_kubectl_cert: bool,
    log_level: str,
):
    logging.basicConfig(level=log_level)
    unseal_keys = get_unseal_keys(secret_name, bw_url, key_fields)
    unseal_vault(
        unseal_keys,
        replica_count,
        namespace,
        pod_prefix,
        vault_url_template,
        use_kubectl_cert,
    )


def cli_main():
    parser = argparse.ArgumentParser(
        description="Fetch unseal key from BitWarden CLI server and apply to HashiCorp Vault"
    )

    parser.add_argument(
        "-l",
        "--logging",
        type=str,
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set the log level.",
    )

    bw_group = parser.add_argument_group(
        "BitWarden", description="Arguments for BitWarden"
    )
    bw_group.add_argument(
        "--bw-url",
        type=str,
        default="http://localhost:8087",
        help="Set URL to BitWarden CLI API",
    )
    bw_group.add_argument(
        "-s", "--secret-name", type=str, help="Vault unseal key BitWarden secret name"
    )
    bw_group.add_argument(
        "-f",
        "--fields",
        type=str,
        nargs="+",
        help="BitWarden secret fields with unseal keys",
    )

    vault_group = parser.add_argument_group(
        "HashiCorp Vault", description="Arguments for HashiCorp Vault"
    )
    vault_group.add_argument(
        "-n",
        "--namespace",
        type=str,
        default="vault",
        help="Kubernetes namespace for HashiCorp Vault",
    )
    vault_group.add_argument(
        "-r", "--replicas", type=int, default=3, help="Number of Vault replicas running"
    )
    vault_group.add_argument(
        "-p",
        "--pod-prefix",
        type=str,
        default="vault-",
        help="Pod prefix for Vault replicas",
    )
    vault_group.add_argument(
        "-t",
        "--url-template",
        type=str,
        default="https://{name}.vault-internal.{namespace}.cluster.local:8200",
        help="Template for pod URLs, must use the namespace.cluster.local format and should provide pod name and template parameters",
    )

    vault_group.add_argument(
        "-k",
        "--use-kube-ca",
        action="store_true",
        help="Use root CA for Kubernetes when connecting to Vault pods",
    )

    args = parser.parse_args()
    main(
        args.bw_url,
        args.secret_name,
        args.fields,
        args.namespace,
        args.replicas,
        args.pod_prefix,
        args.url_template,
        args.use_kube_ca,
        args.logging,
    )


if __name__ == "__main__":
    cli_main()
