# Studio concurrency read-only baseline

T06 first measurement, source172; no production code or scheduler settings changed.
Actual EngineBus default cap8, Python3.12.14, Qt/PyQt6.11.0. Workload:64 synthetic
read-only tasks, each parsing an immutable engine.py snapshot8times. No model,
network, database, user document, process primitive or existing test was used or
changed. This is a QCoreApplication event-loop measurement, not mounted-widget
or representative inference/vector performance qualification.

Five-ms timer observations: idle201samples/p95 5.524ms/max5.899ms; loaded11samples/
p95 510.612ms/max607.496ms. Loaded elapsed1470.943ms; task duration44.442–304.063ms.
Observed RSS peak43,204,608bytes. Eight worker threads observed; all64 results
arrived on the GUI thread; pool join passed, shutdown0.020ms. Sparse timer
sampling cannot prove exact queue or instantaneous resource peaks. These are
observed timer intervals, not independently measured input latency or a universal
performance guarantee. One local run is not a repeatability study.

Evidence: backups/studio_concurrency_baseline_20261115_v01/result.json and measure.py.
Engine SHA256:6a87fab20d1a2e535478fc2dddf85678e23b18dae45497436894287bf6f36fce.

Disposition: CPU-heavy pure-Python parsing on the pool does not meet the proposed
responsive-UI aim under this synthetic burst. GIL contention is a plausible
explanation, not an established sole cause. Do not raise thread caps or invent
sub-millisecond claims. Next compare this same immutable parsing workload using
existing owned process batching, with bounded jobs/output and actual drain;
then select an actual harmless caller and measured acceptance budget before
migration. Existing EngineBus/JobObject/cancellation/storage primitives stay
frozen. General task IDs/progress/workspace fairness remain proposed, not applied.
Full ten-goal/six-addition goal ACTIVE/incomplete.

Four-member engineering Drive archive downloaded byte-exact and all member
hashes verified. Receipt: backups/studio_concurrency_baseline_20261115_v01/
engineering/drive-verified.json; sharing unchanged and private records excluded.
