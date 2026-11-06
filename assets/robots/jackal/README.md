# Jackal model assets

Two local OmniLRS USD variants have been copied from the preserved source: `ros2_jackal_PhysX_vlp16.usd` and `ros2_jackal_PhysX_vlp16_stereo.usd`. The package license is included as `LICENSE.txt`; provenance is listed in `docs/ownership-and-migration.md`.

The canonical `scenes/CAMERASYNCSSMOETIMES.usd` composes the local VLP-16 variant; its Action Graph tokens are mapped to the asset's four `front/rear_*_wheel` revolute joints and pass a structural audit. The shared VLP-16 asset has PhysX lidar `drawLines` and `drawPoints` enabled so its rays and hits appear in the viewport after a scene reload. `/scan` messages reached WSL in the open 55 kg candidate, and the user confirmed controller-driven motion there. Motion in the separate canonical scene and sustained contact still need acceptance. The stereo variant remains unselected because it adds a separate camera graph that is not part of the current sensor path.
