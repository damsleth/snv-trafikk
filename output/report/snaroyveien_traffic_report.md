# Trafikkanalyse Snarøyveien

*Automatisk generert 16.03.2026 kl. 11:30*

## QA-status

Denne rapporten bruker periodedelte scenarioer (AM/PM), appendix-baserte OD-matriser og en systemforsinkelses-KPI som inkluderer både fullførte turer og blokkerte avganger.

Det betyr at tallene under ikke er direkte sammenlignbare med tidligere repo-utgaver som brukte kun morgenrute og kun tidstap fra fullførte turer.

## Hovedobservasjoner

### Morgenrush 07:45-08:45

- Base: 3.6 min gjennomsnittlig reisetid, 487.6 kjt-t systemforsinkelse, 462 maks ventende kjøretøy.
- V1: 5.3 min gjennomsnittlig reisetid, 594.6 kjt-t systemforsinkelse, 550 maks ventende kjøretøy.
- Endring V1 vs. base: 5.3 min (+1.7 min vs. base), 594.6 kjt-t (+107.0 kjt-t vs. base), 550 kjt (+88 kjt vs. base).

### Ettermiddagsrush 15:30-16:30

- Base: 3.7 min gjennomsnittlig reisetid, 402.2 kjt-t systemforsinkelse, 390 maks ventende kjøretøy.
- V1: 5.3 min gjennomsnittlig reisetid, 491.3 kjt-t systemforsinkelse, 437 maks ventende kjøretøy.
- Endring V1 vs. base: 5.3 min (+1.5 min vs. base), 491.3 kjt-t (+89.1 kjt-t vs. base), 437 kjt (+47 kjt vs. base).

## Metode

- Etterspørsel er hentet fra appendixmatrisene i PGF Trafikkanalyse Snarøyveien (Scenario 1A/4A, morgen og ettermiddag).
- V1/V2/V3 følger segmentert A/B/C-laneoppsett i stedet for en ensartet 2+2-forenkling.
- Rapporten bruker `system_delay_h = completed_time_loss_h + blocked_vehicle_h` for å unngå survivorship-bias når mange biler aldri kommer inn i modellen.
- Resultatene er fortsatt begrenset av nettverksforenklinger fra OSM-basen og manglende kalibrering mot observerte telledata.

## Visualiseringer

![AM reisetid](../visualizations/morning_avg_duration.png)

![AM systemforsinkelse](../visualizations/morning_system_delay.png)

![PM reisetid](../visualizations/afternoon_avg_duration.png)

![PM systemforsinkelse](../visualizations/afternoon_system_delay.png)

## Scenariotabell

| Scenario | Reisetid | Systemforsinkelse | Blokkerte avganger | Maks ventende |
|---|---|---|---|---|
| Base (Sc. 1A) PM | 4.1 min | 630.2 kjt-t | 144 | 667 |
| Base (Sc. 1A) AM | 9.2 min | 1557.9 kjt-t | 781 | 1471 |
| V1 (Sc. 1A) PM | 6.5 min | 861.6 kjt-t | 184 | 835 |
| V1 (Sc. 1A) AM | 9.1 min | 1608.2 kjt-t | 972 | 1446 |
| Base (dagens profil) PM | 3.7 min | 402.2 kjt-t | 77 | 390 |
| Base + konsert PM | 5.5 min | 3800.7 kjt-t | 5291 | 5480 |
| Base (dagens profil) AM | 3.6 min | 487.6 kjt-t | 201 | 462 |
| V1 PM | 5.3 min | 491.3 kjt-t | 100 | 437 |
| V1 + konsert PM | 7.1 min | 3900.1 kjt-t | 5422 | 5580 |
| V1 AM | 5.3 min | 594.6 kjt-t | 251 | 550 |
| V1 + miljøgate PM | 5.7 min | 527.5 kjt-t | 104 | 474 |
| V1 + miljøgate AM | 7.4 min | 1039.6 kjt-t | 462 | 990 |
| V2 PM | 5.8 min | 549.7 kjt-t | 169 | 531 |
| V2 AM | 5.9 min | 709.4 kjt-t | 360 | 700 |
| V3 PM | 5.3 min | 497.1 kjt-t | 103 | 444 |
| V3 AM | 5.0 min | 571.9 kjt-t | 255 | 508 |

## Utrykningstid (beredskap)

Tre ambulanser er lagt inn i hver simuleringsperiode (snv_syd → snv_nordost, dvs. Snarøya til nordre rundkjøring). Tabellen viser gjennomsnittlig reisetid for utrykningskjøretøy:

