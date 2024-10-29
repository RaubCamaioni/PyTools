from typing import Dict, Any, List
from json import dumps
import cadquery as cq
from cadquery.occ_impl import jupyter_tools as jtool

TEMPLATE = """
<div id="vtk-container">
    <script type="module">
        function render(data, parent_element, ratio) {{
            const renderWindow = vtk.Rendering.Core.vtkRenderWindow.newInstance();
            const renderer = vtk.Rendering.Core.vtkRenderer.newInstance({{ background: [1, 1, 1 ] }});
            renderWindow.addRenderer(renderer);

            for (const el of data) {{ 
                const {{ shape, color, position, orientation }} = el;
                const reader = vtk.IO.XML.vtkXMLPolyDataReader.newInstance();
                const textEncoder = new TextEncoder();
                reader.parseAsArrayBuffer(textEncoder.encode(shape));
                
                const mapper = vtk.Rendering.Core.vtkMapper.newInstance();
                mapper.setInputConnection(reader.getOutputPort());
                const actor = vtk.Rendering.Core.vtkActor.newInstance();
                actor.setMapper(mapper);

                actor.getProperty().setColor(color.slice(0,3));
                actor.getProperty().setOpacity(color[3] || 1);
                actor.setPosition(position);
                actor.rotateX(orientation[0]);
                actor.rotateY(orientation[1]);
                actor.rotateZ(orientation[2]);
                
                renderer.addActor(actor);
            }};
            renderer.resetCamera();

            const openglRenderWindow = vtk.Rendering.OpenGL.vtkRenderWindow.newInstance();
            renderWindow.addView(openglRenderWindow);
            openglRenderWindow.setContainer(parent_element);
            const dims = parent_element.getBoundingClientRect();
            openglRenderWindow.setSize(dims.width, dims.width * ratio);

            const interactor = vtk.Rendering.Core.vtkRenderWindowInteractor.newInstance();
            interactor.setView(openglRenderWindow);
            interactor.initialize();
            interactor.bindEvents(parent_element);

            // Interaction setup
            const interact_style = vtk.Interaction.Style.vtkInteractorStyleTrackballCamera.newInstance();
            interactor.setInteractorStyle(interact_style);
        }};

        async function load_and_render() {{
            if (typeof vtk === 'undefined') {{
                const vtkScript = document.createElement('script');
                vtkScript.src = "https://unpkg.com/vtk.js";
                document.head.appendChild(vtkScript);
                await new Promise(resolve => vtkScript.onload = resolve);
            }}
            const data = {data};
            const parent_element = document.getElementById("vtk-container");
            render(data, parent_element, {ratio});
        }}
        load_and_render();
    </script>
</div>
"""


def display(shape) -> str:
    payload: List[Dict[str, Any]] = []

    if isinstance(shape, cq.Shape):
        payload.append(
            dict(
                shape=jtool.toString(shape),
                color=jtool.DEFAULT_COLOR,
                position=[0, 0, 0],
                orientation=[0, 0, 0],
            )
        )
    elif isinstance(shape, cq.Assembly):
        payload = jtool.toJSON(shape)
    else:
        raise ValueError(f"Type {type(shape)} is not supported")

    html_content = TEMPLATE.format(data=dumps(payload), ratio=0.5)
    return html_content
