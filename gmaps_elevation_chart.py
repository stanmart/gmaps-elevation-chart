import collections
from math import radians, sqrt, sin, cos, asin
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
        self.gradients = None

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

        """
        if mode not in ["driving", "walking", "bicycling"]:
            raise ValueError("Invalid travel mode (must be driving, walking or bycicling).")
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


def main():
    with open(".api-key") as api_file:
        api_key = api_file.read()
    gmaps = GmapsClient(api_key)
    return gmaps
