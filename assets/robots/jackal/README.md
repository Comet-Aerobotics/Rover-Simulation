# Jackal model assets

Two local OmniLRS USD variants have been copied from the preserved source: `ros2_jackal_PhysX_vlp16.usd` and `ros2_jackal_PhysX_vlp16_stereo.usd`. The package license is included as `LICENSE.txt`; provenance is listed in `docs/ownership-and-migration.md`.

The canonical scene still references NVIDIA's remote Isaac 5.0 `jackal.usd`. The VLP-16 variant is composed in `scenes/CAMERASYNCSSMOETIMES_LOCAL_JACKAL_CANDIDATE.usd`; its Action Graph tokens were remapped to the asset's four `front/rear_*_wheel` revolute joints and pass a structural audit. Isaac Sim visual, sensor, articulation-motion, and contact acceptance is still required before promoting that candidate to the default scene. The stereo variant remains unselected because it adds a separate camera graph that is not part of the current sensor path.
