from helper import (
    FastLogger,
    compute_coverage,
    observed_m_ids,
    plot_metrics,
    uav_position,
    compute_mse,
)
from terrain_creation import (
    fft_gaussian_random_field,
    terrain,
)
from uav_camera import camera
from planner import planning

desktop = "/home/bota/Desktop/"
action_select_strategy = "ig"  # "ig", "random" "sweep"
pairwise = "equal"
n_step = 51


class grid_info:
    x = 50
    y = 50
    length = 0.5
    shape = (int(x / length), int(y / length))


class camera_params:
    fov_angle = 60


camera = camera(grid_info, camera_params.fov_angle)


# Ground truth map with n gaussian peaks
true_map = terrain(grid_info)
true_map.set_map(fft_gaussian_random_field(true_map, 20))
x = uav_position(((0, 0), 5.4))

logger = FastLogger(
    "/home/bota/Desktop/active_sensing",
    strategy=action_select_strategy,
    pairwise=pairwise,
    grid=grid_info,
    init_x=x,
)


plan1 = planning(true_map, camera)

actions, uav_positions = [], []
entropies, mse, height, coverage = [], [], [], []
obs_ms = set()


true_map.plot_map(desktop + "gt.png", fit=False)
for step in range(n_step):
    print("step ", step)
    # Observe
    uav_positions.append(x)
    camera.set_altitude(x.altitude)
    camera.set_position(x.position)
    z = camera.sample_observation(true_map, x)
    # print(np.max(z.x))

    # Map
    plan1.mapping(x, z)
    current_state = plan1.get_current_state()
    obs_ms.update(observed_m_ids(camera, x))

    # collect data
    entropies.append(plan1.get_entropy())
    mse.append(compute_mse(true_map.map, current_state.map))
    coverage.append(compute_coverage(list(obs_ms), grid_info))
    pos, alt = plan1.get_uav_current_pos()
    height.append(alt)

    # Plan
    next_action = plan1.select_action(strategy=action_select_strategy)

    # Act
    # x_{t+1} UAV position after taking action a
    x = uav_position(camera.x_future(next_action))
    actions.append(next_action)

    # Check plots
    logger.log_data(entropies[-1], mse[-1], height[-1], coverage[-1])
    logger.log("actions: " + str(actions))
    if step % 1 == 0:
        current_x, current_z = plan1.get_last_observation()

        # current_z.plot_prob(desktop + str(step) + "_prob_z.png")
        filename = desktop + "step_" + str(step) + ".png"
        current_state.plot_prob(desktop + "_prob_step" + str(step) + ".png")
        current_state.plot_terrain(filename, uav_positions, true_map, current_z)


plot_metrics(entropies, mse, coverage)
