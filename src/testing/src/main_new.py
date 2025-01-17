from mapper import OccupancyMap, get_observations
import timeit
import os

from helper import (
    FastLogger,
    compute_metrics,
    observed_m_ids,
    uav_position,
    gaussian_random_field
)
from planner_new import planning
from uav_camera import camera

from viewer import plot_terrain, plot_metrics

desktop = "/home/bota/Desktop/active_sensing"
# desktop = "/Users/botaduisenbay/active_sensing"

cache_dir = desktop + "/cache/"
desktop += "/testing"
correlation_type = "adaptive"  # "biased", "equal" "adaptive"
action_select_strategy = "ig"  # "ig", "random" "sweep" ig_with_mexgen
n_steps = 100
grf_r = 5
if not os.path.exists(desktop):
    os.makedirs(desktop)


class grid_info:
    x = 50
    y = 50
    length = 0.125
    shape = (int(x / length), int(y / length))


uav_pos = uav_position(((0, 0), 5.4))

logger = FastLogger(
    desktop,
    strategy=action_select_strategy,
    pairwise=correlation_type,
    grid=grid_info,
    init_x=uav_pos,
    r=grf_r,
)

ground_truth_map = gaussian_random_field(grf_r, grid_info.shape[0])
mapper = OccupancyMap(grid_info.shape[0])
camera = camera(grid_info, 60)


camera.set_altitude(uav_pos.altitude)
camera.set_position(uav_pos.position)
uav_positions, past_observations, actions = [uav_pos], [], []


belief_map = mapper.marginalize()
planner = planning(belief_map, camera, action_select_strategy)

obs_ms = set()
entropy, mse, height, coverage = [], [], [], []

for step in range(n_steps + 1):
    # collect observations
    print(f"step {step}")
    zx, zy, submap = get_observations(grid_info, ground_truth_map, uav_pos)
    # mapping
    mapper.update_observations(zx, zy, submap, uav_pos, belief_map)
    mapper.propagate_messages(max_iterations=1, correlation_type=correlation_type)
    belief_map = mapper.marginalize()

    # collect metrics, log and plot
    obs_ms.update(observed_m_ids(camera, uav_pos))
    entropy_val, mse_val, coverage_val = compute_metrics(
        ground_truth_map, belief_map, obs_ms, grid_info
    )

    entropy.append(entropy_val)
    mse.append(mse_val)
    coverage.append(coverage_val)
    height.append(uav_pos.altitude)

    logger.log_data(entropy[-1], mse[-1], height[-1], coverage[-1])
    logger.log("actions: " + str(actions))

    plot_metrics(desktop, entropy, mse, coverage, height)

    plot_terrain(
        f"{desktop}/step_{step}.png",
        belief_map,
        grid_info,
        uav_positions,
        ground_truth_map,
        submap,
        zx,
        zy,
    )

    if step == n_steps:
        break

    # PLAN
    next_action = planner.select_action(belief_map, uav_positions)

    # ACT
    uav_pos = uav_position(camera.x_future(next_action))
    uav_positions.append(uav_pos)
    actions.append(next_action)

    camera.set_altitude(uav_pos.altitude)
    camera.set_position(uav_pos.position)
