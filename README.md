# Novatrix Azure - Uppgift 4

## Syfte

Formuläret från uppgift 1 får riktig lagring. Ett ärende sparas som en JSON-fil i Azure Blob Storage. En frivillig bilaga sparas i samma ärendemapp. Lösningen använder identiteten från uppgift 2 och det privata subnätet från uppgift 3.

## Lösningens delar

| Del | Uppgift |
| --- | --- |
| Nginx och webbformulär | Tar emot formuläret och skickar det till serverns API. |
| Python på webbservern | Kontrollerar formuläret och sparar ärende och bilaga. |
| `id-novatrix-app` | Hämtar en tillfällig åtkomsttoken från Azure utan lagringsnycklar. |
| `Novatrix Blob Writer` | Ger bara rätt att skriva blobbar i behållaren `arenden`. |
| Private Endpoint och privat DNS | Ansluter till Blob Storage genom det privata subnätet. |
| StorageV2, Standard LRS, Hot | Enkel och billig lagring för små labbärenden som används direkt. |

```text
Formulär -> Nginx -> Python API -> privat HTTPS -> Blob Storage
                       |
                 hanterad identitet

arenden/
  <ärendenummer>/
    arende.json
    bilaga.txt       (frivillig bilaga)
```

## Säker åtkomst

Appen får endast `Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write`, på just `arenden`. Den har inga rättigheter att läsa, lista eller radera blobbar. Inga kontonycklar eller SAS används. Publik nätverksåtkomst, anonyma blobbar och åtkomst med kontonycklar är avstängda. Lagringen kräver HTTPS och minst TLS 1.2.

Private Endpoint ligger i `snet-novatrix-private`. Privat DNS översätter lagringens namn till en privat adress. Subnätets nätverkspolicy är aktiverad så att reglerna från uppgift 3 gäller även för den privata anslutningen. Webbservern kan nå den på port 443.

Detta är en avgränsad labb. Webbformuläret använder ännu HTTP och saknar användarinloggning; använd bara påhittade uppgifter. I en riktig kundtjänst behövs även HTTPS till webben, inloggning, kontroll av bilagornas innehåll och en plan för säkerhetskopiering. Skyddet ovan gäller framför allt appens åtkomst till lagringen.

## Körinstruktioner

Förutsättningar: färdig miljö från uppgift 1-3, Azure CLI, Bash och Python 3. Administratören behöver rätt att skapa resurser, en anpassad roll och rolltilldelningar.

1. Kopiera `v37/config.example.sh` till `v37/config.local.sh` och fyll i prenumeration och ett unikt lagringsnamn med små bokstäver och siffror.
2. Logga in med `az login` och välj rätt prenumeration.
3. Skapa lagringen och tilldela appens skrivrätt:

```bash
bash v37/scripts/apply-storage.sh
```

4. Installera appen:

```bash
python3 v37/scripts/deploy-app.py \
  --resource-group rg-novatrix \
  --storage-account YOUR_STORAGE_ACCOUNT
```

Installationen startar VM:n tillfälligt och frigör den efteråt, även vid ett installationsfel. Starta den igen bara under formulärtestet. Rolländringar kan behöva några minuter innan de fungerar.

## Verifiering

`v37/scripts/verify-storage.py` körs på VM:n och kontrollerar privat DNS, lagrat innehåll samt nekad åtkomst för appens identitet. Återläsning görs med en separat tillfällig identitet som får `Storage Blob Data Reader` endast på `arenden`. Den tas bort efter kontrollen. Appen får aldrig läsrätt för att förenkla testet.

För test av skrivning utanför behållaren används en separat tom behållare, `kontroll`, utan rolltilldelning till appen. Testet ska ge 403. Kontrollbehållaren tas bort efteråt.

Genomförda kontroller:

| Kontroll | Resultat |
| --- | --- |
| Formulär med txt-bilaga | Sparbekräftelse och ärendenummer. |
| Återläsning med separat testidentitet | Ärendets innehåll och bilagans byte stämde. |
| Privat DNS | Lagringen gav en adress i `10.10.2.0/24`. |
| Appidentiteten läser ärende | Nekades, HTTP 403. |
| Appidentiteten raderar ärende | Nekades, HTTP 403. |
| Appidentiteten skriver i annan behållare | Nekades, HTTP 403. |
| Anonym läsning från internet | Nekades, HTTP 403. |
| Lagring som kod | Driftsättningen `novatrix-v37-storage` fick `Succeeded`. |

Bildbevisen finns i rapporten, som distribueras separat från detta repo.

## VG: kostnad, prestanda och kod

Hot passar små ärenden som läses direkt vid kontrollen. Cool och Archive kan ge lägre lagringspris för stora datamängder som sällan används, men har andra läskostnader och krav på lagringstid. Det behövs inte i den här labben. Standard LRS ger kopior inom en region och är billigare än redundans över flera regioner; det skyddar inte mot ett helt regionbortfall.

`v37/infra/storage.json` skapar lagringskonto, behållare, privat anslutning och DNS. `apply-storage.sh` kopplar identiteten, aktiverar nätverkspolicyn och tilldelar den anpassade rollen. På så sätt byggs miljön vidare som kod.

## Kostnad och avslut

Den privata anslutningen debiteras per timme även när VM:n är avstängd. Privat DNS, lagrade data, operationer och eventuellt disk och publik IP kan också kosta. Gratisgränser och budgetvarningar är inget hårt kostnadstak.

Efter labbtestet används:

```bash
bash v37/scripts/remove-private-connection.sh
```

Det frigör VM:n och tar bort den privata anslutningen och DNS, men bevarar lagringskontot och ärendena. **Formuläret kan då inte spara nya ärenden.** Kör `apply-storage.sh` och starta VM:n när anslutningen behövs igen. Lagringen öppnas inte mot internet som ersättning.

Detta avslut har genomförts efter verifieringen. Den tillfälliga läsidentiteten, dess roll och kontrollbehållaren är också borttagna. Appens identitet är den enda hanterade identitet som finns kvar på VM:n.

Rapporter, privata inställningar, lösenord och interna arbetsfiler ingår inte i GitHub-underlaget.
