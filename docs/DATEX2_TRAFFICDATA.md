# DATEX2 / Trafikkdata Refresh

The current local traffic count export in `.plans/trafikkdata/` is hourly. The active follow-up is to pull higher-resolution data for the same six sensor points using Trafikkdata GraphQL or DATEX2 3.1.

## Target Sensors

See `.plans/trafikkdata/trafikkdata-atlas-vegvesen.md` for the selected points:

- Snarøyveien
- Fornebuveien
- Fornebukrysset off-ramp from E18 toward Lysaker
- Fornebukrysset ramp from Granfoss tunnel and E18
- Fornebukrysset on-ramp from Fornebu toward E18 Drammen
- Lysakerlokket ramp

## Desired Resolution

Prefer 15-minute bins or per-passage observations for the same date window currently represented by the hourly export.

## Suggested Workflow

1. Query `https://trafikkdata.atlas.vegvesen.no/graphql` for the selected traffic registration points.
2. Store raw exports under `.plans/trafikkdata/` because this remains local working state.
3. Produce a normalized CSV with sensor id, timestamp, direction, volume, and resolution.
4. Feed the normalized data into the validation checks planned in `docs/DEVELOPMENT.md` and `.plans/dataset-review.md`.

## Notes

This step depends on the external API and exact sensor identifiers; it was not executed automatically during the implementation pass.
