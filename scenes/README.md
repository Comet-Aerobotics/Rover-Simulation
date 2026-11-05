# scenes/

Isaac Sim USD stages. `CAMERASYNCSSMOETIMES.usd` is the canonical scene, with the local VLP-16 Jackal, corrected DEM orientation, and colliders on the placed lunar rocks. Its visual appearance was reviewed in Isaac Sim; powered rover motion and terrain contact still need runtime checks. The stage USD owns its robot and camera Action Graphs.

The `in work/` folder holds non-canonical scene experiments. Its `CAMERASYNCSSMOETIMES_55KG_CANDIDATE.usd` sets the composed Jackal mass to 55 kg while keeping the four authored wheel masses. Use it to compare rover settling and bounce behavior before changing the canonical scene.

## Contents

- CAMERASYNCSSMOETIMES.usd
- in work/ (non-canonical scene experiments)
- test_scenes/

## Simulation relevance
This folder supports the selected LunaLab/Jackal simulation; the purpose above describes its specific role and ownership boundary.
