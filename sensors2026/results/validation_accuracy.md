# LLM extraction accuracy against the blind human reference (one coder)

Human-coded studies: 23. Accuracy of LLM extraction against a single human reference coder on a random subsample - not inter-rater reliability between independent human coders.

## Pass A

| Item | n | Agreement (95% CI) | Prev. human | Prev. LLM | kappa (95% CI) | human-only yes | LLM-only yes |
|---|---:|---|---:|---:|---|---:|---:|
| `rci1_platform_model` | 23 | 91.3% (73.2%-97.6%) | 78.3% | 69.6% | 0.777 (0.481-1.000) | 2 | 0 |
| `rci2_sensors_model` | 23 | 95.7% (79.0%-99.2%) | 39.1% | 34.8% | 0.907 (0.728-1.000) | 1 | 0 |
| `rci3_compute_model` | 23 | 82.6% (62.9%-93.0%) | 34.8% | 34.8% | 0.617 (0.275-0.958) | 2 | 2 |
| `rci4_middleware_version` | 23 | 100.0% (85.7%-100.0%) | 0.0% | 0.0% | undefined | 0 | 0 |
| `rci5_algorithms_cited` | 23 | 82.6% (62.9%-93.0%) | 65.2% | 82.6% | 0.566 (0.180-0.953) | 0 | 4 |
| `rci6_parameters` | 23 | 82.6% (62.9%-93.0%) | 73.9% | 91.3% | 0.425 (-0.087-0.937) | 0 | 4 |
| `rci7_eval_environment` | 23 | 82.6% (62.9%-93.0%) | 65.2% | 56.5% | 0.638 (0.315-0.960) | 3 | 1 |
| `cap_real_world_validation` | 23 | 65.2% (44.9%-81.2%) | 65.2% | 82.6% | 0.132 (-0.354-0.618) | 2 | 6 |
| `rci8_success_metric` | 23 | 91.3% (73.2%-97.6%) | 73.9% | 82.6% | 0.747 (0.413-1.000) | 0 | 2 |
| `cap_slam_mapping` | 23 | 82.6% (62.9%-93.0%) | 47.8% | 39.1% | 0.649 (0.336-0.962) | 3 | 1 |
| `cap_autonomous_navigation` | 23 | 73.9% (53.5%-87.5%) | 43.5% | 52.2% | 0.481 (0.124-0.838) | 2 | 4 |
| `cap_obstacle_avoidance` | 23 | 73.9% (53.5%-87.5%) | 26.1% | 43.5% | 0.444 (0.061-0.826) | 1 | 5 |
| `cap_object_detection` | 23 | 87.0% (67.9%-95.5%) | 30.4% | 34.8% | 0.704 (0.391-1.000) | 1 | 2 |
| `cap_instrument_reading` | 23 | 91.3% (73.2%-97.6%) | 8.7% | 17.4% | 0.623 (0.124-1.000) | 0 | 2 |
| `cap_target_tracking` | 23 | 100.0% (85.7%-100.0%) | 4.3% | 4.3% | 1.000 (1.000-1.000) | 0 | 0 |
| `rci9_artifact` | 23 | 100.0% (85.7%-100.0%) | 13.0% | 13.0% | 1.000 (1.000-1.000) | 0 | 0 |
| `rci4_middleware_version__blind` | 23 | 78.3% (58.1%-90.3%) | 21.7% | 0.0% | 0.000 (-0.775-0.775) | 5 | 0 |
| `rci2_sensors_model__blind` | 23 | 91.3% (73.2%-97.6%) | 43.5% | 34.8% | 0.819 (0.579-1.000) | 2 | 0 |
| `sensor_specificity` (ordinal) | 23 | 73.9% (53.5%-87.5%) | - | - | weighted 0.629 | - | - |
| `compute_specificity` (ordinal) | 23 | 82.6% (62.9%-93.0%) | - | - | weighted 0.728 | - | - |
| `eval_environment_kind` (nominal) | 23 | 73.9% (53.5%-87.5%) | - | - | - | - | - |

