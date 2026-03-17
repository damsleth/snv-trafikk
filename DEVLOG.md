# snv-trafikk devlog
løpende liste over endringer og forbedringer i snv-trafikk.  
omvendt kronologisk, med de nyeste endringene øverst.  
endringer legges til med dato, timestamp og en kort beskrivelse av hva som er gjort, direkte under denne linjen.
---  
2026-03-17 11:19:09 CET - oppdaterte rapportgeneratorens begrensningstekst og regenererte rapport-/presentasjonsartefakter slik at avledede filer samsvarer med dagens kode og data.
2026-03-17 10:46:21 CET - samlet delte output-/rapport-/presentasjonsstier i scripts/config.py og fjernet unødvendige sys.path-hacks fra analyse-, rapport- og eksportskriptene.
2026-03-17 10:37:54 CET - fjernet ubrukte nettverks-hjelpemoduler slik at scripts/02_build_network.py er eneste kanoniske sti for nettverksvarianter og signalrelatert byggelogikk.
2026-03-17 10:31:12 CET - modulariserte presentasjonsappen i native ES-moduler, samlet kart-/data-/diagramansvar bedre og rettet syntetiske/konsert-KPI-er i frontend.
2026-03-17 10:09:27 CET - fortsatte QA-remediering: delte resultat-hjelpere, strammet inn feilhåndtering, flyttet presentasjonsmetadata til manifestet, la til README-dataflyt/QA og fjernet `main.py`.  
2026-03-17 09:56:48 CET - la til QA_IMPLEMENTATION_CHECKLIST.md og gjennomførte første QA-remedieringsbatch: pytest-oppsett, felles KPI-konstanter og første enhetstester.  
2026-03-17 09:50:44 CET - la til QA_REVIEW_FINAL.md som sammenslått sluttversjon av QA_REVIEW.md og QA_REVIEW_2.md.  
2026-03-17 09:46:36 CET - la til QA_REVIEW_2.md med en ny, prioritert QA- og refaktoreringsplan uten å implementere endringer.  