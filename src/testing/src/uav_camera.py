import math
import numpy as np

# from helper import id_converter, sample_event_matrix,
from helper import uav_position

# from terrain_creation import terrain


class camera:
    def __init__(
        self,
        grid,
        fov_angle,
        camera_altitude=0,
        camera_pos=(0.0, 0.0),
        rng=np.random.default_rng(123),
    ):

        self.grid = grid
        self.altitude = camera_altitude
        self.position = camera_pos
        self.rng = rng
        self.fov = fov_angle
        if self.grid.center:
            self.x_range = [-self.grid.x / 2, self.grid.x / 2]
            self.y_range = [-self.grid.y / 2, self.grid.y / 2]
        else:
            self.x_range = [0, self.grid.x]
            self.y_range = [0, self.grid.y]

        # Dynamic xy_step and h_step calculation if not explicitly provided
        min_range = min(
            self.x_range[1] - self.x_range[0], self.y_range[1] - self.y_range[0]
        )
        self.xy_step = min_range / 2 / 8
        self.h_step = self.xy_step / np.tan(np.deg2rad(self.fov * 0.5))
        self.h_range = (self.h_step, 6 * self.h_step)
        self.a = 1
        self.b = 0.015
        self.actions = {"up", "down", "front", "back", "left", "right", "hover"}
        # print(f"H range: {self.h_range}")

    def reset(self):
        self.position = (0.0, 0.0)
        self.altitude = self.h_step

    def set_position(self, pos):
        self.position = pos

    def get_hstep(self):
        return self.h_step

    def set_altitude(self, alt):
        self.altitude = alt

    def get_x(self):
        return uav_position((self.position, self.altitude))

    def convert_xy_ij(self, x, y, centered):
        if centered:
            center_i, center_j = (dim // 2 for dim in self.grid.shape)
            j = x / self.grid.length + center_j
            i = -y / self.grid.length + center_i
        else:
            j = x / self.grid.length
            i = self.grid.shape[0] - y / self.grid.length
        return int(i), int(j)

    def get_range(self, position=None, altitude=None, index_form=False):
        """
        calculates indices of camera footprints (part of terrain (therefore terrain indices) seen by camera at a given UAV pos and alt)
        """
        position = position if position is not None else self.position
        altitude = altitude if altitude is not None else self.altitude
        grid_length = self.grid.length
        fov_rad = np.deg2rad(self.fov) / 2

        x_dist = round(altitude * math.tan(fov_rad) / grid_length) * grid_length
        y_dist = round(altitude * math.tan(fov_rad) / grid_length) * grid_length

        x_min, x_max = np.clip(
            [position[0] - x_dist, position[0] + x_dist], *self.x_range
        )
        y_min, y_max = np.clip(
            [position[1] - y_dist, position[1] + y_dist], *self.y_range
        )
        if x_max - x_min == 0 or y_max - y_min == 0:
            return [[0, 0], [0, 0]]
        """
        print(f"dist x:{x_dist} y:{y_dist}")
        print(f"ranges x{self.x_range} y{self.y_range}")
        print(f"pos: {self.position} {self.altitude}")
        print(f"visible ranges x:({x_min}:{x_max}) y:({y_min}:{y_max})")
        """

        if not index_form:
            return [[x_min, x_max], [y_min, y_max]]
        i_max, j_min = self.convert_xy_ij(x_min, y_min, self.grid.center)
        i_min, j_max = self.convert_xy_ij(x_max, y_max, self.grid.center)
        # print(f"visible ranges i:({i_min}:{i_max}) j:({j_min}:{j_max})")
        return [[i_min, i_max], [j_min, j_max]]

    def get_observations(self, ground_truth_map, sigmas=None):
        [[i_min, i_max], [j_min, j_max]] = self.get_range(
            # uav_pos, grid_info,
            index_form=True
        )

        submap = ground_truth_map[i_min:i_max, j_min:j_max]
        """
        print(f"obs area ids:{x_min_id}:{x_max_id}, {y_min_id}:{y_max_id} ")
        print(f"gt map shape:{ground_truth_map.shape}")
        print(f"gt submap shape:{submap.shape}")
        """
        # x = np.arange(i_min, i_max, 1)
        # y = np.arange(j_min, j_max, 1)
        if sigmas is None:
            sigma = self.a * (1 - np.exp(-self.b * self.altitude))
            sigmas = [sigma, sigma]

        sigma0, sigma1 = sigmas[0], sigmas[1]

        # rng = np.random.default_rng()
        random_values = self.rng.random(submap.shape)
        success0 = random_values <= 1.0 - sigma0
        success1 = random_values <= 1.0 - sigma1
        z0 = np.where(np.logical_and(success0, submap == 0), 0, 1)
        z1 = np.where(np.logical_and(success1, submap == 1), 1, 0)
        z = np.where(submap == 0, z0, z1)

        # x, y = np.meshgrid(x, y, indexing="ij")
        fp_vertices_ij = {
            "ul": np.array([i_min, j_min]),
            "bl": np.array([i_max, j_min]),
            "ur": np.array([i_min, j_max]),
            "br": np.array([i_max, j_max]),
        }

        return fp_vertices_ij, z

    def x_future(self, action):
        # possible_actions = {"up", "down", "front", "back", "left", "right", "hover"}
        if action == "up" and round(self.altitude + self.h_step, 1) <= round(
            self.h_range[1], 1
        ):
            return (self.position, self.altitude + self.h_step)
        elif action == "down" and self.altitude - self.h_step >= self.h_range[0]:
            return (self.position, self.altitude - self.h_step)
        # front (+y)
        elif action == "front" and self.position[1] + self.xy_step <= self.y_range[1]:
            return (self.position[0], self.position[1] + self.xy_step), self.altitude
        # back (-y)
        elif action == "back" and self.position[1] - self.xy_step >= self.y_range[0]:
            return (self.position[0], self.position[1] - self.xy_step), self.altitude
        # right (+x)
        elif action == "right" and self.position[0] + self.xy_step <= self.x_range[1]:
            return (self.position[0] + self.xy_step, self.position[1]), self.altitude
        # left (-x)
        elif action == "left" and self.position[0] - self.xy_step >= self.x_range[0]:
            return (self.position[0] - self.xy_step, self.position[1]), self.altitude
        # hover
        else:
            return self.position, self.altitude

    def permitted_actions(self, x):
        # possible_actions = {"up", "down", "front", "back", "left", "right", "hover"}
        permitted_actions = ["hover"]
        for action in self.actions:
            if action == "up" and round(x.altitude + self.h_step, 2) <= round(
                self.h_range[1], 2
            ):
                permitted_actions.append(action)
            elif action == "down" and x.altitude - self.h_step >= self.h_range[0]:
                permitted_actions.append(action)
            elif action == "front" and x.position[0] - self.xy_step >= self.x_range[0]:
                permitted_actions.append(action)
            elif action == "back" and x.position[0] + self.xy_step <= self.x_range[1]:
                permitted_actions.append(action)
            elif action == "right" and x.position[1] + self.xy_step <= self.y_range[1]:
                permitted_actions.append(action)
            elif action == "left" and x.position[1] - self.xy_step >= self.y_range[0]:
                permitted_actions.append(action)
        return permitted_actions
