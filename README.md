# Snarøyveien Trafikksimulering

Dette prosjektet er en åpen SUMO (Simulation of Urban MObility)-simulering av trafikken på Snarøyveien og Fornebu, med fokus på hva som skjer når veien forbi Flytårnet stasjon får lavere kapasitet enn tidligere.

Målet er å gjøre trafikkdiskusjonen mer etterprøvbar:

- Hvilke køer oppstår i morgen- og ettermiddagsrushet?
- Hvor mye dårligere blir framkommeligheten når veinettet strammes inn?
- Hvilke varianter ser ut til å fungere best og dårligst?

Prosjektet er laget som et uavhengig, åpent supplement til de offisielle utredningene, og er ikke en offisiell rapport fra Bærum kommune eller Fornebubanen.

## Kort fortalt

Den siste 5-seed-kjøringen i dette repoet peker i samme retning i både morgen- og ettermiddagsrush:

- Dagens profil (ingen innsnevring) kommer best ut.
- Variant V1 (KDP3-forslaget, 2+2 bygate) kommer tydelig dårligere ut enn dagens profil.
- Variant V3 (hybridvariant) kommer litt bedre ut enn V1, men fortsatt dårligere enn dagens profil.
- Variant V2 (lavkapasitetsvariant, 1+1 + kollektivfelt) kommer dårligst ut av de utredede variantene.

For scenariet som helhet viser de oppdaterte 5-seed-resultatene blant annet:

- Morgenrush: gjennomsnittlig reisetid øker fra 3,7 til 5,3 minutter fra base til V1.
- Morgenrush: systemforsinkelse øker fra 495,9 til 597,3 kjøretøy-timer fra base til V1.
- Ettermiddagsrush: gjennomsnittlig reisetid øker fra 3,7 til 5,2 minutter fra base til V1.
- Ettermiddagsrush: systemforsinkelse øker fra 404,3 til 490,2 kjøretøy-timer fra base til V1.

## Varianter og scenario

### Scenario 4A

Scenario 4A er trafikkgrunnlaget som brukes i alle simuleringene. Det er hentet fra PGF-rapporten og beskriver trafikken i 2040 med full utbygging av Fornebu og innstrammet parkeringsnorm – omtrent 31 300 turer per døgn. Morgenrush (07:45–08:45) og ettermiddagsrush (15:30–16:30) simuleres separat.

### Base (dagens profil)

Dagens veinett med 2+3 felt (2 sørgående + 3 nordgående). Dette er referansepunktet alle variantene måles mot.

### V1 – KDP3-forslaget (2+2 bygate)

Den offisielle anbefalingen fra kommunedelplan 3: Snarøyveien bygges om til en 2+2-felts bygate med 40 km/t, separate gang- og sykkelfelt, og busstasjon med kantstopp. Kapasiteten reduseres fra dagens 2+3 til 2+2. Simuleringene viser at reisetid og forsinkelse øker merkbart sammenlignet med dagens profil.

### V2 – Lavkapasitetsvariant (1+1 + kollektivfelt)

Den mest restriktive varianten: kun 1 kjørefelt + 1 kollektivfelt i hver retning. Testene viser at V2 gir dårligst framkommelighet av alle variantene, med høyest forsinkelse og lengst kø.

### V3 – Hybridvariant

En mellomløsning der noen strekninger beholder 3 felt nordover mens andre strammes inn til 2. V3 kommer bedre ut enn V1 i simuleringene, men fortsatt dårligere enn dagens profil.

### V1 + miljøgate

V1 kombinert med Rolfsbuktveien som miljøgate (15 km/t). Når alternativruten også begrenses, blir konsekvensene størst – simulering viser gjennomsnittlig reisetid på 7,4 min og over 1 000 kjøretøy-timer i systemforsinkelse i morgenrushet.

## Hva prosjektet inneholder

