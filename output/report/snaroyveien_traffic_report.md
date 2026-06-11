# Trafikkanalyse Snarøyveien

*Automatisk generert 11.06.2026 kl. 11:50*

## QA-status

Denne rapporten bruker periodedelte scenarioer (AM/PM), appendix-baserte OD-matriser og en systemforsinkelses-KPI som inkluderer både fullførte turer og blokkerte avganger.

Det betyr at tallene under ikke er direkte sammenlignbare med tidligere repo-utgaver som brukte kun morgenrute og kun tidstap fra fullførte turer.

## Hovedobservasjoner

### Morgenrush 07:45-08:45

- Base (5/5 seeds): 9.2 ± 0.2 min reisetid, 263.3 ± 15.4 kjt-t systemforsinkelse, 151 ± 45 kjt maks ventende.
- V1 (5/5 seeds): 9.9 ± 0.3 min reisetid, 249.6 ± 17.4 kjt-t systemforsinkelse, 117 ± 48 kjt maks ventende.
- Endring V1 vs. base (snitt): 9.9 min (+0.7 min vs. base), 249.6 kjt-t (-13.8 kjt-t vs. base), 117 kjt (-35 kjt vs. base). Tall etter ± er standardavvik over seeds; vurder overlapp før forskjeller tolkes som reelle.

### Ettermiddagsrush 15:30-16:30

- Base (5/5 seeds): 7.5 ± 0.2 min reisetid, 329.6 ± 8.5 kjt-t systemforsinkelse, 349 ± 5 kjt maks ventende.
- V1 (5/5 seeds): 9.2 ± 0.2 min reisetid, 362.0 ± 17.9 kjt-t systemforsinkelse, 334 ± 25 kjt maks ventende.
- Endring V1 vs. base (snitt): 9.2 min (+1.7 min vs. base), 362.0 kjt-t (+32.5 kjt-t vs. base), 334 kjt (-15 kjt vs. base). Tall etter ± er standardavvik over seeds; vurder overlapp før forskjeller tolkes som reelle.

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

Verdier er gjennomsnitt ± standardavvik over vellykkede seeds. «Seeds» viser hvor mange av kjøringene som ga brukbare resultater (mislykkede seeds er utelatt fra snittene).

| Scenario | Seeds | Reisetid | Systemforsinkelse | Blokkerte avganger | Maks ventende |
|---|---|---|---|---|---|
| Base (Sc. 1A) PM | 5/5 | 8.7 ± 0.1 min | 509.8 ± 9.5 kjt-t | 628 | 634 |
| Base (Sc. 1A) AM | 5/5 | 11.2 ± 0.4 min | 613.5 ± 26.4 kjt-t | 871 | 875 |
| V1 (Sc. 1A) PM | 5/5 | 10.1 ± 0.2 min | 508.1 ± 7.7 kjt-t | 604 | 609 |
| V1 (Sc. 1A) AM | 5/5 | 11.1 ± 0.6 min | 452.8 ± 52.5 kjt-t | 558 | 566 |
| Base (dagens profil) PM | 5/5 | 7.5 ± 0.2 min | 329.6 ± 8.5 kjt-t | 346 | 349 |
| Base + konsert PM | 5/5 | 7.6 ± 0.1 min | 1983.6 ± 3.3 kjt-t | 6151 | 6156 |
| Base (dagens profil) AM | 5/5 | 9.2 ± 0.2 min | 263.3 ± 15.4 kjt-t | 144 | 151 |
| Base (dagens profil, 80 % trafikk) PM | 5/5 | 6.1 ± 0.2 min | 171.0 ± 8.5 kjt-t | 155 | 158 |
| Base (dagens profil, 80 % trafikk) AM | 5/5 | 7.4 ± 0.1 min | 142.4 ± 4.5 kjt-t | 4 | 33 |
| V1 PM | 5/5 | 9.2 ± 0.2 min | 362.0 ± 17.9 kjt-t | 331 | 334 |
| V1 + konsert PM | 5/5 | 9.5 ± 0.1 min | 2029.9 ± 7.3 kjt-t | 6226 | 6229 |
| V1 AM | 5/5 | 9.9 ± 0.3 min | 249.6 ± 17.4 kjt-t | 107 | 117 |
| V1 + miljøgate PM | 5/5 | 10.2 ± 0.2 min | 321.7 ± 17.9 kjt-t | 315 | 320 |
| V1 + miljøgate AM | 5/5 | 11.9 ± 0.2 min | 290.0 ± 16.2 kjt-t | 381 | 382 |
| V1 (80 % trafikk) PM | 5/5 | 7.8 ± 0.1 min | 199.0 ± 6.5 kjt-t | 131 | 138 |
| V1 (80 % trafikk) AM | 5/5 | 8.5 ± 0.2 min | 157.1 ± 5.3 kjt-t | 2 | 33 |
| V2 PM | 5/5 | 8.5 ± 0.2 min | 296.4 ± 11.3 kjt-t | 390 | 400 |
| V2 AM | 5/5 | 8.9 ± 0.2 min | 299.6 ± 7.1 kjt-t | 454 | 458 |
| V3 PM | 5/5 | 9.3 ± 0.3 min | 359.0 ± 11.7 kjt-t | 324 | 328 |
| V3 AM | 5/5 | 10.0 ± 0.2 min | 253.9 ± 10.3 kjt-t | 99 | 105 |

