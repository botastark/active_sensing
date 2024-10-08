# pairwise_factor_weights: equal, biased, adaptive
import numpy as np


def collect_sample_set(grid):
    rows, cols = grid.shape
    D = []

    # Calculate number of complete 3x3 grids
    num_blocks_row = rows // 3
    num_blocks_col = cols // 3

    # Iterate over the grid in steps of 3 to access central cells of each 3x3 block
    for block_i in range(num_blocks_row):
        for block_j in range(num_blocks_col):
            # Central cell in a 3x3 block
            central_i = block_i * 3 + 1
            central_j = block_j * 3 + 1
            c = grid[central_i, central_j]

            # Collect Von Neumann neighbors
            neighbors = [
                grid[central_i - 1, central_j],  # North
                grid[central_i + 1, central_j],  # South
                grid[central_i, central_j - 1],  # West
                grid[central_i, central_j + 1],  # East
            ]

            n = sum(neighbors)

            # Append the central cell value and the sum of neighbors
            D.append((c, n))
    return D


def pearson_correlation_coeff(d_sampled):
    c_values = [c for c, n in d_sampled]
    n_values = [n for c, n in d_sampled]
    avg_c = np.mean(c_values)
    avg_n = np.mean(n_values)
    p = 0
    numerator = 0
    sum_sq_central_diff = 0
    sum_sq_neighbors_diff = 0
    for c, n in d_sampled:
        c_diff = c - avg_c
        n_diff = n - avg_n
        numerator += n_diff * c_diff
        sum_sq_central_diff += c_diff**2
        sum_sq_neighbors_diff += n_diff**2
    denominator = np.sqrt(sum_sq_central_diff * sum_sq_neighbors_diff)
    p = numerator / denominator if denominator != 0 else 0
    return p


def adaptive_weights(m_i, m_j, obs_map):

    d_sampled = collect_sample_set(obs_map)
    p = pearson_correlation_coeff(d_sampled)
    exp = np.exp(-p)

    if m_i == m_j:
        return 1 / (1 + exp)
    else:
        return exp / (1 + exp)


def pairwise_factor_(m_i, m_j, obs_map=[], type="equal"):
    if type == "equal":
        return 0.5
    elif type == "biased":
        if m_i == m_j:
            return 0.7
        else:
            return 0.3
    else:
        return adaptive_weights(m_i, m_j, obs_map)


def id_converter(map_s, coord_s, map_f):
    """
    given coordinates of map_s (i_s, j_s)
    return corresponding coordinates of map2 (i_f, j_f)
    """
    pos = map_s.grid2pos(coord_s)  # (x, y) for (i_s, j_s)
    return map_f.pos2grid(pos)


def normalize_2d_grid(grid):
    grid = np.array(grid, dtype=float)

    # Get the minimum and maximum values from the grid
    min_val = np.min(grid)
    max_val = np.max(grid)

    # Normalize the grid by scaling it to range [0, 1]
    normalized_grid = (grid - min_val) / (max_val - min_val)

    return normalized_grid


def get_neighbors(map, pos):
    i, j = pos[0], pos[1]
    rows = len(map)
    cols = len(map[0]) if rows > 0 else 0
    possible_neighbors = [
        (i - 1, j),  # Top
        (i + 1, j),  # Bottom
        (i, j - 1),  # Left
        (i, j + 1),  # Right
    ]
    neighbors = [
        (ni, nj) for ni, nj in possible_neighbors if 0 <= ni < rows and 0 <= nj < cols
    ]
    return neighbors


def observed_m_ids(uav=None, uav_pos=None, new_z=None, m_terrain=None):

    if new_z != None and m_terrain != None:
        [obsd_m_i_min, obsd_m_j_min] = id_converter(new_z, [0, 0], m_terrain)

        [obsd_m_i_max, obsd_m_j_max] = id_converter(
            new_z, [new_z.map.shape[0] - 1, new_z.map.shape[1] - 1], m_terrain
        )

    elif uav != None and uav_pos != None:
        [[obsd_m_i_min, obsd_m_i_max], [obsd_m_j_min, obsd_m_j_max]] = uav.get_range(
            position=uav_pos.position, altitude=uav_pos.altitude, index_form=True
        )
    else:
        raise TypeError("Pass either z or uav_position")

    observed_m = []
    for i_b in range(obsd_m_i_min, obsd_m_i_max):
        for j_b in range(obsd_m_j_min, obsd_m_j_max):
            observed_m.append((i_b, j_b))
    return observed_m


def normalize_probabilities(current_probs):
    # Normalization
    normalization_factor = np.sum(current_probs)  # Sum of probabilities
    normalized_probs = current_probs / normalization_factor  # Normalize
    return normalized_probs


def normalize_probabilities_(P):
    """
    Normalize the probabilities in the matrix P so that P[0, i, j] + P[1, i, j] = 1
    for all i, j.
    """
    # Sum of the probabilities for each element
    total = P[0, :, :] + P[1, :, :]

    # Normalize by dividing each probability by the total sum
    P[0, :, :] /= total
    P[1, :, :] /= total

    return P


def sample_event_matrix(P):
    "P should have shape (2, m, n) with probabilities for 0 and 1."
    P = normalize_probabilities_(P)
    assert P.shape[0] == 2
    m, n = P.shape[1], P.shape[2]
    A = np.zeros((m, n), dtype=int)
    for i in range(m):
        for j in range(n):
            # Sample a 0 or 1 based on the probabilities in P
            A[i, j] = np.random.choice([0, 1], p=[P[0, i, j], P[1, i, j]])
    return A


class uav_position:
    def __init__(self, input) -> None:

        self.position = input[0]
        self.altitude = input[1]


class point:
    def __init__(self, x=None, y=None, z=None, p=None) -> None:
        self.x = x
        self.y = y
        self.z = z
        self.probability = p