| Scenario | Utrykningstid (gj.snitt) | Maks utrykningstid | Tidstap utrykn. |
|---|---|---|---|
| Base (Sc. 1A) PM | 4.8 min | 4.9 min | 169 s |
| Base (Sc. 1A) AM | 41.0 min | 41.0 min | 2343 s |
| V1 (Sc. 1A) PM | 5.8 min | 6.9 min | 172 s |
| V1 (Sc. 1A) AM | 3.9 min | 3.9 min | 72 s |
| Base (dagens profil) PM | 3.7 min | 4.2 min | 103 s |
| Base + konsert PM | 6.2 min | 11.1 min | 252 s |
| Base (dagens profil) AM | 4.7 min | 5.5 min | 167 s |
| V1 PM | 4.8 min | 5.0 min | 125 s |
| V1 + konsert PM | 5.0 min | 5.4 min | 135 s |
| V1 AM | 4.2 min | 4.6 min | 87 s |
| V1 + miljøgate PM | 4.7 min | 4.9 min | 120 s |
| V1 + miljøgate AM | 7.2 min | 10.7 min | 271 s |
| V2 PM | 4.8 min | 4.9 min | 126 s |
| V2 AM | 4.0 min | 4.5 min | 75 s |
| V3 PM | 4.9 min | 5.0 min | 127 s |
| V3 AM | 5.3 min | 6.3 min | 157 s |

## Forsinkelse for Snarøya-beboere

Kun turer med avgang fra Snarøya (snv_syd-sonen). Viser forsinkelsen for beboere som skal ut fra halvøya.

| Scenario | Ant. turer | Gj.snitt reisetid | Gj.snitt tidstap |
|---|---|---|---|
| Base (Sc. 1A) PM | 670 | 4.0 min | 132 s |
| Base (Sc. 1A) AM | 316 | 27.9 min | 1562 s |
| V1 (Sc. 1A) PM | 670 | 7.6 min | 287 s |
| V1 (Sc. 1A) AM | 245 | 21.8 min | 1162 s |
| Base (dagens profil) PM | 538 | 3.5 min | 100 s |
| Base + konsert PM | 538 | 7.4 min | 331 s |
| Base (dagens profil) AM | 652 | 4.4 min | 153 s |
| V1 PM | 538 | 5.2 min | 165 s |
| V1 + konsert PM | 538 | 6.3 min | 229 s |
| V1 AM | 652 | 6.6 min | 247 s |
| V1 + miljøgate PM | 538 | 4.8 min | 131 s |
| V1 + miljøgate AM | 369 | 14.3 min | 704 s |
| V2 PM | 538 | 5.3 min | 169 s |
| V2 AM | 652 | 6.7 min | 254 s |
| V3 PM | 538 | 5.2 min | 161 s |
| V3 AM | 652 | 5.3 min | 168 s |

## Estimert kølengde

Beregnet fra antall blokkerte + ventende kjøretøy, konvertert med 120 kjt/km (stoppet trafikk) fordelt på 2 tilkomstfelt.

| Scenario | Blokkerte kjt | Maks ventende | Kølengde (km) |
|---|---|---|---|
| Base (Sc. 1A) PM | 144 | 667 | 3.4 km |
| Base (Sc. 1A) AM | 781 | 1471 | 9.4 km |
| V1 (Sc. 1A) PM | 184 | 835 | 4.2 km |
| V1 (Sc. 1A) AM | 972 | 1446 | 10.1 km |
| Base (dagens profil) PM | 77 | 390 | 1.9 km |
| Base + konsert PM | 5291 | 5480 | 44.9 km |
| Base (dagens profil) AM | 201 | 462 | 2.8 km |
| V1 PM | 100 | 437 | 2.3 km |
| V1 + konsert PM | 5422 | 5580 | 45.8 km |
| V1 AM | 251 | 550 | 3.3 km |
| V1 + miljøgate PM | 104 | 474 | 2.4 km |
| V1 + miljøgate AM | 462 | 990 | 6.1 km |
| V2 PM | 169 | 531 | 2.9 km |
| V2 AM | 360 | 700 | 4.4 km |
| V3 PM | 103 | 444 | 2.3 km |
| V3 AM | 255 | 508 | 3.2 km |

## Begrensninger

- Repoet mangler fortsatt observasjonsbasert kalibrering og automatiserte tester.
- Flytårnet/Bernt Balchens-krysset er fortsatt avhengig av OSM-nettets geometri og prioriteringsmodell; dette er en kjent modellbegrensning som må forbedres før rapportering utad.
- Scenarioet med signaloptimalisering er midlertidig tatt ut av standardkjøringen til kryssmodellen er eksplisitt implementert.
- Utrykningstidsberegningen forutsetter at andre kjøretøy viker (SUMO vClass=emergency). I praksis er dette avhengig av at det finnes plass å vike til — med 2+2 felt er det mindre rom for å slippe frem utrykningskjøretøy enn med 2+3.
- Kølengdeestimatet er en forenklet omregning og tar ikke hensyn til faktisk køgeometri eller E18-tilknytning.

