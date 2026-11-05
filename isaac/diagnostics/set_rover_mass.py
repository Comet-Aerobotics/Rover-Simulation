"""Create a separate scene copy with the configured total Jackal mass."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "scenes/CAMERASYNCSSMOETIMES.usd"
DEFAULT_OUTPUT = ROOT / "scenes/in work/CAMERASYNCSSMOETIMES_55KG_CANDIDATE.usd"
BASE_LINK = "/jackal/base_link"
WHEEL_LINKS = (
    "/jackal/front_left_wheel_link",
    "/jackal/front_right_wheel_link",
    "/jackal/rear_left_wheel_link",
    "/jackal/rear_right_wheel_link",
)


def configured_total_mass() -> float:
    with (ROOT / "config/simulation.yaml").open("r", encoding="utf-8") as stream:
        return float(yaml.safe_load(stream)["robot"]["estimated_total_mass_kg"])


def create_candidate(source: Path, output: Path, total_mass_kg: float) -> Path:
    try:
        from pxr import Sdf, Usd, UsdPhysics
    except ImportError as exc:
        raise RuntimeError("Run with Isaac Sim Python or install the usd-audit extra") from exc

    source = source.resolve()
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {output}")
    if total_mass_kg <= 0:
        raise ValueError("Total rover mass must be positive")

    source_stage = Usd.Stage.Open(str(source))
    if not source_stage:
        raise RuntimeError(f"Could not open source scene: {source}")
    body_paths = (BASE_LINK, *WHEEL_LINKS)
    wheel_mass_total = 0.0
    for path in body_paths:
        prim = source_stage.GetPrimAtPath(path)
        if not prim or not prim.IsValid() or not prim.HasAPI(UsdPhysics.RigidBodyAPI):
            raise RuntimeError(f"Expected Jackal rigid body is missing: {path}")
        if not prim.HasAPI(UsdPhysics.MassAPI):
            raise RuntimeError(f"Expected Jackal rigid body has no MassAPI: {path}")
        if path != BASE_LINK:
            mass_attr = UsdPhysics.MassAPI(prim).GetMassAttr()
            if not mass_attr.HasAuthoredValueOpinion() or float(mass_attr.Get()) <= 0:
                raise RuntimeError(f"Wheel mass must be explicitly authored and positive: {path}")
            wheel_mass_total += float(mass_attr.Get())

    base_mass_kg = total_mass_kg - wheel_mass_total
    if base_mass_kg <= 0:
        raise ValueError("Wheel masses already meet or exceed the requested rover mass")

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    stage = Usd.Stage.Open(str(output))
    root_layer = stage.GetRootLayer()

    def relocate_asset_path(path: str) -> str:
        if path.startswith("../assets/"):
            return "../../assets/" + path[len("../assets/"):]
        return path

    def relocate_spec(path: Sdf.Path) -> None:
        spec = root_layer.GetObjectAtPath(path)
        if isinstance(spec, Sdf.PrimSpec):
            refs = spec.referenceList.explicitItems
            if refs:
                spec.referenceList.explicitItems = [
                    Sdf.Reference(
                        assetPath=relocate_asset_path(ref.assetPath),
                        primPath=ref.primPath,
                        layerOffset=ref.layerOffset,
                        customData=ref.customData,
                    )
                    for ref in refs
                ]
            payloads = spec.payloadList.explicitItems
            if payloads:
                spec.payloadList.explicitItems = [
                    Sdf.Payload(
                        assetPath=relocate_asset_path(payload.assetPath),
                        primPath=payload.primPath,
                        layerOffset=payload.layerOffset,
                    )
                    for payload in payloads
                ]
        elif isinstance(spec, Sdf.AttributeSpec) and isinstance(spec.default, Sdf.AssetPath):
            spec.default = Sdf.AssetPath(relocate_asset_path(spec.default.path))

    root_layer.Traverse(Sdf.Path.absoluteRootPath, relocate_spec)
    base = stage.GetPrimAtPath(BASE_LINK)
    UsdPhysics.MassAPI(base).GetMassAttr().Set(base_mass_kg)
    stage.GetRootLayer().Save()

    check_stage = Usd.Stage.Open(str(output))
    check_base_mass = float(UsdPhysics.MassAPI(check_stage.GetPrimAtPath(BASE_LINK)).GetMassAttr().Get())
    check_wheel_mass = sum(
        float(UsdPhysics.MassAPI(check_stage.GetPrimAtPath(path)).GetMassAttr().Get())
        for path in WHEEL_LINKS
    )
    actual_total = check_base_mass + check_wheel_mass
    if abs(actual_total - total_mass_kg) > 1e-5:
        raise RuntimeError(f"Saved mass sum is {actual_total:g} kg, expected {total_mass_kg:g} kg")

    print(f"Wrote mass candidate: {output}")
    print(f"Base link: {check_base_mass:.3f} kg; four wheels: {check_wheel_mass:.3f} kg; total: {actual_total:.3f} kg")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--total-mass-kg", type=float, default=configured_total_mass())
    args = parser.parse_args()
    create_candidate(args.source, args.output, args.total_mass_kg)
