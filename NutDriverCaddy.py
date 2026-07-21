# Klein Nut Driver Caddy - Base Plate and Handle
# Revision 1.3

import adsk.core
import adsk.fusion
import math
import traceback


SCRIPT_NAME = 'Klein Nut Driver Caddy - Base Plate and Handle'


def get_or_create_parameter(
    design,
    name,
    expression,
    units,
    comment
):
    user_params = design.userParameters
    parameter = user_params.itemByName(name)

    if parameter:
        parameter.expression = expression
        parameter.comment = comment
        return parameter

    return user_params.add(
        name,
        adsk.core.ValueInput.createByString(expression),
        units,
        comment
    )


def delete_existing_caddy_body(root_component):
    for index in range(
        root_component.bRepBodies.count - 1,
        -1,
        -1
    ):
        body = root_component.bRepBodies.item(index)

        if body.name == 'Klein Nut Driver Caddy Base Plate':
            body.deleteMe()


def find_top_planar_face(body):
    top_face = None
    highest_z = -999999.0

    for face in body.faces:
        geometry = face.geometry

        if geometry.objectType != adsk.core.Plane.classType():
            continue

        normal = geometry.normal

        if normal.z < 0.9:
            continue

        point = face.pointOnFace

        if point.z > highest_z:
            highest_z = point.z
            top_face = face

    if not top_face:
        raise RuntimeError(
            'Could not locate the top surface of the plate.'
        )

    return top_face


