# Third-party assets and notices

- LunaLab/OmniLRS environment layers, textures, and the two local Jackal USD candidates originate from the preserved OmniLRS source snapshot. The repository license/notice is included at `assets/environments/lunalab/LICENSE.txt` and `assets/robots/jackal/LICENSE.txt`.
- `USD_Assets/lunalab/Lunalab_walls_textured.usd` has one project-local metadata correction: the Black Matte normal-map UI default now matches the active material value and its `BlackPaint.mdl` default (`Textures/BlackPaint/BlackPaint_nor_dx_4k.exr`). The original source remains unchanged in the preserved OmniLRS snapshot.
- The canonical scene also references Isaac Sim's built-in `OmniPBR.mdl` and a remote NVIDIA Jackal USD. Those are supplied by/hosted through NVIDIA and are not included as local files.
- `DM9098Pro_enclosure.usd` came from the user's Downloads directory and is included as a project asset.
