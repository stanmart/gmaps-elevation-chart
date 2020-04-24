from math import log, tan, pi
import numpy as np
from bokeh.plotting import figure
from bokeh.models import Range1d
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
    fig.xaxis.axis_label = "Distance (meters)"
    fig.yaxis.axis_label = "Gradient (%)"
    for route in reversed(routes):
        data = route.elevation_plot_data()
        glyph = fig.line(data["distance"], data["height"],
                         color="#8f8f8f", line_width=2, line_alpha=0.2)
        glyphs.append(glyph)
    glyphs.reverse()
    col.children.append(fig)


def plot_gradient_graphs(col, glyphs, routes, max_gradient):
    glyphs.clear()
    fig = figure(width=400, height=240)
    fig.toolbar.logo = None
    fig.toolbar_location = None
    fig.xgrid.grid_line_color = None
    fig.ygrid.grid_line_color = None
    fig.xaxis.axis_label = "Distance (meters)"
    fig.yaxis.axis_label = "Gradient (%)"
    fig.y_range = Range1d(-max_gradient, max_gradient)
    for route in reversed(routes):
        data = route.gradient_plot_data()
        glyph = fig.line(data["distance"], data["gradient"],
                         color="#8f8f8f", line_width=2, line_alpha=0.3)
        glyphs.append(glyph)
    glyphs.reverse()
    col.children.append(fig)


def plot_gradient_histogram(col, glyphs, routes, max_gradient):
    glyphs.clear()
    step = 2
    bins = np.arange(-max_gradient, max_gradient + 0.1, step)  # include endpoint
    extended_bins = np.r_[-np.inf, bins, np.inf]
    plot_bins = np.r_[-max_gradient - step, bins, max_gradient + step]

    fig = figure(width=400, height=240)
    fig.toolbar.logo = None
    fig.toolbar_location = None
    fig.xgrid.grid_line_color = None
    fig.ygrid.grid_line_color = None
    fig.y_range.start = 0
    fig.x_range = Range1d(min(plot_bins), max(plot_bins))
    fig.xaxis.axis_label = "Gradient (%)"
    fig.yaxis.axis_label = "Density"

    for route in routes:
        data = route.gradient_plot_data()
        hist, _ = np.histogram(data["gradient"], density=False, bins=extended_bins)
        normed_hist = hist / step
        glyph = fig.quad(top=normed_hist, bottom=0, left=plot_bins[:-1], right=plot_bins[1:],
                         fill_color="#5cb85c", line_color="white")
        glyph.visible = False
        glyphs.append(glyph)
    col.children.append(fig)


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
