# Klein Nut Driver Clip Test Strip
# Revision 1.0
#
# Rebuilt clip geometry:
# - true curved shaft pocket
# - tapered lead-in
# - straight vertical stems from each curved arm down into the base
# - stems overlap the base slightly so the Join extrusion produces one body
#
# Nominal Klein shaft diameters:
#   0.2500, 0.3125, 0.3750, 0.4375, 0.5000 inch

import adsk.core
import adsk.fusion
import traceback
import math


SCRIPT_NAME = 'Klein Nut Driver Clip Test Strip Rev 1.0'
BODY_NAME = 'Klein Nut Driver Clip Test Strip Rev 1.0'

INCH_TO_CM = 2.54

SHAFT_DIAMETERS = [0.2500, 0.3125, 0.3750, 0.4375, 0.5000]

# Base dimensions, inches.
STRIP_WIDTH = 6.50
STRIP_DEPTH = 1.50
STRIP_THICKNESS = 0.20
STRIP_CORNER_RADIUS = 0.20

# Clip dimensions, inches.
CLIP_DEPTH = 0.65
POCKET_CLEARANCE = 0.012
ARM_WALL = 0.095
THROAT_INTERFERENCE = 0.050

# Straight support section.
STEM_HEIGHT = 0.350
STEM_OVERLAP_INTO_BASE = 0.030

# Curved pocket and entry geometry.
POCKET_LOWER_ANGLE = 225.0
POCKET_UPPER_ANGLE = 120.0
ARC_SEGMENTS = 12
LEAD_HEIGHT = 0.180
LEAD_FLARE = 0.080


def cm(value_in_inches):
    return value_in_inches * INCH_TO_CM


def delete_existing_generated_bodies(root_component):
    generated_names = {
        'Klein Nut Driver Clip Test Strip',
        'Klein Nut Driver Clip Test Strip Rev 0.2',
        'Klein Nut Driver Clip Test Strip Rev 0.3',
        'Klein Nut Driver Clip Test Strip Rev 0.4',
        BODY_NAME,
    }

    for index in range(root_component.bRepBodies.count - 1, -1, -1):
        body = root_component.bRepBodies.item(index)
        if body.name in generated_names:
            body.deleteMe()


def add_closed_polygon(sketch_lines, points):
    fusion_points = [
        adsk.core.Point3D.create(cm(x), cm(z), 0)
        for x, z in points
    ]

    for index in range(len(fusion_points)):
        sketch_lines.addByTwoPoints(
            fusion_points[index],
            fusion_points[(index + 1) % len(fusion_points)]
        )


def arc_points(center_x, center_z, radius,
               start_degrees, end_degrees, segments):
    points = []

    for index in range(segments + 1):
        fraction = index / float(segments)
        angle_degrees = (
            start_degrees +
            (end_degrees - start_degrees) * fraction
        )
        angle = math.radians(angle_degrees)

        points.append((
            center_x + radius * math.cos(angle),
            center_z + radius * math.sin(angle)
        ))

    return points


