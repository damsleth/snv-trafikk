# snv-trafikk devlog
løpende liste over endringer og forbedringer i snv-trafikk.  
omvendt kronologisk, med de nyeste endringene øverst.  
endringer legges til med dato, timestamp og en kort beskrivelse av hva som er gjort, direkte under denne linjen.
---  
2026-06-11 11:15:29 CET - rapportgeneratoren viser nå gjennomsnitt ± standardavvik over seeds og antall vellykkede seeds per scenario (ny `seed_counts`-hjelper), slik at mislykkede seeds ikke lenger forsvinner stille fra snittene og forskjeller kan vurderes mot spredningen.
2026-06-11 11:15:29 CET - flyttet rundkjøringskalibreringen (gap-aksept + fartsfordeling) til `car`-vType-en som trafikken faktisk bruker; den lå tidligere på en ubrukt `default`-vType og hadde derfor ingen effekt. `roundabout_params.add.xml` redefinerer nå SUMOs reelle `DEFAULT_VEHTYPE` i stedet for en død type. Krever full rerun (03→04→05→06) for at resultatene skal oppdateres.
2026-06-11 11:15:29 CET - kodegjennomgang: la til manglende `import sys` i 03/04 (krasjet på feilstier), netconvert-feil kaster nå i 02 i stedet for å svelges stille, rettet døde README-lenker (QA_REPORT/QA_REMEDIATION_PLAN/docs) og fylte ut pyproject-beskrivelsen.
2026-03-20 09:09:58 CET - la til OFFICIAL_REPORT_INTERPRETATION.md som låser hvordan PGF-rapporten skal leses før nye simuleringer, inkludert skillet mellom offisiell 60-minutters sammenlignings-KPI og eventuell lengre diagnostisk avviklingshorisont.
2026-03-20 09:09:58 CET - kjørte full 5-seed-rerun av alle scenarioer med oppdatert 60-minutters horisont og regenererte `output/`-artefakter, rapport, visualiseringer og presentasjonsdata/manifest.
2026-03-20 08:08:52 CET - byttet til de eksakte 1A/4A-appendiksmatrisene fra PGF-rapporten, la inn eksakt-bevarende disaggregasjon av nordøstsonen og strammet inn standard simulerings-/presentasjonshorisonten til rapportens 60-minutters rushvindu.
2026-03-17 13:50:03 CET - la til separat advanced.html med edge-inspektør, lokal redigerings-/artefaktarbeidsflate, rikere nettverksmetadata i presentasjonseksporten og en patch-generator for `.edg.xml`/`.con.xml` fra nedlastede patchpakker.
2026-03-17 11:20:24 CET - la til skalerbar OD-generering med `--demand-scale`, deklarative 80 %-scenarier i scenario-katalogen, nye skalerte rute/CSV-artefakter og testdekning for skalaoppløsning/avrunding.
2026-03-17 11:19:09 CET - oppdaterte rapportgeneratorens begrensningstekst og regenererte rapport-/presentasjonsartefakter slik at avledede filer samsvarer med dagens kode og data.
2026-03-17 10:46:21 CET - samlet delte output-/rapport-/presentasjonsstier i scripts/config.py og fjernet unødvendige sys.path-hacks fra analyse-, rapport- og eksportskriptene.
2026-03-17 10:37:54 CET - fjernet ubrukte nettverks-hjelpemoduler slik at scripts/02_build_network.py er eneste kanoniske sti for nettverksvarianter og signalrelatert byggelogikk.
2026-03-17 10:31:12 CET - modulariserte presentasjonsappen i native ES-moduler, samlet kart-/data-/diagramansvar bedre og rettet syntetiske/konsert-KPI-er i frontend.
2026-03-17 10:09:27 CET - fortsatte QA-remediering: delte resultat-hjelpere, strammet inn feilhåndtering, flyttet presentasjonsmetadata til manifestet, la til README-dataflyt/QA og fjernet `main.py`.  
2026-03-17 09:56:48 CET - la til QA_IMPLEMENTATION_CHECKLIST.md og gjennomførte første QA-remedieringsbatch: pytest-oppsett, felles KPI-konstanter og første enhetstester.  
2026-03-17 09:50:44 CET - la til QA_REVIEW_FINAL.md som sammenslått sluttversjon av QA_REVIEW.md og QA_REVIEW_2.md.  
2026-03-17 09:46:36 CET - la til QA_REVIEW_2.md med en ny, prioritert QA- og refaktoreringsplan uten å implementere endringer.  
