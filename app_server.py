from bokeh.layouts import column, row
from bokeh.models import Button, TextInput, Div, RadioButtonGroup, PreText, RadioGroup
from bokeh.models.callbacks import CustomJS
from bokeh.plotting import curdoc
from gmaps_client import init_client
from googlemaps.exceptions import ApiError, HTTPError, Timeout, TransportError
from bokeh_plots import plot_elevation_graphs, plot_gradient_graphs, plot_map, plot_gradient_histogram  # noqa: E501


MAX_GRADIENT = 24

gmaps = init_client()
search_results = []


def radio_text(route):
    """Returns a short representation of a Route

    Args:
        route: a Route object

    Returns:
        str: a string containing the route summary and duration
    """
    text = " ".join([
        "via " + route.summary,
        f"({max(1, round(route.duration / 60))} minutes)"
    ])
    return text


def find_routes():
    """Callback for the go button. Obtains the planned routes and fills the document with plots.
    Modifies nonlocal mutable variables!
    """
    modes = ["bicycling", "driving", "walking"]
    try:
        results = gmaps.get_directions(
            origin=origin_input.value,
            destination=destination_input.value,
            mode=modes[type_input.active],
            alternatives=True
        )
    except (ApiError, HTTPError, Timeout, TransportError) as e:
        if alert_holder.text == str(e):
            alert_holder.text += " "
        else:
            alert_holder.text = str(e)
        return
    search_results.clear()
    search_results.extend(results)
    result_picker.labels = [radio_text(route) for route in search_results]
    result_picker.active = None
    try:
        for result in search_results:
            result.get_elevations(gmaps)
            result.calculate_segment_data()
    except (ApiError, HTTPError, Timeout, TransportError) as e:
        if alert_holder.text == str(e):
            alert_holder.text += " "
        else:
            alert_holder.text = str(e)
        return
    graph_pane.children.clear()
    plot_elevation_graphs(graph_pane, elevation_graph_glyphs, search_results)
    plot_gradient_graphs(graph_pane, gradient_graph_glyphs, search_results, MAX_GRADIENT)
    plot_gradient_histogram(graph_pane, gradient_histogram_glyphs, search_results, MAX_GRADIENT)
    if len(map_pane.children) == 2:
        del map_pane.children[0]
    plot_map(map_pane, map_plot_glyphs, search_results)


def display_results(attr, new, old):
    """Callback for the route picker radio buttons. Highlights the route on the plots.
    Modifies nonlocal mutable variables!
    """
    if result_picker.active is None:
        instructions.text = ""
    else:
        active_result = search_results[result_picker.active]
        instructions.text = "<br>".join(active_result.instructions)
    if (len(search_results) == len(elevation_graph_glyphs)
            == len(map_plot_glyphs) == len(gradient_histogram_glyphs)):
        for i in range(len(search_results)):
            if i == result_picker.active:
                elevation_graph_glyphs[i].glyph.line_color = "#5cb85c"
                gradient_graph_glyphs[i].glyph.line_color = "#5cb85c"
                map_plot_glyphs[i].glyph.line_color = "#5cb85c"
                elevation_graph_glyphs[i].glyph.line_alpha = 1
                gradient_graph_glyphs[i].glyph.line_alpha = 1
                map_plot_glyphs[i].glyph.line_alpha = 1
                gradient_histogram_glyphs[i].visible = True
            else:
                elevation_graph_glyphs[i].glyph.line_color = "#8f8f8f"
                gradient_graph_glyphs[i].glyph.line_color = "#8f8f8f"
                map_plot_glyphs[i].glyph.line_color = "#8f8f8f"
                elevation_graph_glyphs[i].glyph.line_alpha = 0.2
                gradient_graph_glyphs[i].glyph.line_alpha = 0.2
                map_plot_glyphs[i].glyph.line_alpha = 0.3
                gradient_histogram_glyphs[i].visible = False


###############################
# Route selection pane (left) #
###############################

origin_input = TextInput(width=400, title="Origin")
destination_input = TextInput(width=400, title="Destination")
type_input = RadioButtonGroup(
    labels=["Bicycle", "Driving", "Walking"],
    width=400,
    active=0
)
go_button = Button(width=400, label="Search", button_type="success")
go_button.on_click(find_routes)

alert_holder = PreText(text="", css_classes=['hidden'], visible=False)
alert = CustomJS(args={}, code='alert(cb_obj.text);')
alert_holder.js_on_change("text", alert)

result_picker = RadioGroup(labels=[], width=400)
result_picker.on_change("active", display_results)

route_selection_pane = column(
    Div(text="<h2>Search</h2>"),
    origin_input,
    destination_input,
    type_input,
    go_button,
    alert_holder,
    Div(text="<h2>Results</h2>"),
    result_picker
)

#####################
# Map pane (middle) #
#####################

map_plot_glyphs = []

instructions = Div(text="", width=600)
map_pane = column(instructions)

######################
# Graph pane (right) #
######################

elevation_graph_glyphs = []
gradient_graph_glyphs = []
gradient_histogram_glyphs = []

graph_pane = column()

layout = row(route_selection_pane, map_pane, graph_pane)

curdoc().add_root(layout)
