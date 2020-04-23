import collections
from math import radians, sqrt, sin, cos, asin
from itertools import accumulate
import googlemaps
import polyline


Position = collections.namedtuple("Position", ["lat", "lng"])
Elevation = collections.namedtuple("Elevation", ["position", "height", "resolution"])
Segment = collections.namedtuple(
    "Segment",
    ["start", "end", "distance", "height_diff", "gradient"]
)


class Route:

    def __init__(self, gmaps_response, mode):
        self.summary = gmaps_response["summary"]
        self.origin = gmaps_response["legs"][0]["start_address"]
        self.destination = gmaps_response["legs"][-1]["end_address"]
        self.waypoint_order = gmaps_response["waypoint_order"]
        self.coordinates = self.get_route_coordinates(gmaps_response)
        self.bounds = {
            "northeast": Position(
                gmaps_response["bounds"]["northeast"]["lat"],
                gmaps_response["bounds"]["northeast"]["lng"]
            ),
            "southwest": Position(
                gmaps_response["bounds"]["southwest"]["lat"],
                gmaps_response["bounds"]["southwest"]["lng"]
            )
        }
        self.instructions = []
        self.duration = 0
        self.distance = 0
        for leg in gmaps_response["legs"]:
            self.duration += leg["duration"]["value"]
            self.distance += leg["distance"]["value"]
            for step in leg["steps"]:
                self.instructions.append(step["html_instructions"])
        self.mode = mode
        self.elevations = None
        self.segments = None

    def __str__(self):
        head = f"{self.mode.capitalize()} route from {self.origin} to {self.destination}"
        via = f"via {self.summary}"
        length = f"{round(self.distance / 1000, 1)} kilometers"
        time = f"{max(1, round(self.duration / 60))} minutes"
        return f"{head} {via}\n{length} in {time}"

    def __repr__(self):
        return f"{self.mode.capitalize()} route from {self.origin} to {self.destination}"

    @staticmethod
    def get_route_coordinates(gmaps_response):
        """Extract the location data and convert to latitude-longitude pairs from
        a route returned by the googlemaps.directions API.

        Args:
            gmaps_response: a route returned by the googlemaps.directions API

        Returns:
            [Position]: a list of latitude-longitude pairs
        """
        coordinates = []
        for leg in gmaps_response["legs"]:
            for step in leg["steps"]:
                coordinates += polyline.decode(step["polyline"]["points"])
        return [Position(*coordinate) for coordinate in coordinates]

    def get_elevations(self, client, samples=None):
        """Get the elevation data for a number of samples along a path of this route.


        Args:
            samples: the number of samples along the path for which elevation is returned

        Returns:
            None
        """
        if samples is None:
            samples = min(self.distance // 30, 512)
        self.elevations = client.get_elevations(self.coordinates, samples)

    def calculate_segment_data(self):
        """Calculate the distance and gradient for the segments of this route

        Args:
            None

        Returns:
            None
        """
        if self.elevations is None:
            raise ValueError("Elevation samples must be obtained first")
        self.segments = calculate_gradients(self.elevations)

    def gradient_plot_data(self):
        """Return the gradient data in a plottable format (as a dict of two lists).

        Args:
            None

        Returns:
            {"distance": [float], "gradient": [float]}
        """
        if self.elevations is None:
            raise ValueError("Elevation samples must be obtained first")
        if self.segments is None:
            self.calculate_segment_data()
        segment_distance = [segment.distance for segment in self.segments]
        gradient = [segment.gradient for segment in self.segments]
        distance = list(accumulate(segment_distance))
        return {"distance": distance, "gradient": gradient}

    def elevation_plot_data(self):
        """Return the elevation data in a plottable format (as a dict of two lists).

        Args:
            None

        Returns:
            {"distance": [float], "height": [float]}
        """
        if self.elevations is None:
            raise ValueError("Elevation samples must be obtained first")
        if self.segments is None:
            self.calculate_segment_data()
        segment_distance = [segment.distance for segment in self.segments]
        distance = [0] + list(accumulate(segment_distance))
        height = [elevation.height for elevation in self.elevations]
        return {"distance": distance, "height": height}


class GmapsClient:

    def __init__(self, key):
        self.client = googlemaps.Client(key=key)

    def get_elevations(self, path_coordinates, samples=512):
        """Get the elevation data for a number of samples along a path of coordinates.

        Args:
            path_coordinates: a list of latitude-longitude tuples representing a path
            samples: the number of samples along the path for which elevation is returned

        Returns:
            [Elevation]: a list of Position-height-resolution tuples
        """
        if samples > 512:
            raise ValueError("The maximum sample size is 512")
        encoded_path = polyline.encode(path_coordinates)
        elevations = self.client.elevation_along_path(path=encoded_path, samples=samples)
        return [Elevation(Position(point["location"]["lat"], point["location"]["lng"]),
                          point["elevation"], point["resolution"])
                for point in elevations]

    def get_directions(self, origin, destination, mode="bicycling", alternatives=True,
                       waypoints=None, optimize_waypoints=False,
                       departure_time=None, traffic_model=None):
        """
        Calculate the route between two points and a possible set of waypoints.

        Args:
            see googlemaps directions documentation

        Returns:
            [Route]: a list of calculated routes
        """
        if mode not in ["driving", "walking", "bicycling"]:
            raise ValueError("Invalid travel mode (must be driving, walking or bicycling).")
        results = self.client.directions(
            origin=origin, destination=destination, mode=mode, alternatives=alternatives,
            waypoints=waypoints, optimize_waypoints=optimize_waypoints,
            departure_time=departure_time, traffic_model=traffic_model
        )
        return [Route(result, mode) for result in results]


def calculate_distance(start_pos, end_pos):
    """Calculate the great-circle distance between two positions using the havrsine formula.

    Args:
        start_pos: the start Position
        end_pos: the end Position

    Returns:
        float: their distance in meters
    """
    r = 6_371_000  # mean radius of the Earth
    lambda_start = radians(start_pos.lng)
    phi_start = radians(start_pos.lat)
    lambda_end = radians(end_pos.lng)
    phi_end = radians(end_pos.lat)

    delta_lambda = lambda_end - lambda_start
    delta_phi = phi_end - phi_start

    delta_sigma = 2 * asin(sqrt(sin(delta_phi/2) ** 2 +
                           cos(phi_start) * cos(phi_end) * sin(delta_lambda/2) ** 2))

    return r * delta_sigma


def calculate_gradients(elevations):
    """Calculate the distance and gradient data from position and elevation data

    Args:
        elevations: a list of Elevation tuples

    Returns:
        [Segment]: a list of start-end-distance-height_diff-gradient tuples
    """
    gradients = []
    for i in range(1, len(elevations)):
        start = elevations[i-1].position
        end = elevations[i].position
        distance = calculate_distance(start, end)
        height_diff = elevations[i].height - elevations[i-1].height
        gradient = 100 * height_diff / distance
        gradients.append(Segment(start, end, distance, height_diff, gradient))
    return gradients


def init_client():
    """Initialize a GmapsClient using credentials stored in an .api-key file.
    Most useful for testing and debugging purposes"

    Args:
        None

    Returns:
        GmapsClient: an initializet google maps client object
    """
    with open(".api-key") as api_file:
        api_key = api_file.read()
    gmaps = GmapsClient(api_key)
    return gmaps
