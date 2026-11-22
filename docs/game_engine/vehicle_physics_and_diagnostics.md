# Vehicle physics, garage and diagnostic planning

Status: PROPOSED implementation design; creator direction recorded 2026-11-01. Planning only. No vehicle simulation, SDK integration or performance test has been implemented or run.

## Confirmed direction

Start with a prebuilt coolant skimmer. Discover a garage later for detailed assisted assembly, donor rebuilds, original chassis/body designs, repair, tuning and storage. Use hybrid engineering: recognizable vehicle mechanics combined with computer-inspired energy, cooling and control systems. Vehicles support an agent logistics fleet. Personal wrecks retain a recoverable core; some cargo and replaceable upgrades can be lost.

Vehicle quality is evaluated through connected component-level physics: weight, balance, power, cooling, handling and reliability. A generic quality score cannot override simulated behavior. Comprehensive game simulation is the target; numerical models and fidelity budgets below remain proposals rather than a claim to simulate every physical phenomenon exactly.

## Functional assembly

Every functional part has a stable instance ID, geometry, material/mass properties, mounting transform, compatibility, condition and relevant mechanical/electrical/thermal interfaces. The assembled graph records structural joints, torque paths, power wiring, coolant links, control signals and cargo attachment. Assisted placement handles alignment and repetitive fasteners while retaining the consequences of installed parts and connections.

Fixed attached parts contribute to an aggregate body and inertia; only genuinely articulated or detachable systems need separate physics bodies and constraints. Decorative fasteners need not each run a rigid-body simulation. Geometry remains authored/editable while its simulation representation is cooked and validated.

Blueprints, instantiated vehicles and installed component state remain separate. Editing a saved design creates a revision; existing vehicles do not silently receive new parts. Broken or unsupported connections produce inspectable build faults. Preview shows center of mass, wheel loads, available power, cooling paths, clearances and estimated operating envelope.

## Physical quality model

| System | Inputs and proposed simulation | Result observable by BS |
| --- | --- | --- |
| Weight | Installed dry mass, cargo, stored energy/fluid mass and their locations; recompute aggregate mass/inertia when configuration changes | Acceleration, stopping distance, suspension load, flotation and transport limits |
| Balance | Center of mass/inertia, wheelbase, track width, cargo position, support and flotation geometry | Unequal corner loads, steering behavior, pitching/rolling, tip risk and attitude |
| Power | Energy capacity, drive torque/speed curve, conversion losses, gearing/differentials where installed, wiring limits and thermal derating | Pulling ability, acceleration, speed under load, endurance, voltage/current and power limits |
| Cooling | Heat generation, component thermal capacity, connection/flow resistance, pump behavior, radiator exchange, airflow and ambient/coolant temperature | Warmup, sustained performance, throttling, overheating, leakage and recovery |
| Handling | Suspension spring/damping/travel, tire grip/slip, steering geometry, brake distribution, surface state and aerodynamic forces | Grip, understeer/oversteer, wheelspin, braking, bottoming out and response to bumps |
| Reliability | Part condition, accumulated thermal/mechanical/electrical stress, joint loads, contamination and maintenance | Progressive wear, degraded output, looseness, damaged connections and explainable failures |

Use explicit units and conserve mass/energy within each declared model's approximation. Coolant capacity, boost energy and heat must have costs; cosmetic effects cannot create free thrust or cooling. Fictional magnetic adhesion has finite force and power draw, so vertical travel can fail when overloaded or unpowered.

Start with rigid-body mechanics, supported wheel/suspension contact models and lumped thermal/electrical networks. Skimmer buoyancy, drag, immersion and propulsion respond to authored current/pressure fields. Cable rigs have their own contact/attachment constraints. Higher-fidelity fluid/structural deformation extensions require measured need; a full computational-fluid or deformable-body solver is not implied by the initial model.

Jolt's vehicle sources expose suspension/traction infrastructure and a wheeled controller with engine, transmission and differential models. They are a candidate mechanical foundation, not a complete coolant, electrical, boat or failure simulation. AI-BS must integrate and validate those additional systems. [VehicleConstraint](https://github.com/jrouwe/JoltPhysics/blob/master/Jolt/Physics/Vehicle/VehicleConstraint.h), [WheeledVehicleController](https://github.com/jrouwe/JoltPhysics/blob/master/Jolt/Physics/Vehicle/WheeledVehicleController.h).