- Et digitalt veinett for Fornebu/Snarøya-området.
- Trafikkgrunnlag basert på OD-matriser fra vedleggene i PGF-rapporten.
- Simuleringer for både morgen- og ettermiddagsrush.
- Sammenligning av flere varianter av Snarøyveien.
- Figurer, animasjoner og en rapport som kan leses uten teknisk bakgrunn.

## Viktigste figurer

### Morgenrush: reisetid

![Morgenrush reisetid](output/visualizations/morning_avg_duration.png)

### Morgenrush: systemforsinkelse

![Morgenrush systemforsinkelse](output/visualizations/morning_system_delay.png)

### Ettermiddagsrush: reisetid

![Ettermiddagsrush reisetid](output/visualizations/afternoon_avg_duration.png)

### Ettermiddagsrush: systemforsinkelse

![Ettermiddagsrush systemforsinkelse](output/visualizations/afternoon_system_delay.png)

## Animasjoner og videoer

Github viser ikke alltid videofiler like pent direkte i README, så de er lenket her:

- [Side-by-side-animasjon (GIF)](output/visualizations/side_by_side.gif)
- [Side-by-side-animasjon (MP4)](output/visualizations/side_by_side.mp4)
- [Køvekst gjennom rush (GIF)](output/visualizations/queue_growth.gif)
- [Køvekst gjennom rush (MP4)](output/visualizations/queue_growth.mp4)
- [Trafikkavspilling for V1 (GIF)](output/visualizations/traffic_replay_scenario_4A_v1.gif)
- [Trafikkavspilling for V1 (MP4)](output/visualizations/traffic_replay_scenario_4A_v1.mp4)
- [Interaktivt dashboard (HTML)](output/visualizations/dashboard.html)

## Presentasjonskart

Det finnes en interaktiv kartvisning med Kartverket-kart i bakgrunnen og SUMO-data oppå. Kartsiden er en ren statisk nettside (HTML + JS + JSON) uten noen backend, og publiseres automatisk som GitHub Pages via en Actions-workflow.

