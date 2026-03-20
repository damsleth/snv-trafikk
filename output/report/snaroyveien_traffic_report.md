# Trafikkanalyse Snarøyveien

*Automatisk generert 20.03.2026 kl. 09:08*

## QA-status

Denne rapporten bruker periodedelte scenarioer (AM/PM), appendix-baserte OD-matriser og en systemforsinkelses-KPI som inkluderer både fullførte turer og blokkerte avganger.

Det betyr at tallene under ikke er direkte sammenlignbare med tidligere repo-utgaver som brukte kun morgenrute og kun tidstap fra fullførte turer.

## Hovedobservasjoner

### Morgenrush 07:45-08:45

- Base: 9.4 min gjennomsnittlig reisetid, 273.6 kjt-t systemforsinkelse, 176 maks ventende kjøretøy.
- V1: 9.8 min gjennomsnittlig reisetid, 236.7 kjt-t systemforsinkelse, 89 maks ventende kjøretøy.
- Endring V1 vs. base: 9.8 min (+0.4 min vs. base), 236.7 kjt-t (-36.8 kjt-t vs. base), 89 kjt (-87 kjt vs. base).

### Ettermiddagsrush 15:30-16:30

- Base: 7.6 min gjennomsnittlig reisetid, 328.9 kjt-t systemforsinkelse, 350 maks ventende kjøretøy.
- V1: 9.2 min gjennomsnittlig reisetid, 357.6 kjt-t systemforsinkelse, 324 maks ventende kjøretøy.
- Endring V1 vs. base: 9.2 min (+1.6 min vs. base), 357.6 kjt-t (+28.8 kjt-t vs. base), 324 kjt (-26 kjt vs. base).

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
| Base (Sc. 1A) PM | 8.8 min | 516.3 kjt-t | 588 | 599 |
| Base (Sc. 1A) AM | 11.2 min | 600.8 kjt-t | 880 | 883 |
| V1 (Sc. 1A) PM | 10.1 min | 520.3 kjt-t | 609 | 618 |
| V1 (Sc. 1A) AM | 11.4 min | 482.8 kjt-t | 586 | 595 |
| Base (dagens profil) PM | 7.6 min | 328.9 kjt-t | 344 | 350 |
| Base + konsert PM | 7.7 min | 1987.3 kjt-t | 6158 | 6163 |
| Base (dagens profil) AM | 9.4 min | 273.6 kjt-t | 168 | 176 |
| Base (dagens profil, 80 % trafikk) PM | 6.4 min | 174.1 kjt-t | 145 | 150 |
| Base (dagens profil, 80 % trafikk) AM | 7.4 min | 142.5 kjt-t | 4 | 33 |
| V1 PM | 9.2 min | 357.6 kjt-t | 317 | 324 |
| V1 + konsert PM | 9.7 min | 2034.7 kjt-t | 6227 | 6229 |
| V1 AM | 9.8 min | 236.7 kjt-t | 75 | 89 |
| V1 + miljøgate PM | 10.6 min | 337.0 kjt-t | 303 | 312 |
| V1 + miljøgate AM | 12.2 min | 290.4 kjt-t | 388 | 390 |
| V1 (80 % trafikk) PM | 7.9 min | 199.8 kjt-t | 133 | 136 |
| V1 (80 % trafikk) AM | 8.5 min | 156.8 kjt-t | 1 | 33 |
| V2 PM | 8.5 min | 295.0 kjt-t | 394 | 398 |
| V2 AM | 8.8 min | 293.2 kjt-t | 456 | 459 |
| V3 PM | 9.2 min | 355.3 kjt-t | 313 | 318 |
| V3 AM | 9.9 min | 247.8 kjt-t | 80 | 84 |

## Utrykningstid (beredskap)

Tre ambulanser er lagt inn i hver simuleringsperiode (snv_syd → snv_nordost, dvs. Snarøya til nordre rundkjøring). Tabellen viser gjennomsnittlig reisetid for utrykningskjøretøy:

| Scenario | Utrykningstid (gj.snitt) | Maks utrykningstid | Tidstap utrykn. |
|---|---|---|---|
| Base (Sc. 1A) PM | 21.2 min | 21.9 min | 976 s |
| Base (Sc. 1A) AM | 10.9 min | 12.3 min | 352 s |
| V1 (Sc. 1A) PM | 19.6 min | 20.2 min | 845 s |
| V1 (Sc. 1A) AM | 13.1 min | 19.8 min | 456 s |
| Base (dagens profil) PM | 17.2 min | 17.8 min | 729 s |
| Base + konsert PM | 23.4 min | 29.6 min | 1099 s |
| Base (dagens profil) AM | 9.7 min | 11.5 min | 286 s |
| Base (dagens profil, 80 % trafikk) PM | 10.8 min | 13.0 min | 349 s |
| Base (dagens profil, 80 % trafikk) AM | 8.2 min | 8.8 min | 199 s |
| V1 PM | 12.7 min | 15.9 min | 435 s |
| V1 + konsert PM | 16.0 min | 18.5 min | 635 s |
| V1 AM | 8.8 min | 9.8 min | 202 s |
| V1 + miljøgate PM | 34.2 min | 34.2 min | 1621 s |
| V1 + miljøgate AM | 11.7 min | 12.3 min | 273 s |
| V1 (80 % trafikk) PM | 9.5 min | 11.2 min | 245 s |
| V1 (80 % trafikk) AM | 7.7 min | 8.3 min | 139 s |
| V2 PM | 9.5 min | 10.6 min | 242 s |
| V2 AM | 9.1 min | 10.1 min | 222 s |
| V3 PM | 14.7 min | 17.6 min | 551 s |
| V3 AM | 8.9 min | 9.6 min | 207 s |

