from bokeh.layouts import column, row
from bokeh.models import Button, TextInput, Div, RadioButtonGroup, PreText, RadioGroup
from bokeh.models.callbacks import CustomJS
from bokeh.plotting import curdoc
from gmaps_elevation_chart import init_client
from googlemaps.exceptions import ApiError, HTTPError, Timeout, TransportError


gmaps = init_client()
search_results = []


def find_routes():
    modes = ["bicycling", "driving", "walking"]
    try:
        results = gmaps.get_directions(
            origin=origin_input.value,
            destination=destination_input.value,
            mode=modes[type_input.active]
        )
    except (ApiError, HTTPError, Timeout, TransportError) as e:
        if alert_holder.text == str(e):
            alert_holder.text += " "
        else:
            alert_holder.text = str(e)
        return
    search_results.clear()
    search_results.extend(results)
    result_picker.labels = ["via " + route.summary for route in search_results]
    result_picker.active = None


def display_results(attr, new, old):
    if result_picker.active is None:
        instructions.text = ""
    else:
        active_result = search_results[result_picker.active]
        instructions.text = "<br>".join(active_result.instructions)


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

instructions = Div(text="", width=500)

route_selection_pane = column([
    Div(text="<h2>Search</h2>"),
    origin_input,
    destination_input,
    type_input,
    go_button,
    alert_holder,
    Div(text="<h2>Results</h2>"),
    result_picker
])
map_pane = column([
    instructions
])
graph_pane = column()

layout = row(route_selection_pane, map_pane, graph_pane)

curdoc().add_root(layout)