**Live-versjon:** Se kartet direkte på [GitHub Pages-siden til dette repoet](https://damsleth.github.io/snv-trafikk/).

Innhold:

- **Vegvariant:** Base (dagens profil), V1, V2, V3 og V1 + miljøgate
- **Tidsrom:** Morgenrush (07:45–08:45), ettermiddagsrush (15:30–16:30) og et syntetisk estimat for midt på dagen
- **Blålyskjøretøy:** Eget lag for simulerte utrykningskjøretøy
- **Konsertpåslag:** Unity Arena-konsert med ekstra trafikk ettermiddag/kveld
- **Trafikkinnføring:** Viser innkommende/utgående trafikk fra Snarøya, E18 vest, E18 øst og Ring 3 nord (Granfosstunnelen)
- **Avansert side:** `advanced.html` viser signalpunkter, rundkjøringer, edge-metadata, lokal redigeringsmodus og artefakt-/patcharbeidsflate uten å belaste hovedsiden

### Kjør lokalt

```bash
uv run python scripts/07_export_presentation_data.py
uv run python scripts/08_serve_presentation.py
```

Åpne deretter [http://127.0.0.1:8000](http://127.0.0.1:8000).

Den rene simulatoren ligger på `index.html`, mens den avanserte arbeidsflaten ligger på `advanced.html`.

`advanced.html` kan nå også sende lokale edge-/artefaktpatcher til den lokale presentasjonsserveren og kjøre et patched scenario direkte. Dette krever at siden kjøres via `scripts/08_serve_presentation.py`, siden API-et eksponeres derfra på samme origin.

For å oversette en nedlastet patchpakke fra `advanced.html` til SUMO-filer kan du kjøre:

```bash
uv run python scripts/09_generate_patch_files.py --input path/to/patch.json --output tmp/patch_bundle
```

Dette skriver `.edg.xml`, `.con.xml` og en metadatafil for artefakter som ennå ikke kan oversettes direkte til netconvert-patcher.

Merk: morgen- og ettermiddagskartene bygger på reelle SUMO-kjøringer. Midt på dagen er laget som et tydelig merket presentasjonsestimat.

## Les mer

Hvis du vil gå dypere enn figurene:

- Oppsummert resultatrapport: [output/report/snaroyveien_traffic_report.md](output/report/snaroyveien_traffic_report.md)
- Tolkning av offisiell utredning: [OFFICIAL_REPORT_INTERPRETATION.md](OFFICIAL_REPORT_INTERPRETATION.md)
- Utviklingslogg: [DEVLOG.md](DEVLOG.md)

## Viktige forbehold

Dette repoet er betydelig forbedret gjennom QA, men det finnes fortsatt begrensninger:

- Modellen er fortsatt ikke fullt kalibrert mot observerte trafikktellinger.
- Flytårnet / Bernt Balchens vei er fortsatt enklere modellert enn i en full håndbygget mikrosimulering.
- Resultatene bør derfor brukes som et åpent og etterprøvbart beslutningsstøtteverktøy, ikke som eneste grunnlag for politiske vedtak.

## For deg som bare vil se konklusjonen

Hvis du er innom repoet for å forstå saken raskt, er dette det viktigste:

1. Se figurene over.
2. Åpne [resultatrapporten](output/report/snaroyveien_traffic_report.md).
3. Sammenlign base, V1, V2 og V3.

## For deg som vil kjøre analysen selv

```bash
uv run python scripts/01_fetch_osm.py
uv run python scripts/02_build_network.py
uv run python scripts/03_generate_demand.py
uv run python scripts/04_run_simulation.py --all --seeds 5
uv run python scripts/05_analyze_results.py
uv run python scripts/06_generate_report.py
```

For sensitivitetskjøringer kan du i tillegg generere skalerte OD-varianter, for eksempel:

```bash
uv run python scripts/03_generate_demand.py --demand-scale 0.8
```

Dette skriver egne `*_scale_0_8`-ruter/CSV-er og inkluderer også skalaer som er deklarert i `scripts/utils/scenario_catalog.py`.

## Dataflyt i pipeline

Pipeline-kjedene er bevisst enkle og filbaserte:

1. `scripts/01_fetch_osm.py`
	Leser fra Overpass API og skriver `network/osm/fornebu.osm.xml`.
2. `scripts/02_build_network.py`
	Leser OSM-data og skriver base- og variantnett i `network/base/` og `network/proposed/`.
3. `scripts/03_generate_demand.py`
	Leser OD-matriser i koden og skriver ruter og CSV-er i `demand/routes/` og `demand/od_matrices/`, inkludert eventuelle skalerte varianter.
4. `scripts/04_run_simulation.py`
	Leser nett og ruter, kjører SUMO og skriver seed-resultater i `output/<scenario>/seed_<n>/` samt `output/all_results.json`.
5. `scripts/05_analyze_results.py`
	Leser `output/all_results.json` og `summary.xml`, og skriver figurer til `output/visualizations/`.
6. `scripts/06_generate_report.py`
	Leser `output/all_results.json` og skriver rapport og aggregater til `output/report/`.
7. `scripts/07_export_presentation_data.py`
	Leser rapportaggregater og SUMO-output og skriver presentasjonsdata til `web/presentation/data/`.
8. `scripts/08_serve_presentation.py`
	Serverer `web/presentation/` lokalt som en statisk side.

## Lokal QA

Anbefalt minimumssekvens før større endringer merges:

```bash
uv run --extra dev pytest -q
uv run python -m compileall scripts tests
```

Ved endringer i presentasjonsdata eller rapportlogikk er det også naturlig å kjøre:

```bash
uv run python scripts/06_generate_report.py
uv run python scripts/07_export_presentation_data.py
```