def create_base_plate(root_component, design):
    # ------------------------------------------------------------
    # User parameters
    # ------------------------------------------------------------
    get_or_create_parameter(
        design,
        'BoardWidth',
        '8.000 in',
        'in',
        'Overall base-plate width.'
    )

    get_or_create_parameter(
        design,
        'BoardHeight',
        '9.500 in',
        'in',
        'Overall base-plate height.'
    )

    get_or_create_parameter(
        design,
        'BoardThickness',
        '0.375 in',
        'in',
        'Base-plate thickness.'
    )

    get_or_create_parameter(
        design,
        'CornerRadius',
        '0.500 in',
        'in',
        'Radius of the four outside corners.'
    )

    get_or_create_parameter(
        design,
        'HandleWidth',
        '4.000 in',
        'in',
        'Overall handle-opening width.'
    )

    get_or_create_parameter(
        design,
        'HandleHeight',
        '2.000 in',
        'in',
        'Overall handle-opening height.'
    )

    get_or_create_parameter(
        design,
        'HandleTopMargin',
        '0.500 in',
        'in',
        'Distance from board top edge to handle opening.'
    )

    delete_existing_caddy_body(root_component)

    # ------------------------------------------------------------
    # Create centered rectangular base sketch
    # ------------------------------------------------------------
    sketch = root_component.sketches.add(
        root_component.xYConstructionPlane
    )

    sketch.name = 'Klein Caddy Base Plate Footprint'

    lines = sketch.sketchCurves.sketchLines

    center = adsk.core.Point3D.create(0, 0, 0)

    # Temporary half dimensions:
    # 4.000 inches x 4.750 inches, converted to cm
    corner = adsk.core.Point3D.create(
        10.16,
        12.065,
        0
    )

    rectangle_lines = lines.addCenterPointRectangle(
        center,
        corner
    )

    horizontal_line = None
    vertical_line = None

    for line in rectangle_lines:
        start = line.startSketchPoint.geometry
        end = line.endSketchPoint.geometry

        dx = abs(end.x - start.x)
        dy = abs(end.y - start.y)

        if dx > dy and horizontal_line is None:
            horizontal_line = line

        elif dy > dx and vertical_line is None:
            vertical_line = line

    if not horizontal_line or not vertical_line:
        raise RuntimeError(
            'Could not identify rectangle width and height lines.'
        )

    dimensions = sketch.sketchDimensions

    width_dimension = dimensions.addDistanceDimension(
        horizontal_line.startSketchPoint,
        horizontal_line.endSketchPoint,
        adsk.fusion.DimensionOrientations
        .HorizontalDimensionOrientation,
        adsk.core.Point3D.create(0, -13.5, 0)
    )

    width_dimension.parameter.expression = 'BoardWidth'

    height_dimension = dimensions.addDistanceDimension(
        vertical_line.startSketchPoint,
        vertical_line.endSketchPoint,
        adsk.fusion.DimensionOrientations
        .VerticalDimensionOrientation,
        adsk.core.Point3D.create(-11.5, 0, 0)
    )

    height_dimension.parameter.expression = 'BoardHeight'

    if sketch.profiles.count != 1:
        raise RuntimeError(
            'Expected one closed base profile, found {}.'.format(
                sketch.profiles.count
            )
        )

    # ------------------------------------------------------------
    # Extrude the base plate
    # ------------------------------------------------------------
    extrudes = root_component.features.extrudeFeatures

    extrude_input = extrudes.createInput(
        sketch.profiles.item(0),
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )

    extrude_input.setDistanceExtent(
        False,
        adsk.core.ValueInput.createByString(
            'BoardThickness'
        )
    )

    extrusion = extrudes.add(extrude_input)
    extrusion.name = 'Klein Caddy Base Plate Extrusion'

    body = extrusion.bodies.item(0)
    body.name = 'Klein Nut Driver Caddy Base Plate'

    # ------------------------------------------------------------
    # Round the four outside corners
    # ------------------------------------------------------------
    vertical_edges = adsk.core.ObjectCollection.create()
    tolerance = 0.0001

    for edge in body.edges:
        start_vertex = edge.startVertex
        end_vertex = edge.endVertex

        if not start_vertex or not end_vertex:
            continue

        start = start_vertex.geometry
        end = end_vertex.geometry

        same_x = abs(start.x - end.x) < tolerance
        same_y = abs(start.y - end.y) < tolerance
        different_z = abs(start.z - end.z) > tolerance

        if same_x and same_y and different_z:
            vertical_edges.add(edge)

    if vertical_edges.count != 4:
        raise RuntimeError(
            'Expected four outside vertical edges, found {}.'.format(
                vertical_edges.count
            )
        )

    fillets = root_component.features.filletFeatures
    fillet_input = fillets.createInput()

    fillet_input.edgeSetInputs.addConstantRadiusEdgeSet(
        vertical_edges,
        adsk.core.ValueInput.createByString(
            'CornerRadius'
        ),
        True
    )

    corner_fillet = fillets.add(fillet_input)
    corner_fillet.name = 'Klein Caddy Outside Corner Radius'

    # ------------------------------------------------------------
    # Find the top face after the outside corner fillet
    # ------------------------------------------------------------
    top_face = find_top_planar_face(body)

    # ------------------------------------------------------------
    # Create the rounded handle opening
    #
    # Fusion internally uses centimeters.
    #
    # Board top edge:        4.750 in
    # Handle top margin:     0.500 in
    # Handle top edge:       4.250 in
    # Handle height:         2.000 in
    # Handle center Y:       3.250 in
    # Handle radius:         1.000 in
    # Arc centers:          -1.000 and +1.000 in
    # ------------------------------------------------------------
    handle_sketch = root_component.sketches.add(top_face)
    handle_sketch.name = 'Handle Opening'

    handle_lines = handle_sketch.sketchCurves.sketchLines
    handle_arcs = handle_sketch.sketchCurves.sketchArcs

    inch = 2.54

    radius = 1.0 * inch
    center_y = 3.25 * inch
    left_center_x = -1.0 * inch
    right_center_x = 1.0 * inch

    top_y = center_y + radius
    bottom_y = center_y - radius
    left_outer_x = left_center_x - radius
    right_outer_x = right_center_x + radius

    top_left = adsk.core.Point3D.create(
        left_center_x,
        top_y,
        0
    )

    top_right = adsk.core.Point3D.create(
        right_center_x,
        top_y,
        0
    )

    bottom_right = adsk.core.Point3D.create(
        right_center_x,
        bottom_y,
        0
    )

    bottom_left = adsk.core.Point3D.create(
        left_center_x,
        bottom_y,
        0
    )

    right_middle = adsk.core.Point3D.create(
        right_outer_x,
        center_y,
        0
    )

    left_middle = adsk.core.Point3D.create(
        left_outer_x,
        center_y,
        0
    )

    handle_lines.addByTwoPoints(
        top_left,
        top_right
    )

    handle_arcs.addByThreePoints(
        top_right,
        right_middle,
        bottom_right
    )

    handle_lines.addByTwoPoints(
        bottom_right,
        bottom_left
    )

    handle_arcs.addByThreePoints(
        bottom_left,
        left_middle,
        top_left
    )

    if handle_sketch.profiles.count != 1:
        raise RuntimeError(
            'Expected one closed handle profile, found {}.'.format(
                handle_sketch.profiles.count
            )
        )

    # ------------------------------------------------------------
    # Cut the handle through the plate
    # ------------------------------------------------------------
    handle_cut_input = extrudes.createInput(
        handle_sketch.profiles.item(0),
        adsk.fusion.FeatureOperations.CutFeatureOperation
    )

    handle_cut_input.setDistanceExtent(
        False,
        adsk.core.ValueInput.createByString(
            '-BoardThickness'
        )
    )

    handle_cut = extrudes.add(handle_cut_input)
    handle_cut.name = 'Handle Opening Cut'

    adsk.core.Application.get().activeViewport.fit()


def run(context):
    app = None
    ui = None

    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        design = adsk.fusion.Design.cast(
            app.activeProduct
        )

        if not design:
            app.documents.add(
                adsk.core.DocumentTypes
                .FusionDesignDocumentType
            )

            design = adsk.fusion.Design.cast(
                app.activeProduct
            )

        if not design:
            raise RuntimeError(
                'Unable to create or access a Fusion design.'
            )

        create_base_plate(
            design.rootComponent,
            design
        )

        ui.messageBox(
            'Base plate and handle created successfully.\n\n'
            'Board: 8.000 x 9.500 x 0.375 in\n'
            'Handle: 4.000 x 2.000 in\n'
            'Top margin: 0.500 in\n\n'
            'Dimensions can be changed under:\n'
            'Modify > Change Parameters',
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