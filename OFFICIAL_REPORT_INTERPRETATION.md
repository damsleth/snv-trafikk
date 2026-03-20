# Official Report Interpretation

This note records how the PGF / Aimsun report is to be read before any new
simulation work is started. The purpose is to lock the interpretation once, so
the model is calibrated against a stable target instead of being reinterpreted
during each rerun.

Source report:
[docs/Trafikkanalyse_Snar_yveien_PF_FLY0_070_RA_0006_02_G_O__7133122_1_A_2447954.pdf](/Users/damsleth/Code/snv-trafikk/docs/Trafikkanalyse_Snar_yveien_PF_FLY0_070_RA_0006_02_G_O__7133122_1_A_2447954.pdf)

## Report Observations

1. The official model is built around the peak-hour demand periods only.
   Morning is 07:45-08:45. Afternoon is 15:30-16:30.

2. The report explicitly says the calculations cover only the approximate
   max-hour of each rush period. It also explicitly says the model does not
   answer how the queue continues to develop after the calculation ends.

3. The report also states that the worst 10-minute delay period occurs at the
   end of the modeled hour:
   morning 08:35-08:45, afternoon 16:20-16:30.
   Interpretation:
   the system is still worsening at the end of the official comparison window.

4. The official “virtual queue” metric is not “maximum queue at any time”.
   It is the number of vehicles still outside the model at the end of the
   modeled period because they were unable to enter.

5. The official OD matrices in appendix 1 are the traffic basis.
   They represent all modeled motor vehicles in the matrix:
   passenger cars plus heavy vehicles.
   Buses are added separately and are not part of the appendix matrix totals.

6. The official report uses averages from 10 replications.

7. The narrative conclusions matter as calibration targets, not just the raw
   numbers. In particular, for scenario 4A:
   Base should perform best overall.
   V1 should be worse than base, not better.
   V2 should be clearly worst.
   V3 should be near V1 and not materially better than base.

8. For scenario 4A / V1 / morning, the report says there is still a substantial
   queue on Snarøyveien south at the end of the hour, on the order of about
   310 vehicles outside the model.
   Interpretation:
   a simulation result where V1 morning ends with almost no blocked traffic is
   not consistent with the official report.

9. The report also says the queue may continue to build somewhat after the end
   of the modeled hour because the rush peak is reached late.
   Interpretation:
   a runtime longer than 60 minutes can be useful and may be necessary for
   diagnostics, but that does not change what the report-comparable metric is.

## Locked Interpretation For This Repo

1. There are two different concepts and they must not be mixed:
   Official comparison window:
   the modeled peak hour only.
   Diagnostic clearance window:
   extra simulated time after the peak hour to see how queues continue.

2. If the purpose is comparison to the official report, the primary KPI
   snapshot must be taken at the end of the official modeled hour, not after a
   longer clearance run.

3. If a longer runtime is used, the repo must expose both:
   Report-comparable metrics at t = 3600 s.
   Diagnostic tail / clearance metrics after t = 3600 s.

4. A longer runtime is therefore acceptable, and probably desirable, but only
   if the 60-minute report snapshot remains the primary comparison basis.

5. The model should not be considered aligned with the report unless it gets
   both of these broadly right:
   The ordering and direction of results between Base, V1, V2, and V3.
   The rough magnitude and location of end-of-hour virtual queues.

6. Any future change that improves “clearance by 90 minutes” at the cost of
   hiding the official end-of-hour queue should be treated as a methodology
   error, not a better calibration.

## Practical Rules Before Future Reruns

1. Read this note first.

2. Use appendix 1 matrix totals as the traffic basis.

3. Treat end-of-hour virtual queue as the primary blocked-traffic target for
   report comparison.

4. Keep a separate longer-horizon diagnostic if needed, but do not replace the
   official end-of-hour KPI with it.

5. Reject any rerun where V1 comes out materially better than base on the main
   congestion picture unless there is a concrete network-model reason that is
   stronger than “random variation”.

## Current Interpretation Gap

The current rerun established a better demand basis and a cleaner distinction
between blocked and inserted vehicles, but it still does not reproduce the
official qualitative outcome for scenario 4A / V1 / morning.

That means the remaining problem is not “how to read the report”.
It is model behavior or calibration.
