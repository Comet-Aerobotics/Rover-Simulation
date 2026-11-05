# Material ownership

Material dependencies referenced by the stage are primarily under `../environments/lunalab/Textures/`. This folder is reserved for project-owned materials. The Black Matte UI default in the local LunaLab wall layer now matches its active input and `BlackPaint.mdl` default. The SDK-provided `OmniPBR.mdl` resolves from Isaac Sim, not this project; remaining runtime dependencies are tracked in `../../docs/known-issues.md`.