## Utrykningstid (beredskap)

Tre ambulanser er lagt inn i hver simuleringsperiode (snv_syd → snv_nordost, dvs. Snarøya til nordre rundkjøring). Tabellen viser gjennomsnittlig reisetid for utrykningskjøretøy:

| Scenario | Utrykningstid (gj.snitt) | Maks utrykningstid | Tidstap utrykn. |
|---|---|---|---|
| Base (Sc. 1A) PM | 22.3 min | 22.4 min | 1041 s |
| Base (Sc. 1A) AM | 10.7 min | 12.5 min | 344 s |
| V1 (Sc. 1A) PM | 22.7 min | 24.1 min | 1035 s |
| V1 (Sc. 1A) AM | 12.1 min | 15.9 min | 397 s |
| Base (dagens profil) PM | 18.8 min | 20.2 min | 830 s |
| Base + konsert PM | 17.3 min | 20.1 min | 739 s |
| Base (dagens profil) AM | 9.5 min | 10.9 min | 277 s |
| Base (dagens profil, 80 % trafikk) PM | 11.2 min | 14.2 min | 376 s |
| Base (dagens profil, 80 % trafikk) AM | 7.8 min | 8.4 min | 174 s |
| V1 PM | 13.5 min | 14.7 min | 483 s |
| V1 + konsert PM | 19.9 min | 22.1 min | 860 s |
| V1 AM | 8.7 min | 9.4 min | 195 s |
| V1 + miljøgate PM | 39.8 min | 39.8 min | 1960 s |
| V1 + miljøgate AM | 11.6 min | 12.4 min | 267 s |
| V1 (80 % trafikk) PM | 9.7 min | 11.2 min | 253 s |
| V1 (80 % trafikk) AM | 7.8 min | 8.4 min | 144 s |
| V2 PM | 10.1 min | 11.3 min | 278 s |
| V2 AM | 8.9 min | 10.7 min | 206 s |
| V3 PM | 15.6 min | 17.8 min | 601 s |
| V3 AM | 9.9 min | 11.0 min | 264 s |

## Forsinkelse for Snarøya-beboere

Kun turer med avgang fra Snarøya (snv_syd-sonen). Viser forsinkelsen for beboere som skal ut fra halvøya.

