# hashicorp-bitwarden-vault-scripts

Scripts for easing administration tasks of HashiCorp Vault via BitWarden.

## unseal-vault-replicas

Unseals HashiCorp Vault replicas using a secret in BitwWarden.
This is intended to help users who cannot or do not want to use auto-unseal (e.g. home users for whom a HSM is impractical to purchase) or users who wish to have a human in the loop for unsealing.

If multiple users hold key shares, they can each execute this script using their share until the unseal threshold is reached.

### Prereqs

* the BitWarden CLI API server should be running and the client should be running with a valid session key
* kubectl must be properly configured to allow access to the Kubernetes instance hosting your Vault server

### Usage

For basic information, please run `unseal-vault-replicas  --help`

To unseal your Vault replicas by using the secret `vault unseal share` using three shares saved as custom fields `key 1`, `key 2` and `key 3` use `unseal-vault-replicas  --secret-name "vault unseal share" --fields "key 1" "key 2" "key 3"`.

### Accessing Replicas using TLS certificates signed by Kubernetes root

If you are using replicas that use TLS encryption on the backend which use certificates signed by the Kubernetes root certificate authority, it is possible to automatically extract this from the kube config file by adding the flag `--use-kube-ca`.