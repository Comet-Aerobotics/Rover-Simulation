"""Create a portable local-Jackal candidate from the canonical USD scene.

Run with Isaac Sim Python or a compatible usd-core installation. The output
must stay beside the source scene so the scene's existing relative asset paths
remain valid. The script never overwrites an existing scene.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from pxr import Sdf, Usd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "scenes/CAMERASYNCSSMOETIMES.usd"
DEFAULT_OUTPUT = ROOT / "scenes/CAMERASYNCSSMOETIMES_LOCAL_JACKAL_REBUILT_CANDIDATE.usd"
JACKAL_ASSET = ROOT / "assets/robots/jackal/ros2_jackal_PhysX_vlp16.usd"
WHEEL_JOINTS = (
    "front_left_wheel",
    "front_right_wheel",
    "rear_left_wheel",
    "rear_right_wheel",
)


def prepare(source: Path, output: Path) -> None:
    source = source.resolve()
    output = output.resolve()
    if source.parent != output.parent:
        raise ValueError("Output must be beside the source USD so relative asset paths remain valid")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing USD: {output}")
    if not JACKAL_ASSET.is_file():
        raise FileNotFoundError(f"Local Jackal asset is missing: {JACKAL_ASSET}")

    source_layer = Sdf.Layer.FindOrOpen(str(source))
    if not source_layer or not source_layer.Export(str(output)):
        raise RuntimeError(f"Could not copy source USD to {output}")

    layer = Sdf.Layer.FindOrOpen(str(output))
    jackal = layer.GetPrimAtPath("/jackal")
    if not jackal:
        raise ValueError("Source scene has no /jackal prim")
    relative_asset = os.path.relpath(JACKAL_ASSET, output.parent).replace("\\", "/")
    jackal.payloadList.ClearEdits()
    jackal.payloadList.Add(Sdf.Payload(relative_asset))

    for node_name, joint_name in zip(
        ("constant_token", "constant_token_01", "constant_token_02", "constant_token_03"),
        WHEEL_JOINTS,
    ):
        attr = layer.GetAttributeAtPath(f"/jackal/ActionGraph/{node_name}.inputs:value")
        if not attr:
            raise ValueError(f"Source scene is missing Action Graph token node {node_name}")
        attr.default = joint_name

    package = layer.GetPrimAtPath("/package")
    if package:
        for _, variant_set in package.variantSets.items():
            for _, variant in variant_set.variants.items():
                payloads = variant.primSpec.payloadList.GetAppliedItems()
                if payloads and all("lunarenvironment_" in payload.assetPath for payload in payloads):
                    variant.primSpec.payloadList.ClearEdits()

    layer.subLayerPaths = [path for path in layer.subLayerPaths if not path.startswith("anon:")]
    layer.Save()

    stage = Usd.Stage.Open(str(output), load=Usd.Stage.LoadAll)
    if not stage:
        raise RuntimeError(f"Candidate stage could not be opened: {output}")
    for joint_name in WHEEL_JOINTS:
        joint = stage.GetPrimAtPath(f"/jackal/base_link/{joint_name}")
        if not joint or joint.GetTypeName() != "PhysicsRevoluteJoint":
            raise RuntimeError(f"Candidate Jackal is missing revolute joint: {joint_name}")
    print(f"Created and structurally checked: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    prepare(args.source, args.output)