| Scenario | Ant. turer | Gj.snitt reisetid | Gj.snitt tidstap |
|---|---|---|---|
| Base (Sc. 1A) PM | 290 | 19.0 min | 810 s |
| Base (Sc. 1A) AM | 607 | 10.7 min | 314 s |
| V1 (Sc. 1A) PM | 330 | 18.1 min | 728 s |
| V1 (Sc. 1A) AM | 626 | 11.2 min | 322 s |
| Base (dagens profil) PM | 327 | 16.3 min | 646 s |
| Base + konsert PM | 300 | 15.3 min | 594 s |
| Base (dagens profil) AM | 527 | 9.7 min | 258 s |
| Base (dagens profil, 80 % trafikk) PM | 347 | 9.9 min | 268 s |
| Base (dagens profil, 80 % trafikk) AM | 447 | 8.0 min | 160 s |
| V1 PM | 355 | 14.3 min | 503 s |
| V1 + konsert PM | 322 | 15.8 min | 599 s |
| V1 AM | 552 | 9.5 min | 222 s |
| V1 + miljøgate PM | 107 | 31.1 min | 1385 s |
| V1 + miljøgate AM | 503 | 12.1 min | 282 s |
| V1 (80 % trafikk) PM | 325 | 10.8 min | 299 s |
| V1 (80 % trafikk) AM | 444 | 8.4 min | 158 s |
| V2 PM | 447 | 9.6 min | 226 s |
| V2 AM | 542 | 9.2 min | 208 s |
| V3 PM | 366 | 14.4 min | 510 s |
| V3 AM | 521 | 10.2 min | 266 s |

## Estimert kølengde

Beregnet fra antall blokkerte + ventende kjøretøy, konvertert med 120 kjt/km (stoppet trafikk) fordelt på 2 tilkomstfelt.

| Scenario | Blokkerte kjt | Maks ventende | Kølengde (km) |
|---|---|---|---|
| Base (Sc. 1A) PM | 628 | 634 | 5.2 km |
| Base (Sc. 1A) AM | 871 | 875 | 7.3 km |
| V1 (Sc. 1A) PM | 604 | 609 | 5.0 km |
| V1 (Sc. 1A) AM | 558 | 566 | 4.7 km |
| Base (dagens profil) PM | 346 | 349 | 2.9 km |
| Base + konsert PM | 6151 | 6156 | 51.3 km |
| Base (dagens profil) AM | 144 | 151 | 1.2 km |
| Base (dagens profil, 80 % trafikk) PM | 155 | 158 | 1.3 km |
| Base (dagens profil, 80 % trafikk) AM | 4 | 33 | 0.1 km |
| V1 PM | 331 | 334 | 2.8 km |
| V1 + konsert PM | 6226 | 6229 | 51.9 km |
| V1 AM | 107 | 117 | 0.9 km |
| V1 + miljøgate PM | 315 | 320 | 2.6 km |
| V1 + miljøgate AM | 381 | 382 | 3.2 km |
| V1 (80 % trafikk) PM | 131 | 138 | 1.1 km |
| V1 (80 % trafikk) AM | 2 | 33 | 0.1 km |
| V2 PM | 390 | 400 | 3.3 km |
| V2 AM | 454 | 458 | 3.8 km |
| V3 PM | 324 | 328 | 2.7 km |
| V3 AM | 99 | 105 | 0.9 km |

## Begrensninger

- Modellen mangler fortsatt observasjonsbasert kalibrering, og testdekningen dekker foreløpig bare de viktigste kodebanene.
- Flytårnet/Bernt Balchens-krysset er fortsatt avhengig av OSM-nettets geometri og prioriteringsmodell; dette er en kjent modellbegrensning som må forbedres før rapportering utad.
- Scenarioet med signaloptimalisering er midlertidig tatt ut av standardkjøringen til kryssmodellen er eksplisitt implementert.
- Utrykningstidsberegningen forutsetter at andre kjøretøy viker (SUMO vClass=emergency). I praksis er dette avhengig av at det finnes plass å vike til — med 2+2 felt er det mindre rom for å slippe frem utrykningskjøretøy enn med 2+3.
- Kølengdeestimatet er en forenklet omregning og tar ikke hensyn til faktisk køgeometri eller E18-tilknytning.