## Pass B

| Item | n | Agreement (95% CI) | Prev. human | Prev. LLM | kappa (95% CI) | human-only yes | LLM-only yes |
|---|---:|---|---:|---:|---|---:|---:|
| `rci1_platform_model` | 23 | 95.7% (79.0%-99.2%) | 78.3% | 73.9% | 0.881 (0.652-1.000) | 1 | 0 |
| `rci2_sensors_model` | 23 | 95.7% (79.0%-99.2%) | 39.1% | 43.5% | 0.911 (0.739-1.000) | 0 | 1 |
| `rci3_compute_model` | 23 | 91.3% (73.2%-97.6%) | 34.8% | 34.8% | 0.808 (0.555-1.000) | 1 | 1 |
| `rci4_middleware_version` | 23 | 82.6% (62.9%-93.0%) | 0.0% | 17.4% | 0.000 (-0.891-0.891) | 0 | 4 |
| `rci5_algorithms_cited` | 23 | 82.6% (62.9%-93.0%) | 65.2% | 73.9% | 0.593 (0.230-0.956) | 1 | 3 |
| `rci6_parameters` | 23 | 82.6% (62.9%-93.0%) | 73.9% | 91.3% | 0.425 (-0.087-0.937) | 0 | 4 |
| `rci7_eval_environment` | 23 | 87.0% (67.9%-95.5%) | 65.2% | 69.6% | 0.704 (0.391-1.000) | 1 | 2 |
| `cap_real_world_validation` | 23 | 69.6% (49.1%-84.4%) | 65.2% | 78.3% | 0.265 (-0.189-0.719) | 2 | 5 |
| `rci8_success_metric` | 23 | 82.6% (62.9%-93.0%) | 73.9% | 91.3% | 0.425 (-0.087-0.937) | 0 | 4 |
| `cap_slam_mapping` | 23 | 82.6% (62.9%-93.0%) | 47.8% | 47.8% | 0.652 (0.341-0.962) | 2 | 2 |
| `cap_autonomous_navigation` | 23 | 69.6% (49.1%-84.4%) | 43.5% | 65.2% | 0.415 (0.053-0.776) | 1 | 6 |
| `cap_obstacle_avoidance` | 23 | 82.6% (62.9%-93.0%) | 26.1% | 34.8% | 0.593 (0.230-0.956) | 1 | 3 |
| `cap_object_detection` | 23 | 73.9% (53.5%-87.5%) | 30.4% | 47.8% | 0.469 (0.104-0.834) | 1 | 5 |
| `cap_instrument_reading` | 23 | 95.7% (79.0%-99.2%) | 8.7% | 13.0% | 0.777 (0.349-1.000) | 0 | 1 |
| `cap_target_tracking` | 23 | 100.0% (85.7%-100.0%) | 4.3% | 4.3% | 1.000 (1.000-1.000) | 0 | 0 |
| `rci9_artifact` | 23 | 100.0% (85.7%-100.0%) | 13.0% | 13.0% | 1.000 (1.000-1.000) | 0 | 0 |
| `rci4_middleware_version__blind` | 23 | 78.3% (58.1%-90.3%) | 21.7% | 17.4% | 0.311 (-0.223-0.845) | 3 | 2 |
| `rci2_sensors_model__blind` | 23 | 91.3% (73.2%-97.6%) | 43.5% | 43.5% | 0.823 (0.589-1.000) | 1 | 1 |
| `sensor_specificity` (ordinal) | 23 | 78.3% (58.1%-90.3%) | - | - | weighted 0.704 | - | - |
| `compute_specificity` (ordinal) | 23 | 91.3% (73.2%-97.6%) | - | - | weighted 0.858 | - | - |
| `eval_environment_kind` (nominal) | 23 | 69.6% (49.1%-84.4%) | - | - | - | - | - |

