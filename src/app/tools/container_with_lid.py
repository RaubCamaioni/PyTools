# cadquery

from cadquery.occ_impl import shapes as occ_shapes
from pathlib import Path
import cadquery as cq
import numpy as np


def loft_faces(f1: occ_shapes.Face, f2: occ_shapes.Face) -> occ_shapes.Solid:
    solid = cq.Solid.makeLoft([f1.outerWire(), f2.outerWire()])

    for inner1, inner2 in zip(f1.innerWires(), f2.innerWires()):
        solid_inner = cq.Solid.makeLoft([inner1, inner2])
        solid = solid.cut(solid_inner)

    return solid


def container(
    width,
    depth,
    height,
    thickness,
    ledge,
    exterior_ledge,
    fillet,
    angle,
    tolerance,
):
    throw = depth * np.arctan(np.deg2rad(angle))
    height = height + throw / 2

    outer = cq.Workplane("XY").rect(width, depth).extrude(height)
    inner = (
        cq.Workplane("XY")
        .rect(
            width - thickness * 2,
            depth - thickness * 2,
        )
        .extrude(height)
        .translate([0, 0, thickness])
    )
    box = outer.cut(inner)

    side_cut = (
        outer.faces(">X")
        .workplane()
        .moveTo(depth / 2, height)
        .lineTo(-depth / 2, height - throw)
        .lineTo(-depth / 2, height)
        .close()
        .extrude(-width, combine=False)
    )
    box = box.cut(side_cut)

    step_cut = box.faces(">Z").val()
    outer_wire = step_cut.outerWire()
    inner_wire: cq.Wire = step_cut.innerWires()[0]

    if exterior_ledge:
        tolerance_thickness = thickness - tolerance
    else:
        tolerance_thickness = thickness + tolerance

    offset_wire = inner_wire.offset2D(tolerance_thickness / 2)[0]

    if exterior_ledge:
        cut_face = occ_shapes.Face.makeFromWires(outer_wire, [offset_wire])
    else:
        cut_face = occ_shapes.Face.makeFromWires(offset_wire, [inner_wire])

    cut_solid = loft_faces(cut_face, cut_face.translate([0, 0, -ledge]))
    box = box.cut(cq.Workplane(obj=cut_solid)).edges("|Z").fillet(fillet)

    # fillet bottom (harder to 3d print)
    # box = box.cut(cq.Workplane(obj=cut_solid)).edges("<Z").fillet(fillet)

    # fillet inner edge
    rad = np.deg2rad(angle)
    normal = cq.Vector(0, -np.sin(rad), np.cos(rad))
    box = (
        box.cut(cq.Workplane(obj=cut_solid))
        .faces(cq.selectors.ParallelDirSelector(normal, tolerance=0.01))
        .faces(cq.selectors.AreaNthSelector(0))
        .edges(cq.selectors.LengthNthSelector(0))
        .fillet(thickness / 4)
    )

    # add retention circle
    edge: cq.Edge
    for edge in offset_wire.edges():
        if not edge.geomType() == "LINE":
            continue

        tangent: cq.Vector = edge.Center() - offset_wire.Center()
        tangent.z = 0
        x_dir = edge.positionAt(0.45) - edge.positionAt(0.55)

        # if exterior_ledge:
        tangent *= -1
        x_dir *= -1

        plane = cq.Plane(
            origin=edge.Center(),
            xDir=x_dir,
            normal=tangent,
        )

        a = thickness / 4
        b = thickness / 4

        arc = (
            cq.Workplane(plane)
            .moveTo(0, -b)
            .ellipseArc(a, b, -90, 90, startAtCurrent=True)
            .moveTo(0, b)
            .close()
        )

        # path = cq.Workplane(plane).moveTo(-0.5, 0).lineTo(0.5, 0)
        # ellip_slit = arc.sweep(path)

        ellip_edge = arc.revolve(360, (0, 0, 0), (0, 1, 0)).translate(
            plane.yDir * ledge / 2
        )

        if exterior_ledge:
            box = box.union(ellip_edge)
        else:
            box = box.cut(ellip_edge)

    return box.val()


def container_with_lid(
    width: float = 20,
    depth: float = 20,
    height: float = 20,
    thickness: float = 2.5,
    ledge: float = 5,
    fillet: float = 3,
    angle: float = 5.0,
    tolerance: float = 0.1,
    top_ratio: float = 0.30,
) -> Path:
    width = width + thickness * 2
    depth = depth + thickness * 2
    height = height + thickness * 2 + ledge
    lower_height = height * 0.70
    upper_height = height * 0.30
    ledge = ledge
    fillet = fillet
    angle = angle
    tolerance = tolerance

    lower = container(
        width,
        depth,
        lower_height,
        thickness,
        ledge,
        True,
        fillet,
        angle,
        tolerance,
    )

    higher = (
        container(
            width,
            depth,
            upper_height,
            thickness,
            ledge,
            False,
            fillet,
            angle,
            tolerance,
        )
        .rotate([0, 0, 0], [0, 0, 1], 0)
        .translate([width * 1.2, 0, 0])
    )

    compound = cq.Compound.makeCompound([lower, higher])
    compound_path = "container_with_lid.stl"
    compound.exportStl(compound_path)

    return Path(compound_path)
