from cadquery.occ_impl import shapes as occ_shapes
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
    angle=15.0,
    tolerance: float = 0.0,
):
    outer = cq.Workplane("XY").rect(width, depth).extrude(height)
    inner = (
        outer.faces("<Z")
        .workplane(thickness, True)
        .rect(width - thickness * 2, depth - thickness * 2)
        .extrude(height, combine=False)
    )
    box = outer.cut(inner)

    side_cut = (
        outer.faces(">X")
        .workplane()
        .moveTo(depth / 2, height)
        .lineTo(-depth / 2, height - depth * np.arctan(np.deg2rad(angle)))
        .lineTo(-depth / 2, height)
        .close()
        .extrude(-width, combine=False)
    )
    box = box.cut(side_cut)

    step_cut: occ_shapes.Face = box.faces(">Z").val()

    outer_wire = step_cut.outerWire()
    inner_wire = step_cut.innerWires()[0]

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
    box = box.cut(cq.Workplane(obj=cut_solid)).edges("<Z").fillet(fillet)

    return box.val()


def converter_container_with_lid(
    width: float,
    depth: float,
    height: float,
    thickness: float,
    ledge: float,
    fillet: float,
    angle: float = 15.0,
    tolerance: float = 0.2,
):
    width = 20 + thickness
    depth = 20 + thickness
    lower_height = height * 0.80 + thickness
    upper_height = height * 0.20 + thickness
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
        .rotate([0, 0, 0], [0, 0, 1], 180)
        .translate([width * 1.2, 0, 0])
    )

    return cq.Compound.makeCompound([lower, higher])
