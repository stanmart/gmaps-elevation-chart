from math import log, tan, pi
import numpy as np
from bokeh.plotting import figure
from bokeh.tile_providers import CARTODBPOSITRON, get_provider


def lat_to_y(lat):
    r = 6_378_137  # radius of the Earth at the equator
    return log(tan((90 + lat) * pi / 360)) * r


def lng_to_x(lng):
    r = 6_378_137  # radius of the Earth at the equator
    return lng * r * pi / 180


def plot_elevation_graphs(col, glyphs, routes):
    glyphs.clear()
    fig = figure(width=400, height=240)
    fig.toolbar.logo = None
    fig.toolbar_location = None
    fig.xgrid.grid_line_color = None
    fig.ygrid.grid_line_color = None
    fig.xaxis.axis_label = "Distance"
    fig.yaxis.axis_label = "Gradient (%)"
    for route in reversed(routes):
        data = route.elevation_plot_data()
        glyph = fig.line(data["distance"], data["height"],
                         color="#8f8f8f", line_width=2, line_alpha=0.2)
        glyphs.append(glyph)
    glyphs.reverse()
    col.children.append(fig)


def plot_gradient_graphs(col, glyphs, routes):
    glyphs.clear()
    fig = figure(width=400, height=240)
    fig.toolbar.logo = None
    fig.toolbar_location = None
    fig.xgrid.grid_line_color = None
    fig.ygrid.grid_line_color = None
    fig.xaxis.axis_label = "Distance"
    fig.yaxis.axis_label = "Gradient (%)"
    for route in reversed(routes):
        data = route.gradient_plot_data()
        glyph = fig.line(data["distance"], data["gradient"],
                         color="#8f8f8f", line_width=2, line_alpha=0.3)
        glyphs.append(glyph)
    glyphs.reverse()
    col.children.append(fig)


def plot_gradient_histogram(route):
    data = route.gradient_plot_data()
    hist, edges = np.histogram(data["gradient"], density=True, bins=50)
    fig = figure(width=400, height=240)
    fig.toolbar.logo = None
    fig.toolbar_location = None
    fig.xgrid.grid_line_color = None
    fig.ygrid.grid_line_color = None
    fig.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
             fill_color="#5cb85c", line_color="white")
    fig.y_range.start = 0
    fig.xaxis.axis_label = "Gradient (%)"
    fig.yaxis.axis_label = "Density"
    return fig


def plot_map(col, glyphs, routes):
    glyphs.clear()
    fig = figure(width=600, height=400, match_aspect=True,
                 x_axis_type="mercator", y_axis_type="mercator")
    fig.axis.visible = False
    tile_provider = get_provider(CARTODBPOSITRON)
    fig.add_tile(tile_provider)
    for route in reversed(routes):
        data = route.map_plot_data()
        glyph = fig.line([lng_to_x(lng) for lng in data["lng"]],
                         [lat_to_y(lat) for lat in data["lat"]],
                         color="#8f8f8f", line_width=2, line_alpha=0.2)
        glyphs.append(glyph)
    glyphs.reverse()
    col.children.insert(0, fig)
