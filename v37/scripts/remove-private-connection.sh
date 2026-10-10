#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${CONFIG_FILE:-$HERE/../config.local.sh}"
az account set --subscription "$SUBSCRIPTION_ID"
az vm deallocate -g "$RESOURCE_GROUP" -n "${VM_NAME:-vm-novatrix-web}" --output none
az network private-endpoint delete -g "$RESOURCE_GROUP" -n pe-novatrix-blob
az network private-dns link vnet delete -g "$RESOURCE_GROUP" -z privatelink.blob.core.windows.net -n novatrix-link --yes
az network private-dns zone delete -g "$RESOURCE_GROUP" -n privatelink.blob.core.windows.net --yes
echo 'VM frigjord. Privat anslutning och DNS borttagna. Ärenden och lagringskonto finns kvar.'