## Forsinkelse for Snarøya-beboere

Kun turer med avgang fra Snarøya (snv_syd-sonen). Viser forsinkelsen for beboere som skal ut fra halvøya.

| Scenario | Ant. turer | Gj.snitt reisetid | Gj.snitt tidstap |
|---|---|---|---|
| Base (Sc. 1A) PM | 332 | 17.7 min | 732 s |
| Base (Sc. 1A) AM | 609 | 10.3 min | 294 s |
| V1 (Sc. 1A) PM | 337 | 18.2 min | 735 s |
| V1 (Sc. 1A) AM | 649 | 11.2 min | 321 s |
| Base (dagens profil) PM | 311 | 16.3 min | 651 s |
| Base + konsert PM | 288 | 17.4 min | 715 s |
| Base (dagens profil) AM | 533 | 10.0 min | 274 s |
| Base (dagens profil, 80 % trafikk) PM | 359 | 11.5 min | 360 s |
| Base (dagens profil, 80 % trafikk) AM | 445 | 8.2 min | 172 s |
| V1 PM | 368 | 13.5 min | 457 s |
| V1 + konsert PM | 342 | 15.5 min | 578 s |
| V1 AM | 546 | 9.7 min | 232 s |
| V1 + miljøgate PM | 134 | 28.9 min | 1266 s |
| V1 + miljøgate AM | 508 | 12.3 min | 292 s |
| V1 (80 % trafikk) PM | 342 | 10.6 min | 286 s |
| V1 (80 % trafikk) AM | 443 | 8.4 min | 160 s |
| V2 PM | 450 | 9.8 min | 240 s |
| V2 AM | 552 | 9.3 min | 211 s |
| V3 PM | 328 | 14.1 min | 494 s |
| V3 AM | 541 | 9.8 min | 240 s |

## Estimert kølengde

Beregnet fra antall blokkerte + ventende kjøretøy, konvertert med 120 kjt/km (stoppet trafikk) fordelt på 2 tilkomstfelt.

| Scenario | Blokkerte kjt | Maks ventende | Kølengde (km) |
|---|---|---|---|
| Base (Sc. 1A) PM | 588 | 599 | 4.9 km |
| Base (Sc. 1A) AM | 880 | 883 | 7.3 km |
| V1 (Sc. 1A) PM | 609 | 618 | 5.1 km |
| V1 (Sc. 1A) AM | 586 | 595 | 4.9 km |
| Base (dagens profil) PM | 344 | 350 | 2.9 km |
| Base + konsert PM | 6158 | 6163 | 51.3 km |
| Base (dagens profil) AM | 168 | 176 | 1.4 km |
| Base (dagens profil, 80 % trafikk) PM | 145 | 150 | 1.2 km |
| Base (dagens profil, 80 % trafikk) AM | 4 | 33 | 0.1 km |
| V1 PM | 317 | 324 | 2.7 km |
| V1 + konsert PM | 6227 | 6229 | 51.9 km |
| V1 AM | 75 | 89 | 0.7 km |
| V1 + miljøgate PM | 303 | 312 | 2.6 km |
| V1 + miljøgate AM | 388 | 390 | 3.3 km |
| V1 (80 % trafikk) PM | 133 | 136 | 1.1 km |
| V1 (80 % trafikk) AM | 1 | 33 | 0.1 km |
| V2 PM | 394 | 398 | 3.3 km |
| V2 AM | 456 | 459 | 3.8 km |
| V3 PM | 313 | 318 | 2.6 km |
| V3 AM | 80 | 84 | 0.7 km |

## Begrensninger

- Modellen mangler fortsatt observasjonsbasert kalibrering, og testdekningen dekker foreløpig bare de viktigste kodebanene.
- Flytårnet/Bernt Balchens-krysset er fortsatt avhengig av OSM-nettets geometri og prioriteringsmodell; dette er en kjent modellbegrensning som må forbedres før rapportering utad.
- Scenarioet med signaloptimalisering er midlertidig tatt ut av standardkjøringen til kryssmodellen er eksplisitt implementert.
- Utrykningstidsberegningen forutsetter at andre kjøretøy viker (SUMO vClass=emergency). I praksis er dette avhengig av at det finnes plass å vike til — med 2+2 felt er det mindre rom for å slippe frem utrykningskjøretøy enn med 2+3.
- Kølengdeestimatet er en forenklet omregning og tar ikke hensyn til faktisk køgeometri eller E18-tilknytning.

