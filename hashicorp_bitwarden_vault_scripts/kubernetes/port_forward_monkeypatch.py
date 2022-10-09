"""
Copyright 2022 Eugene Davis

This file is part of hashicorp-bitwarden-vault-scripts.

hashicorp-bitwarden-vault-scripts is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
hashicorp-bitwarden-vault-scripts is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with hashicorp-bitwarden-vault-scripts. If not, see <https://www.gnu.org/licenses/>. 
"""

"""
Allows using port forwarding from requests by monkeypatching urllib3
Adapted from https://github.com/kubernetes-client/python/blob/master/examples/pod_portforward.py
"""

import urllib3

from kubernetes.stream import portforward


class monkey_patch_requests:
    def __init__(self, api_instance):
        self.original_creation_connection = urllib3.util.connection.create_connection
        self.api_instance = api_instance

    def kubernetes_create_connection(self, address, *args, **kwargs):
        dns_name = address[0]
        if isinstance(dns_name, bytes):
            dns_name = dns_name.decode()
        dns_name = dns_name.split(".")
        if dns_name[-1] != "local":
            return self.original_creation_connection(address, *args, **kwargs)
        if len(dns_name) not in (4, 5):
            raise RuntimeError("Unexpected kubernetes DNS name.")
        namespace = dns_name[-3]
        name = dns_name[0]
        port = address[1]
        if len(dns_name) == 4:
            if dns_name[1] in ("svc", "service"):
                service = self.api_instance.read_namespaced_service(name, namespace)
                for service_port in service.spec.ports:
                    if service_port.port == port:
                        port = service_port.target_port
                        break
                else:
                    raise RuntimeError("Unable to find service port: %s" % port)
                label_selector = []
                for key, value in service.spec.selector.items():
                    label_selector.append("%s=%s" % (key, value))
                pods = self.api_instance.list_namespaced_pod(
                    namespace, label_selector=",".join(label_selector)
                )
                if not pods.items:
                    raise RuntimeError("Unable to find service pods.")
                name = pods.items[0].metadata.name
                if isinstance(port, str):
                    for container in pods.items[0].spec.containers:
                        for container_port in container.ports:
                            if container_port.name == port:
                                port = container_port.container_port
                                break
                        else:
                            continue
                        break
                    else:
                        raise RuntimeError(
                            "Unable to find service port name: %s" % port
                        )
            elif dns_name[1] != "pod":
                raise RuntimeError("Unsupported resource type: %s" % dns_name[1])
        pf = portforward(
            self.api_instance.connect_get_namespaced_pod_portforward,
            name,
            namespace,
            ports=str(port),
        )
        return pf.socket(port)

    def __enter__(self):
        urllib3.util.connection.create_connection = self.kubernetes_create_connection

    def __exit__(self, *args):
        urllib3.util.connection.create_connection = self.original_creation_connection
