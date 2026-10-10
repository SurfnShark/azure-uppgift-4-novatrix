#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${CONFIG_FILE:-$HERE/../config.local.sh}"
: "${SUBSCRIPTION_ID:?}" "${RESOURCE_GROUP:?}" "${STORAGE_ACCOUNT:?}" "${VM_NAME:=vm-novatrix-web}"
az account set --subscription "$SUBSCRIPTION_ID"
az network vnet subnet update -g "$RESOURCE_GROUP" --vnet-name vnet-novatrix --name snet-novatrix-private --private-endpoint-network-policies Enabled --output none
az deployment group create -g "$RESOURCE_GROUP" --name novatrix-v37-storage --template-file "$HERE/../infra/storage.json" --parameters storageAccountName="$STORAGE_ACCOUNT" --output none
IDENTITY_ID="$(az identity show -g "$RESOURCE_GROUP" -n id-novatrix-app --query id -o tsv)"
PRINCIPAL_ID="$(az identity show -g "$RESOURCE_GROUP" -n id-novatrix-app --query principalId -o tsv)"
az vm identity assign -g "$RESOURCE_GROUP" -n "$VM_NAME" --identities "$IDENTITY_ID" --output none
SCOPE="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT/blobServices/default/containers/arenden"
ROLE_JSON="$(python3 - "$HERE/../infra/blob-writer-role.json" "$SUBSCRIPTION_ID" "$RESOURCE_GROUP" <<'PY'
import json,sys
role=json.load(open(sys.argv[1],encoding='utf-8'))
role['AssignableScopes']=[f'/subscriptions/{sys.argv[2]}/resourceGroups/{sys.argv[3]}']
print(json.dumps(role))
PY
)"
ROLE_ID="$(az role definition list --name 'Novatrix Blob Writer' --query '[0].id' -o tsv)"
if [[ -z "$ROLE_ID" ]]; then
  ROLE_ID="$(az role definition create --role-definition "$ROLE_JSON" --query id -o tsv)"
fi
EXISTING="$(az role assignment list --assignee "$PRINCIPAL_ID" --scope "$SCOPE" --query "[?roleDefinitionId=='$ROLE_ID'].id | [0]" -o tsv)"
if [[ -z "$EXISTING" ]]; then
  az role assignment create --assignee-object-id "$PRINCIPAL_ID" --assignee-principal-type ServicePrincipal --role "$ROLE_ID" --scope "$SCOPE" --output none
fi
echo 'Privat lagring, appidentitet och skrivrätt på arenden är klara.'