## Coupling and simulation ownership

The fixed-step simulation owner updates controls, power/thermal constraints, drive forces, physics and telemetry in a defined order. Select step/substep rates through handling/stability profiling before locking release tuning; the existing 60 Hz engine step is the starting integration contract, not proof that every vehicle model is stable at that rate.

Vehicle changes publish validated mass/collision/network revisions at safe boundaries. Agent and player drivers use the same underlying vehicle capabilities. Distant logistics use a declared aggregate model instead of simulating every tire or coolant sample; returning to detailed simulation reconciles cargo, energy, condition and route events without inventing free recovery.

Campaign-level chance influences encounters and uncertain events. Vehicle failures derive from actual condition and stress; any probabilistic wear event has explicit causes and records its outcome. It cannot silently turn a healthy vehicle into a random failure merely to vary the story.

## Diagnostic garage and handheld

The garage provides scales/corner-load pads, a power/drive test stand, coolant flow/pressure/temperature instrumentation, electrical inspection, alignment/suspension tools and a repeatable handling course. Tools unlock deeper observation and assistance, while the installed physical systems remain consistent across assistance levels.

The handheld shows installed topology, observed faults, time-series measurements, part condition, current limits and test results. A symptom is separate from a confirmed cause. Unknown measurements remain unknown until the relevant sensor/test is available. Estimates are labeled and tied to the current configuration and environment.

Example diagnosis: a vehicle accelerates normally cold, loses output after sustained boost, and shows rising controller temperature with low coolant flow. BS inspects pump power, restrictive tubing and radiator exposure, modifies the actual faulty setup, then repeats the same test. Confirmation requires the measurements and sustained behavior to improve.

Adam interprets available evidence and remembers previous tests. New proposed game dialogue: "It holds when it's cold. Let's watch what changes under load." He can suggest a test or compare configurations without inventing sensor readings or claiming a repair succeeded before retest. His expression remains grounded in the creator's remembered warmth and character.

## Quality report and progression

Use a task-specific report rather than one universal ranking. Record configuration/version, cargo, environment, assistance, test route and measurements. Report acceleration, braking, stability, energy use, thermal headroom, durability and maintenance cost separately. A slow heavy hauler can be an excellent logistics vehicle; a fast skimmer can be unsuitable for towing.

Upgrades alter parameters and topology: a larger power source adds mass and heat, armor increases protection and load, extra cooling needs space/power, and cargo placement changes balance. New materials/modules expand possibilities while retaining these tradeoffs. Diagnostics lead to better construction rather than only higher tier numbers.

## Persistence and recovery

Save vehicle IDs, blueprint revision, installed parts/condition, joints/connections, damage, cargo, energy, thermal state, location and recovery state. Parked garage storage uses a declared cooldown policy with elapsed active-play time; loading must not reset heat, repair damage or regenerate cargo. Campaign time pauses when the game is paused/closed as selected.

Personal vehicle destruction creates a recoverable-core record. Tow/retrieval jobs require reachable routes and suitable agent equipment. Define how destroyed non-core modules and cargo are salvaged; recovery cannot duplicate the original vehicle. Placement, repair, salvage and inventory transfers use idempotent recorded operations.

## Future acceptance scenarios

- Add identical mass at different positions: measured center of mass/load distribution and handling change appropriately.
- Repeat a controlled braking/handling test before/after suspension or brake changes; compare recorded configuration-specific results.
- Block or disconnect a cooling path: heat rises under load and output degrades through the declared model; restore the path and verify the retest.
- Compare towing and speed roles with the same cargo and route; preserve meaningful tradeoffs.
- Change cargo during travel: recompute relevant physics properties safely without unstable impulses or duplicate items.
- Exceed adhesion/support/energy limits: produce physically explained loss of capability and visible feedback.
- Save/reload a hot, damaged, loaded vehicle: preserve its state and pending recovery without free repair/cooling or duplicate cargo.
- Transfer a vehicle between detailed player control and aggregate agent logistics: retain consistent resources and condition.
- Recover a wrecked core through an agent mission and rebuild once, retaining loss history.
- Disable model inference: diagnostics remain usable; Adam retains authored evidence-based assistance.

These are proposed future tests, not results. The next planning step is to specify starter-skimmer components, the garage test route, part parameter ranges and fidelity/performance budgets before implementing any model.