def create_base_strip(root_component):
    sketch = root_component.sketches.add(
        root_component.xYConstructionPlane
    )
    sketch.name = 'Clip Test Strip Base Footprint'

    half_width = cm(STRIP_WIDTH / 2.0)
    half_depth = cm(STRIP_DEPTH / 2.0)

    sketch.sketchCurves.sketchLines.addTwoPointRectangle(
        adsk.core.Point3D.create(-half_width, -half_depth, 0),
        adsk.core.Point3D.create(half_width, half_depth, 0)
    )

    if sketch.profiles.count != 1:
        raise RuntimeError(
            'Expected one base profile; found {}.'
            .format(sketch.profiles.count)
        )

    extrudes = root_component.features.extrudeFeatures
    extrude_input = extrudes.createInput(
        sketch.profiles.item(0),
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    extrude_input.setDistanceExtent(
        False,
        adsk.core.ValueInput.createByString(
            '{:.4f} in'.format(STRIP_THICKNESS)
        )
    )

    extrusion = extrudes.add(extrude_input)
    extrusion.name = 'Clip Test Strip Base Extrusion'

    body = extrusion.bodies.item(0)
    body.name = BODY_NAME

    vertical_edges = adsk.core.ObjectCollection.create()
    tolerance = 0.0001

    for edge in body.edges:
        start_vertex = edge.startVertex
        end_vertex = edge.endVertex

        if not start_vertex or not end_vertex:
            continue

        start = start_vertex.geometry
        end = end_vertex.geometry

        if (
            abs(start.x - end.x) < tolerance and
            abs(start.y - end.y) < tolerance and
            abs(start.z - end.z) > tolerance
        ):
            vertical_edges.add(edge)

    if vertical_edges.count == 4:
        fillets = root_component.features.filletFeatures
        fillet_input = fillets.createInput()
        fillet_input.edgeSetInputs.addConstantRadiusEdgeSet(
            vertical_edges,
            adsk.core.ValueInput.createByString(
                '{:.4f} in'.format(STRIP_CORNER_RADIUS)
            ),
            True
        )
        fillets.add(fillet_input)

    return body


def create_left_arm_points(center_x, shaft_diameter):
    pocket_radius = (shaft_diameter + POCKET_CLEARANCE) / 2.0
    outer_radius = pocket_radius + ARM_WALL

    stem_bottom_z = STRIP_THICKNESS - STEM_OVERLAP_INTO_BASE

    # Place the lower arc connection exactly STEM_HEIGHT above the base.
    lower_angle = math.radians(POCKET_LOWER_ANGLE)
    pocket_center_z = (
        stem_bottom_z +
        STEM_HEIGHT -
        pocket_radius * math.sin(lower_angle)
    )

    inner_arc = arc_points(
        center_x,
        pocket_center_z,
        pocket_radius,
        POCKET_LOWER_ANGLE,
        POCKET_UPPER_ANGLE,
        ARC_SEGMENTS
    )

    outer_arc = arc_points(
        center_x,
        pocket_center_z,
        outer_radius,
        POCKET_UPPER_ANGLE,
        POCKET_LOWER_ANGLE,
        ARC_SEGMENTS
    )

    inner_lower = inner_arc[0]
    inner_upper = inner_arc[-1]
    outer_upper = outer_arc[0]
    outer_lower = outer_arc[-1]

    throat_width = max(
        shaft_diameter - THROAT_INTERFERENCE,
        shaft_diameter * 0.78
    )
    throat_x = center_x - throat_width / 2.0

    lead_top_z = max(inner_upper[1], outer_upper[1]) + LEAD_HEIGHT

    # Exact profile order:
    # 1. inner stem bottom
    # 2. straight vertical inner stem
    # 3. curved inner pocket
    # 4. retention throat and lead-in
    # 5. curved outer wall
    # 6. straight vertical outer stem back to base
    points = [
        (inner_lower[0], stem_bottom_z),
        inner_lower,
    ]

    points.extend(inner_arc[1:])

    points.extend([
        (throat_x, lead_top_z - LEAD_HEIGHT * 0.45),
        (throat_x - LEAD_FLARE, lead_top_z),
        (throat_x - LEAD_FLARE - ARM_WALL, lead_top_z),
        outer_upper,
    ])

    points.extend(outer_arc[1:])

    points.extend([
        (outer_lower[0], stem_bottom_z),
    ])

    return points


def mirror_points(points, center_x):
    return [
        (2.0 * center_x - x, z)
        for x, z in reversed(points)
    ]


def create_clip_arms(root_component):
    planes = root_component.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByOffset(
        root_component.xZConstructionPlane,
        adsk.core.ValueInput.createByString(
            '{:.4f} in'.format(-CLIP_DEPTH / 2.0)
        )
    )

    clip_plane = planes.add(plane_input)
    clip_plane.name = 'Clip Profile Plane'

    sketch = root_component.sketches.add(clip_plane)
    sketch.name = 'Five Snap Clips With Straight Stems'
    lines = sketch.sketchCurves.sketchLines

    station_spacing = STRIP_WIDTH / len(SHAFT_DIAMETERS)
    first_x = -STRIP_WIDTH / 2.0 + station_spacing / 2.0

    for station, shaft_diameter in enumerate(SHAFT_DIAMETERS):
        center_x = first_x + station * station_spacing

        left_points = create_left_arm_points(
            center_x,
            shaft_diameter
        )
        right_points = mirror_points(left_points, center_x)

        add_closed_polygon(lines, left_points)
        add_closed_polygon(lines, right_points)

    expected_profiles = len(SHAFT_DIAMETERS) * 2

    if sketch.profiles.count != expected_profiles:
        raise RuntimeError(
            'Expected {} arm profiles; found {}.'
            .format(expected_profiles, sketch.profiles.count)
        )

    profile_collection = adsk.core.ObjectCollection.create()

    for index in range(sketch.profiles.count):
        profile_collection.add(sketch.profiles.item(index))

    extrudes = root_component.features.extrudeFeatures
    extrude_input = extrudes.createInput(
        profile_collection,
        adsk.fusion.FeatureOperations.JoinFeatureOperation
    )
    extrude_input.setDistanceExtent(
        False,
        adsk.core.ValueInput.createByString(
            '{:.4f} in'.format(CLIP_DEPTH)
        )
    )

    extrusion = extrudes.add(extrude_input)
    extrusion.name = 'Five Snap Clips With Straight Stems'


def run(context):
    app = None
    ui = None

    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        design = adsk.fusion.Design.cast(app.activeProduct)

        if not design:
            app.documents.add(
                adsk.core.DocumentTypes.FusionDesignDocumentType
            )
            design = adsk.fusion.Design.cast(app.activeProduct)

        if not design:
            raise RuntimeError(
                'Unable to create or access a Fusion design.'
            )

        root_component = design.rootComponent

        delete_existing_generated_bodies(root_component)
        create_base_strip(root_component)
        create_clip_arms(root_component)

        app.activeViewport.fit()

        ui.messageBox(
            'Revision 1.0 clip test strip created.\n\n'
            'The curved snap arms now have true straight vertical stems\n'
            'that extend down into and join the base.\n\n'
            'Nominal diameters:\n'
            '0.2500, 0.3125, 0.3750, 0.4375, 0.5000 in',
            SCRIPT_NAME
        )

    except:
        if ui:
            ui.messageBox(
                'The script failed:\n\n{}'.format(
                    traceback.format_exc()
                ),
                SCRIPT_NAME
            )
