# Trafikkanalyse Snarøyveien

*Automatisk generert 17.03.2026 kl. 11:14*

## QA-status

Denne rapporten bruker periodedelte scenarioer (AM/PM), appendix-baserte OD-matriser og en systemforsinkelses-KPI som inkluderer både fullførte turer og blokkerte avganger.

Det betyr at tallene under ikke er direkte sammenlignbare med tidligere repo-utgaver som brukte kun morgenrute og kun tidstap fra fullførte turer.

## Hovedobservasjoner

### Morgenrush 07:45-08:45

- Base: 13.2 min gjennomsnittlig reisetid, 580.3 kjt-t systemforsinkelse, 212 maks ventende kjøretøy.
- V1: 15.3 min gjennomsnittlig reisetid, 612.2 kjt-t systemforsinkelse, 126 maks ventende kjøretøy.
- Endring V1 vs. base: 15.3 min (+2.1 min vs. base), 612.2 kjt-t (+31.9 kjt-t vs. base), 126 kjt (-86 kjt vs. base).

### Ettermiddagsrush 15:30-16:30

- Base: 9.1 min gjennomsnittlig reisetid, 557.7 kjt-t systemforsinkelse, 362 maks ventende kjøretøy.
- V1: 11.6 min gjennomsnittlig reisetid, 664.9 kjt-t systemforsinkelse, 332 maks ventende kjøretøy.
- Endring V1 vs. base: 11.6 min (+2.5 min vs. base), 664.9 kjt-t (+107.2 kjt-t vs. base), 332 kjt (-30 kjt vs. base).

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
| Base (Sc. 1A) PM | 12.6 min | 1003.9 kjt-t | 288 | 580 |
| Base (Sc. 1A) AM | 15.7 min | 1137.8 kjt-t | 241 | 911 |
| V1 (Sc. 1A) PM | 13.9 min | 1024.2 kjt-t | 233 | 588 |
| V1 (Sc. 1A) AM | 14.5 min | 850.9 kjt-t | 64 | 563 |
| Base (dagens profil) PM | 9.1 min | 557.7 kjt-t | 0 | 362 |
| Base + konsert PM | 8.8 min | 3852.7 kjt-t | 5217 | 5467 |
| Base (dagens profil) AM | 13.2 min | 580.3 kjt-t | 0 | 212 |
| V1 PM | 11.6 min | 664.9 kjt-t | 0 | 332 |
| V1 + konsert PM | 11.8 min | 3996.3 kjt-t | 5357 | 5557 |
| V1 AM | 15.3 min | 612.2 kjt-t | 0 | 126 |
| V1 + miljøgate PM | 14.2 min | 643.1 kjt-t | 154 | 288 |
| V1 + miljøgate AM | 16.7 min | 633.2 kjt-t | 0 | 359 |
| V2 PM | 10.2 min | 501.4 kjt-t | 102 | 389 |
| V2 AM | 10.7 min | 559.1 kjt-t | 251 | 454 |
| V3 PM | 11.3 min | 650.9 kjt-t | 0 | 319 |
| V3 AM | 15.3 min | 617.6 kjt-t | 0 | 77 |

## Utrykningstid (beredskap)

Tre ambulanser er lagt inn i hver simuleringsperiode (snv_syd → snv_nordost, dvs. Snarøya til nordre rundkjøring). Tabellen viser gjennomsnittlig reisetid for utrykningskjøretøy:

| Scenario | Utrykningstid (gj.snitt) | Maks utrykningstid | Tidstap utrykn. |
|---|---|---|---|
| Base (Sc. 1A) PM | 37.0 min | 55.7 min | 1912 s |
| Base (Sc. 1A) AM | 16.2 min | 19.8 min | 670 s |
| V1 (Sc. 1A) PM | 16.8 min | 18.6 min | 685 s |
| V1 (Sc. 1A) AM | 17.4 min | 31.8 min | 707 s |
| Base (dagens profil) PM | 11.7 min | 13.7 min | 390 s |
| Base + konsert PM | 31.4 min | 53.1 min | 1571 s |
| Base (dagens profil) AM | 10.4 min | 12.2 min | 330 s |
| V1 PM | 11.8 min | 15.2 min | 384 s |
| V1 + konsert PM | 19.4 min | 27.5 min | 840 s |
| V1 AM | 11.4 min | 17.1 min | 348 s |
| V1 + miljøgate PM | 33.5 min | 33.5 min | 1579 s |
| V1 + miljøgate AM | 11.5 min | 12.2 min | 258 s |
| V2 PM | 11.4 min | 13.7 min | 357 s |
| V2 AM | 8.4 min | 9.5 min | 180 s |
| V3 PM | 29.9 min | 46.9 min | 1456 s |
| V3 AM | 9.1 min | 9.6 min | 219 s |

## Forsinkelse for Snarøya-beboere

Kun turer med avgang fra Snarøya (snv_syd-sonen). Viser forsinkelsen for beboere som skal ut fra halvøya.

| Scenario | Ant. turer | Gj.snitt reisetid | Gj.snitt tidstap |
|---|---|---|---|

## Estimert kølengde

Beregnet fra antall blokkerte + ventende kjøretøy, konvertert med 120 kjt/km (stoppet trafikk) fordelt på 2 tilkomstfelt.

| Scenario | Blokkerte kjt | Maks ventende | Kølengde (km) |
|---|---|---|---|
| Base (Sc. 1A) PM | 288 | 580 | 3.6 km |
| Base (Sc. 1A) AM | 241 | 911 | 4.8 km |
| V1 (Sc. 1A) PM | 233 | 588 | 3.4 km |
| V1 (Sc. 1A) AM | 64 | 563 | 2.6 km |
| Base (dagens profil) PM | 0 | 362 | 1.5 km |
| Base + konsert PM | 5217 | 5467 | 44.5 km |
| Base (dagens profil) AM | 0 | 212 | 0.9 km |
| V1 PM | 0 | 332 | 1.4 km |
| V1 + konsert PM | 5357 | 5557 | 45.5 km |
| V1 AM | 0 | 126 | 0.5 km |
| V1 + miljøgate PM | 154 | 288 | 1.8 km |
| V1 + miljøgate AM | 0 | 359 | 1.5 km |
| V2 PM | 102 | 389 | 2.0 km |
| V2 AM | 251 | 454 | 2.9 km |
| V3 PM | 0 | 319 | 1.3 km |
| V3 AM | 0 | 77 | 0.3 km |

## Begrensninger

- Modellen mangler fortsatt observasjonsbasert kalibrering, og testdekningen dekker foreløpig bare de viktigste kodebanene.
- Flytårnet/Bernt Balchens-krysset er fortsatt avhengig av OSM-nettets geometri og prioriteringsmodell; dette er en kjent modellbegrensning som må forbedres før rapportering utad.
- Scenarioet med signaloptimalisering er midlertidig tatt ut av standardkjøringen til kryssmodellen er eksplisitt implementert.
- Utrykningstidsberegningen forutsetter at andre kjøretøy viker (SUMO vClass=emergency). I praksis er dette avhengig av at det finnes plass å vike til — med 2+2 felt er det mindre rom for å slippe frem utrykningskjøretøy enn med 2+3.
- Kølengdeestimatet er en forenklet omregning og tar ikke hensyn til faktisk køgeometri eller E18-tilknytning.

