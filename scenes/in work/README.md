# scenes/in work/

This folder holds USD scene experiments that are not the canonical simulation. The main scene remains `../CAMERASYNCSSMOETIMES.usd`.

## Current scene

- `CAMERASYNCSSMOETIMES_55KG_CANDIDATE.usd` applies a 55 kg total rover mass for physics comparison. It keeps the four wheel masses from the Jackal asset and assigns the remainder to `/jackal/base_link`.

The candidate keeps its referenced assets working from this subfolder by using paths relative to the repository root. It is not the launcher default. Compare rover settling and bounce in Isaac Sim before promoting a physics change to the canonical scene.
