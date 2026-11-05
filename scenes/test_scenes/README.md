# Scene candidates

The selected default scene, `../CAMERASYNCSSMOETIMES_LOCAL_JACKAL_CANDIDATE.usd`, is derived from the preserved baseline. It replaces the Isaac 5.0 remote Jackal payload with the local OmniLRS VLP-16 Jackal, maps the Action Graph to the model's four wheel joint names, removes the anonymous Replicator sublayer, and omits empty configuration payloads. It opened and rendered in Isaac Sim 6.1, and static wheel-terrain contact was measured. Powered motion, contact stability, and sensor behavior remain unverified. This folder is reserved for additional test-only USD stages.

The scene can be recreated with `isaac/diagnostics/prepare_local_jackal_scene.py` using Isaac Sim Python or compatible `usd-core`. It refuses to overwrite an existing USD and keeps the output beside the source scene so relative asset paths remain valid.

Open it for inspection with:

```powershell
.\scripts\windows\start_isaac_sim.ps1 -Scene scenes/CAMERASYNCSSMOETIMES_LOCAL_JACKAL_CANDIDATE.usd
```

Do not save automatic Isaac Sim node migrations over the selected scene until they have been reviewed. Save a separate copy if the stage needs adjustments. The original baseline remains preserved unchanged.
