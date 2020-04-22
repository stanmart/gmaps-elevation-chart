import collections
import googlemaps
import polyline


Position = collections.namedtuple("Position", ["lat", "lng"])
Elevation = collections.namedtuple("Elevation", ["lat", "lng", "elevation", "resolution"])


class GmapsClient:

    def __init__(self, key):
        self.client = googlemaps.Client(key=key)

    @staticmethod
    def get_route_coordinates(route):
        """Extract the location data and convert to latitude-longitude pairs from
        a route returned by the googlemaps.directions API.

        Args:
            route: a route returned by the googlemaps.directions API

        Returns:
            [Position]: a list of latitude-longitude pairs
        """
        coordinates = []
        for leg in route["legs"]:
            for step in leg["steps"]:
                coordinates += polyline.decode(step["polyline"]["points"])
        return [Position(*coordinate) for coordinate in coordinates]

    def get_elevations(self, path_coordinates, samples=512):
        """Get the elevation data for a number of samples along a path of coordinates.

        Args:
            path_coordinates: a list of latitude-longitude tuples representing a path
            samples: the number of samples along the path for which elevation is returned

        Returns:
            [Elevation]: a list of latitude-longitude-elevation-resolution tuples
        """
        encoded_path = polyline.encode(path_coordinates)
        elevations = self.client.elevation_along_path(path=encoded_path, samples=samples)
        return [Elevation(point["location"]["lat"], point["location"]["lng"],
                          point["elevation"], point["resolution"])
                for point in elevations]


def main():
    with open(".api-key") as api_file:
        api_key = api_file.read()
    gmaps = GmapsClient(api_key)
    return gmaps
