---
repo_name: ai-winter/ros_motion_planning
url: "https://github.com/ai-winter/ros_motion_planning"
stars: 3467
forks: 510
contributors_count: 6
last_commit_date: "2026-03-28T08:35:03+00:00"
primary_use_case: Simulation
user_tier: Mid-Tier
total_score: 5
architecture_labels: [Custom/Other]
use_case_labels: [RAG + Agents, Browser / Terminal Use, Simulation]
generated_at: "2026-04-27T13:42:46.834795+00:00"
model: auto
duration_s: 97.3
clone_size_kb: 266137
uses_mas: no
final_use_case: Simulation
---
## 1. Overview

`ai-winter/ros_motion_planning` is a ROS Noetic motion-planning and navigation stack for simulated (and optionally real) mobile robots, not an LLM-agent system. A user typically runs `scripts/main.sh`, which generates launch files from YAML config and starts Gazebo + map server + `move_base` with selected global/local planner plugins (`scripts/main.sh:1-3`, `src/plugins/dynamic_xml_config/plugins/robot_generate.py:27-115`, `src/sim_env/launch/config.launch:27-49`). In RViz (or via a goal publisher script), users send navigation goals and watch robots execute algorithms such as A*, D*, RRT*, DWA, MPC, ORCA, etc. (`src/sim_env/launch/include/navigation/move_base.launch.xml:30-56`, `src/core/controller/orca_controller/scripts/goal_publisher.py:9-53`). The core output is robot trajectories/velocities in simulation, plus planner/controller visualizations.

## 2. Agent Framework & Architecture

No LLM agent framework is used here (no LangChain/LangGraph/AutoGen/CrewAI/LlamaIndex/OpenAI SDK wiring found in source/build manifests). The architecture is a ROS plugin-based navigation system: `move_base` loads a global planner plugin (`path_planner/PathPlanner`) and one local planner plugin (DWA/PID/APF/RPP/LQR/MPC/ORCA) via launch parameters (`src/sim_env/launch/include/navigation/move_base.launch.xml:30-44`).

The global planner wrapper (`PathPlannerNode`) instantiates a concrete planner through `PathPlannerFactory` based on `planner_name`, then serves `makePlan` calls and publishes path/expansion visualizations (`src/core/path_planner/path_planner/src/path_planner_node.cpp:53-95`, `src/core/path_planner/path_planner/src/utils/path_planner_factory.cpp:52-127`). Configuration is loaded from protobuf text (`system_config.pb.txt`) into a singleton config object (`src/core/system_config/src/system_config.cpp:24-46`).

The repo does use the term “agent,” but it refers to robot entities in multi-robot navigation (e.g., ORCA’s `agent_number`, `agent_id`), not AI reasoning agents (`src/core/controller/orca_controller/src/orca_controller.cpp:57-69`).

## 3. Orchestration Pattern

Closest match: **other (ROS node/plugin pipeline with recursive multi-robot launch orchestration)**.

Control is mostly sequential within each navigation cycle (`goal -> global path -> local velocity`), while multi-robot startup is orchestrated recursively in launch XML generation.

Example 1 (planner dispatch inside plugin factory, selecting algorithm at runtime): `src/core/path_planner/path_planner/src/utils/path_planner_factory.cpp:55-63`
```cpp
std::string planner_name;
nh.param("planner_name", planner_name, (std::string) "astar");
if (planner_name == "astar") {
  planner_props.planner_ptr = std::make_shared<AStarPathPlanner>(costmap_ros);
  planner_props.planner_type = GRAPH_PLANNER;
} else if (planner_name == "dijkstra") {
  planner_props.planner_ptr = std::make_shared<AStarPathPlanner>(costmap_ros, true);
```

Example 2 (recursive launch-style orchestration for N robots): `src/plugins/dynamic_xml_config/plugins/robot_generate.py:105-110`
```python
cycle = RobotGenerator.createElement(
    "include",
    props={"file": "$(find sim_env)/launch/include/robots/start_robots.launch.xml",
           "if": "$(eval arg('agent_id') > 1)"}
)
cycle.append(RobotGenerator.createElement("arg", props={"name": "agent_id", "value": "$(eval arg('agent_id') - 1)"}))
```

