# Jackal model assets

Two local OmniLRS USD variants have been copied from the preserved source: `ros2_jackal_PhysX_vlp16.usd` and `ros2_jackal_PhysX_vlp16_stereo.usd`. The package license is included as `LICENSE.txt`; provenance is listed in `docs/ownership-and-migration.md`.

The canonical `scenes/CAMERASYNCSSMOETIMES.usd` composes the local VLP-16 variant; its Action Graph tokens are mapped to the asset's four `front/rear_*_wheel` revolute joints and pass a structural audit. The canonical scene was visually reviewed in Isaac Sim. Sensor output, powered articulation motion, and sustained contact still need acceptance. The stereo variant remains unselected because it adds a separate camera graph that is not part of the current sensor path.