## 4. Tools & External Integrations

No LLM tools/APIs (MCP, web search tools, vector DBs, browser automation, OpenAI/Anthropic calls) are wired in the runtime code.

External integrations that are present are robotics/simulation infrastructure:

- **ROS `move_base` + nav_core plugins**: global/local planner plugin injection via launch params (`src/sim_env/launch/include/navigation/move_base.launch.xml:30-44`).
- **Gazebo simulator**: world launch via `gazebo_ros/empty_world.launch` (`src/sim_env/launch/config.launch:27-35`).
- **ROS map server**: static map loading (`src/sim_env/launch/config.launch:37-39`).
- **RViz + dynamic RViz config generation**: visualization startup (`src/sim_env/launch/config.launch:45-48`).
- **Pluginlib in C++**: exports planner/controller plugins (`src/core/path_planner/path_planner/src/path_planner_node.cpp:26`, `src/core/controller/orca_controller/src/orca_controller.cpp:23`).
- **ORCA/RVO library integration** for multi-robot collision avoidance (`src/core/controller/orca_controller/src/orca_controller.cpp:78-80`, `:164-169`).

## 5. Notable Code Walkthrough

- `src/core/path_planner/path_planner/src/path_planner_node.cpp:53-231` - ROS global planner wrapper that initializes publishers/service, validates frames, calls planner `plan()`, and publishes plan/expansion artifacts.
- `src/core/path_planner/path_planner/src/utils/path_planner_factory.cpp:52-127` - central algorithm router choosing among graph, sampling, and evolutionary planners from `planner_name`.
- `src/sim_env/launch/include/navigation/move_base.launch.xml:30-72` - where `move_base` is wired to global/local planner plugins and costmap parameters; this is the key runtime integration point.
- `src/plugins/dynamic_xml_config/plugins/robot_generate.py:35-115` - generates recursive robot launch XML from user YAML; enables single/multi-robot experiments without manual launch editing.
- `src/core/controller/orca_controller/src/orca_controller.cpp:57-137` - ORCA local controller subscribing to all robot odometry streams and computing collision-avoiding velocity commands.

## 6. Use-Case Mapping

The assigned use case **Simulation** is correct. The codebase centers on Gazebo world launch, map loading, ROS navigation stack wiring, and algorithm benchmarking/visualization in simulated environments (`src/sim_env/launch/config.launch:27-49`, `README.md:85-113`). Even the “multi agents” wording in README corresponds to multiple robots in simulation, not LLM-based agent collaboration (`README.md:106-113`, `src/user_config/user_config_multi.yaml:5-36`). So this project is a robotics simulation/navigation framework rather than an agentic-AI repository.

## 7. Strengths, Limitations & Research Relevance

- **Strengths:**
  - Broad planner/controller coverage under one consistent ROS plugin interface (`path_planner_factory.cpp:58-119`, `move_base.launch.xml:36-43`).
  - Clean runtime configurability through launch params + protobuf/YAML config (`system_config.cpp:24-46`, `robot_generate.py:62-104`).
  - Practical multi-robot support (namespaces, recursive launch, ORCA odom exchange) (`start_robots.launch.xml:12-27`, `orca_controller.cpp:61-67`).
  - Visualization hooks for path search behavior (expand zones, trees, particles) (`path_planner_node.cpp:185-223`).

- **Limitations:**
  - No LLM or multi-agent AI runtime despite repository labels implying “agentic” contexts.
  - Startup relies on generated launch files/scripts, which can obscure source-of-truth config for newcomers (`README.md:93-94`, `scripts/main.sh:1-3`).
  - Some multi-robot examples are hard-coded (e.g., 4-goal publisher script) rather than generalized tooling (`goal_publisher.py:11-19`).
  - Strong ROS1/Gazebo coupling; portability to ROS2 or non-ROS environments is limited by design.

- **Research relevance:**
  - Useful as evidence for **classical multi-robot navigation orchestration** (non-LLM agent interpretation).
  - Useful benchmark substrate for comparing global/local planning algorithms under shared simulation conditions.
  - Useful example of plugin-factory dispatch and configurable planner/controller composition in robotics middleware.

## 8. Machine-readable classification

USES_MAS: no
FINAL_USE_CASE: Simulation
