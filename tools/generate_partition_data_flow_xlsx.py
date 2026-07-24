#!/usr/bin/env python3
"""Generate a formatted Excel workbook for the Autoware partition data flow."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile

import uno
import yaml
from com.sun.star.beans import PropertyValue
from com.sun.star.table import BorderLine2


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "Autoware_Partition_Data_Flow.xlsx"
METADATA = ROOT / "rosbag/dummy_obstacle_20260722_173416/metadata.yaml"
CONFIG_DIR = ROOT / "partition/partition_config"

PARTITION_NAMES = {
    "sample-adsw-perception": "Perception",
    "sample-adsw-decision": "Decision",
    "sample-adsw-control": "Control",
}

COMPONENT_ROLES = {
    "Common / Parameter": "공통 파라미터와 차량 설정",
    "Partition Launch": "파티션별 launch, config 및 RViz 설정",
    "Map": "Lanelet2 및 pointcloud map 제공",
    "Sensing": "센서 드라이버, 전처리 및 sensor kit 구성",
    "Localization": "차량 pose와 좌표계 추정",
    "Perception": "객체 검출, 추적, 예측 및 점군 처리",
    "Visualization / RViz": "RViz 시각화와 조작 플러그인",
    "Planning": "route, path, trajectory 및 속도 계획",
    "System": "Autoware 상태와 진단 관리",
    "Control": "trajectory 추종과 차량 제어 명령 생성",
    "Vehicle Interface": "차량 모델, 인터페이스와 상태 변환",
    "Simulator": "Planning Simulation용 센서·차량 모델",
    "Common / Dependency": "컴포넌트 외부의 공통 빌드·실행 의존성",
}

COMPONENT_ROWS = [
    ("Perception", "Map", "주요 기능", "src/universe/autoware.universe/map\ntier4_map_launch", "tier4_map_component.launch.xml", "vector map, pointcloud map 및 map TF 제공"),
    ("Perception", "Sensing", "주요 기능", "src/sensor_component\nsrc/sensor_kit\nsrc/universe/autoware.universe/sensing", "tier4_sensing_component.launch.xml", "센서 계층 및 전처리 구성"),
    ("Perception", "Localization", "주요 기능", "src/universe/autoware.universe/localization\ntier4_localization_launch", "tier4_localization_component.launch.xml", "초기 pose와 차량 위치·좌표계 처리"),
    ("Perception", "Perception", "주요 기능", "src/universe/autoware.universe/perception\ndummy perception 보완 패키지", "tier4_perception_component.launch.xml\nperception_simulator_component.launch.xml", "객체 검출·추적·예측 및 장애물 점군 생성"),
    ("Perception", "Visualization / RViz", "UI 및 보조 기능", "src/universe/autoware.universe/visualization\nrviz2\ntier4_dummy_object_rviz_plugin", "adsw_perception.launch.xml", "지도·경로 시각화와 pose·goal·더미 객체 입력"),
    ("Decision", "Planning", "주요 기능", "src/universe/autoware.universe/planning\ntier4_planning_launch", "tier4_planning_component.launch.xml", "route, path, trajectory 및 장애물 반영 속도 계획"),
    ("Decision", "System", "주요 기능", "src/universe/autoware.universe/system\ntier4_system_launch", "tier4_system_component.launch.xml", "Autoware 상태와 진단 관리"),
    ("Control", "Control", "주요 기능", "src/universe/autoware.universe/control\ntier4_control_launch", "tier4_control_component.launch.xml", "trajectory 추종과 최종 조향·가감속 명령 생성"),
    ("Control", "Vehicle Interface", "주요 기능", "src/universe/autoware.universe/vehicle\nsrc/vehicle\ntier4_vehicle_launch", "adsw_control.launch.xml", "차량 모델, 인터페이스 및 상태 계층"),
    ("Control", "Simulator", "시험 기능", "autoware_simple_planning_simulator\ntier4_simulator_launch", "obigo_simulator_component.launch.xml", "제어 명령을 차량 운동으로 반영하고 상태 피드백"),
    ("Control", "AD API", "인터페이스", "tier4_autoware_api_launch\nautoware_default_adapi", "tier4_autoware_api_component.launch.xml", "RViz와 외부 도구의 상태·운전 모드 API 제공"),
]

COMPONENT_SUMMARY_ROWS = [
    ("Perception", "Map", "사용", "Lanelet2 Vector Map, Pointcloud Map과 지도 좌표계를 제공"),
    ("Perception", "Sensing", "현재 시험에서는 미사용", "실제 센서 드라이버와 센서 데이터 전처리"),
    ("Perception", "Localization", "현재 시험에서는 Simulator로 대체", "실차 환경에서 차량 위치·자세와 좌표계를 추정"),
    ("Perception", "Perception", "Dummy Perception 사용", "RViz 더미 객체를 검출·추적·예측 객체와 Pointcloud로 변환"),
    ("Perception", "Visualization / RViz", "사용", "지도·경로 시각화와 초기 위치·목적지·더미 객체 입력"),
    ("Decision", "Planning", "사용", "Route, Path, Trajectory와 장애물 반영 속도를 계획"),
    ("Decision", "System", "사용", "Autoware 상태, 운전 모드와 진단 상태를 관리"),
    ("Control", "Control", "사용", "최종 Trajectory를 추종하여 조향·가감속 명령을 생성"),
    ("Control", "Vehicle Interface", "현재 시험에서는 Simulator로 대체", "실차 명령 변환과 차량 상태 인터페이스"),
    ("Control", "Simulator", "사용", "제어 명령을 차량 운동으로 반영하고 위치·속도·가속도를 피드백"),
    ("Control", "AD API", "사용", "RViz와 외부 도구의 Route·운전 모드 요청을 Autoware 내부 인터페이스로 연결"),
]

COMMUNICATION_HEADERS = (
    "송신 파티션",
    "수신 파티션",
    "송신 컴포넌트",
    "수신 컴포넌트",
    "송신 패키지",
    "수신 패키지",
    "송신 노드 이름",
    "수신 노드 이름",
    "토픽",
)

COLORS = {
    "navy": 0x23344A,
    "dark": 0x263238,
    "white": 0xFFFFFF,
    "line": 0xCBD5E1,
    "light": 0xF5F7FA,
    "perception": 0xD8F0EA,
    "perception_dark": 0x147D70,
    "decision": 0xFFF0C9,
    "decision_dark": 0xA56600,
    "control": 0xDCEAF8,
    "control_dark": 0x2C6FA3,
    "rviz": 0xECE2F5,
    "rviz_dark": 0x76528F,
    "feedback": 0xE7EAED,
    "feedback_dark": 0x58636B,
    "safety": 0xF9DEDE,
    "safety_dark": 0xA33A3A,
    "green": 0xDFF1DC,
}


def prop(name: str, value):
    item = PropertyValue()
    item.Name = name
    item.Value = value
    return item


def connect_office():
    profile = Path(tempfile.mkdtemp(prefix="partition_xlsx_lo_"))
    home = profile / "home"
    home.mkdir()
    env = os.environ.copy()
    env["HOME"] = str(home)
    port = 20000 + os.getpid() % 20000
    accept = f"socket,host=127.0.0.1,port={port};urp;StarOffice.ComponentContext"
    user_profile_url = uno.systemPathToFileUrl(str((profile / "profile").resolve()))
    process = subprocess.Popen(
        [
            "libreoffice",
            "--headless",
            f"--accept={accept}",
            "--norestore",
            "--nodefault",
            "--nolockcheck",
            f"-env:UserInstallation={user_profile_url}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )

    local_ctx = uno.getComponentContext()
    resolver = local_ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local_ctx
    )
    url = f"uno:socket,host=127.0.0.1,port={port};urp;StarOffice.ComponentContext"
    for _ in range(80):
        try:
            ctx = resolver.resolve(url)
            desktop = ctx.ServiceManager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", ctx
            )
            return desktop, process, profile
        except Exception:
            if process.poll() is not None:
                raise RuntimeError("LibreOffice failed to start")
            time.sleep(0.1)
    process.terminate()
    raise RuntimeError("Timed out while connecting to LibreOffice")


def set_text(cell, value):
    if value is None:
        value = ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        cell.Value = float(value)
    else:
        cell.String = str(value)


def set_rows(sheet, start_row: int, rows):
    for r, values in enumerate(rows, start=start_row):
        for c, value in enumerate(values):
            set_text(sheet.getCellByPosition(c, r), value)


def style_range(cell_range, *, bg=None, fg=None, bold=None, size=None, center=False):
    cell_range.CharFontName = "Malgun Gothic"
    cell_range.CharFontNameAsian = "Malgun Gothic"
    cell_range.IsTextWrapped = True
    cell_range.VertJustify = 2
    if bg is not None:
        cell_range.CellBackColor = bg
    if fg is not None:
        cell_range.CharColor = fg
    if bold is not None:
        cell_range.CharWeight = 150.0 if bold else 100.0
    if size is not None:
        cell_range.CharHeight = float(size)
    if center:
        cell_range.HoriJustify = 2


def add_borders(cell_range):
    line = BorderLine2()
    line.Color = COLORS["line"]
    line.OuterLineWidth = 18
    cell_range.TopBorder = line
    cell_range.BottomBorder = line
    cell_range.LeftBorder = line
    cell_range.RightBorder = line


def merge_text(sheet, name: str, text: str, *, bg, fg=COLORS["white"], size=12, bold=True):
    cell_range = sheet.getCellRangeByName(name)
    cell_range.merge(True)
    set_text(cell_range.getCellByPosition(0, 0), text)
    style_range(cell_range, bg=bg, fg=fg, bold=bold, size=size, center=True)
    add_borders(cell_range)


def setup_table(doc, sheet, header_row: int, rows, widths, db_name: str):
    if not rows:
        return
    last_col = len(rows[0]) - 1
    last_row = header_row + len(rows) - 1
    table = sheet.getCellRangeByPosition(0, header_row, last_col, last_row)
    style_range(table, size=9)
    add_borders(table)
    header = sheet.getCellRangeByPosition(0, header_row, last_col, header_row)
    style_range(header, bg=COLORS["navy"], fg=COLORS["white"], bold=True, center=True)
    sheet.getRows().getByIndex(header_row).Height = 900
    for idx, width in enumerate(widths):
        sheet.getColumns().getByIndex(idx).Width = width
    try:
        db_ranges = doc.getDatabaseRanges()
        address = table.getRangeAddress()
        db_ranges.addNewByName(db_name, address)
        db_ranges.getByName(db_name).AutoFilter = True
    except Exception:
        pass
    try:
        doc.getCurrentController().setActiveSheet(sheet)
        doc.getCurrentController().freezeAtPosition(0, header_row + 1)
    except Exception:
        pass


def color_partition_rows(sheet, start_row: int, rows, partition_col: int = 0):
    mapping = {
        "Perception": (COLORS["perception"], COLORS["perception_dark"]),
        "Decision": (COLORS["decision"], COLORS["decision_dark"]),
        "Control": (COLORS["control"], COLORS["control_dark"]),
        "RViz": (COLORS["rviz"], COLORS["rviz_dark"]),
        "Feedback": (COLORS["feedback"], COLORS["feedback_dark"]),
        "공통": (COLORS["feedback"], COLORS["feedback_dark"]),
    }
    for i, row in enumerate(rows, start=start_row):
        key = str(row[partition_col]).split("(")[0].strip()
        bg, fg = mapping.get(key, (COLORS["light"], COLORS["dark"]))
        cell = sheet.getCellByPosition(partition_col, i)
        style_range(cell, bg=bg, fg=fg, bold=True, center=True)


def load_counts():
    if not METADATA.exists():
        return {}
    with METADATA.open(encoding="utf-8") as stream:
        info = yaml.safe_load(stream)["rosbag2_bagfile_information"]
    return {
        item["topic_metadata"]["name"]: item["message_count"]
        for item in info["topics_with_message_count"]
    }


def component_from_path(path: str) -> str:
    parts = Path(path).parts
    if path.startswith("src/param"):
        return "Common / Parameter"
    if "obigo_launch" in parts:
        return "Partition Launch"
    if path.startswith(("src/sensor_component", "src/sensor_kit")):
        return "Sensing"
    if path.startswith("src/vehicle"):
        return "Vehicle Interface"
    if "autoware.universe" in parts:
        index = parts.index("autoware.universe")
        if len(parts) > index + 1:
            area = parts[index + 1]
            return {
                "map": "Map",
                "sensing": "Sensing",
                "localization": "Localization",
                "perception": "Perception",
                "visualization": "Visualization / RViz",
                "planning": "Planning",
                "system": "System",
                "control": "Control",
                "vehicle": "Vehicle Interface",
                "simulator": "Simulator",
            }.get(area, "Common / Dependency")
    return "Common / Dependency"


def read_package_name(package_xml: Path) -> str:
    root = ET.parse(package_xml).getroot()
    name = root.find("name")
    if name is None or not name.text:
        raise RuntimeError(f"Package name not found: {package_xml}")
    return name.text.strip()


def package_index():
    result = {}
    for package_xml in ROOT.glob("src/**/package.xml"):
        name = read_package_name(package_xml)
        result.setdefault(name, []).append(package_xml.parent)
    return result


def load_partition_inventory():
    index = package_index()
    component_rows = []
    package_rows = []

    for config_path in sorted(CONFIG_DIR.glob("*.json")):
        config = json.loads(config_path.read_text(encoding="utf-8"))
        partition = PARTITION_NAMES.get(config_path.stem, config_path.stem)
        included = {}

        for folder in config.get("folders", []):
            package_dirs = sorted((ROOT / folder).glob("**/package.xml"))
            component = component_from_path(folder)
            component_rows.append(
                (
                    partition,
                    component,
                    folder,
                    len(package_dirs),
                    COMPONENT_ROLES[component],
                    config_path.relative_to(ROOT).as_posix(),
                )
            )
            for package_xml in package_dirs:
                name = read_package_name(package_xml)
                path = package_xml.parent.relative_to(ROOT).as_posix()
                included.setdefault(name, {"paths": set(), "methods": set()})
                included[name]["paths"].add(path)
                included[name]["methods"].add("folders")

        for name in config.get("packages", []):
            paths = index.get(name, [])
            if not paths:
                included.setdefault(name, {"paths": {"외부/미확인"}, "methods": set()})
            for package_path in paths or ():
                path = package_path.relative_to(ROOT).as_posix()
                included.setdefault(name, {"paths": set(), "methods": set()})
                included[name]["paths"].add(path)
            included[name]["methods"].add("packages")

        for name, info in sorted(included.items()):
            for path in sorted(info["paths"]):
                component = component_from_path(path)
                methods = info["methods"]
                if methods == {"folders", "packages"}:
                    method = "컴포넌트 폴더 + 보완 목록"
                elif methods == {"folders"}:
                    method = "컴포넌트 폴더"
                else:
                    method = "보완 packages"
                package_rows.append(
                    (
                        partition,
                        component,
                        name,
                        path,
                        method,
                        config_path.relative_to(ROOT).as_posix(),
                    )
                )

    return component_rows, package_rows


MODULE_ROWS = [
    ("Perception", "UI / RViz", "rviz2 + tier4_dummy_object_rviz_plugin", "활성", "/map/*\n/tf\n/perception/*\n/planning/*", "/simulation/dummy_perception_publisher/object_info\n/initialpose3d\n/planning/mission_planning/goal", "지도·객체·경로 시각화, 초기 자세·목적지·더미 객체 입력", "obigo_launch/rviz/autoware.rviz"),
    ("Perception", "Global", "autoware_global_parameter_loader", "활성", "vehicle model, use_sim_time", "전역 ROS parameter", "세 파티션 공통 파라미터 로드", "adsw_perception.launch.xml"),
    ("Perception", "Map", "tier4_map_launch", "활성", "lanelet2_map.osm\npointcloud_map.pcd", "/map/vector_map\n/map/pointcloud_map\n/tf_static", "Lanelet2 및 pointcloud map 로드", "tier4_map_component.launch.xml"),
    ("Perception", "Sensing", "tier4_sensing_launch", "비활성", "센서 설정", "/sensing/*", "planning_simulator 실행 모드에서는 launch_sensing=false로 실행하지 않음", "planning_simulator.launch.xml"),
    ("Perception", "Localization", "tier4_localization_launch", "비활성", "/initialpose3d\n/tf", "/localization/*", "planning_simulator 실행 모드에서는 launch_localization=false이며 차량 상태는 Control simulator가 발행", "planning_simulator.launch.xml"),
    ("Perception", "Dummy detection", "autoware_dummy_perception_publisher", "활성", "/simulation/dummy_perception_publisher/object_info\n/tf", "/perception/object_recognition/detection/labeled_clusters\n/perception/obstacle_segmentation/pointcloud\n/simulation/dummy_perception_publisher/output/debug/ground_truth_objects", "RViz DummyObject를 모의 검출 객체와 pointcloud로 변환", "dummy_perception_publisher.launch.xml"),
    ("Perception", "Shape", "autoware_shape_estimation", "활성", "/perception/object_recognition/detection/labeled_clusters", "/perception/object_recognition/detection/objects_with_feature", "클러스터 기반 객체 형상 추정", "dummy_perception_publisher.launch.xml"),
    ("Perception", "Detection", "autoware_detected_object_feature_remover", "활성", "/perception/object_recognition/detection/objects_with_feature", "/perception/object_recognition/detection/objects", "feature 포함 객체를 표준 DetectedObjects로 변환", "dummy_perception_publisher.launch.xml"),
    ("Perception", "Tracking", "autoware_multi_object_tracker", "활성", "/perception/object_recognition/detection/objects", "/perception/object_recognition/tracking/objects", "프레임 간 객체 ID·위치·속도 추적", "perception_simulator_component.launch.xml"),
    ("Perception", "Prediction", "autoware_map_based_prediction", "활성", "/perception/object_recognition/tracking/objects\n/map/vector_map", "/perception/object_recognition/objects", "추적 객체의 미래 경로를 PredictedObjects로 생성", "perception_simulator_component.launch.xml"),
    ("Perception", "Perception stack", "tier4_perception_launch", "비활성", "/sensing/*\n/map/vector_map", "/perception/*", "planning_simulator 실행 모드에서는 launch_perception=false이며 더미 Perception 파이프라인이 객체 인식을 대신함", "planning_simulator.launch.xml"),
    ("Perception", "Simulation helper", "obigo_launch planning_sim helpers", "활성", "simulation state", "/perception/occupancy_grid_map/map\n/localization state helper", "Planning simulation에 필요한 빈 occupancy grid와 상태 보조", "perception_simulator_component.launch.xml"),
    ("Decision", "System", "tier4_system_launch", "활성", "/diagnostics\n노드 상태", "/autoware/state\n/system/*", "상태·진단·중복 노드·처리 시간 관리", "tier4_system_component.launch.xml"),
    ("Decision", "Mission planning", "autoware_mission_planner_universe", "활성", "/planning/mission_planning/goal\n/map/vector_map\n/localization/kinematic_state", "/planning/mission_planning/route", "목적지까지 LaneletRoute 생성", "mission_planner.launch.xml"),
    ("Decision", "Route interface", "autoware_mission_planner_universe/RouteSelector", "활성", "set_waypoint_route\nset_lanelet_route service", "/planning/mission_planning/route", "Main/MRM route 요청 선택 및 전달", "mission_planner.launch.xml"),
    ("Decision", "Behavior path", "autoware_behavior_path_planner", "활성", "/planning/mission_planning/route\n/map/vector_map\n/perception/object_recognition/objects\n/localization/kinematic_state", "/planning/scenario_planning/lane_driving/behavior_planning/path_with_lane_id", "차선 수준 path, 정적 장애물 회피와 차선 변경 판단", "behavior_planning.launch.xml"),
    ("Decision", "Behavior velocity", "autoware_behavior_velocity_planner", "활성", "/planning/scenario_planning/lane_driving/behavior_planning/path_with_lane_id\n/perception/object_recognition/objects\n/perception/obstacle_segmentation/pointcloud", "/planning/scenario_planning/lane_driving/behavior_planning/path", "교차로·횡단보도 등 행동 속도와 정지 반영", "behavior_planning.launch.xml"),
    ("Decision", "Path smoothing", "autoware_path_smoother", "활성", "/planning/scenario_planning/lane_driving/behavior_planning/path", "/planning/scenario_planning/lane_driving/motion_planning/path_smoother/path", "Elastic Band 기반 경로 평활화", "motion_planning.launch.xml"),
    ("Decision", "Path optimization", "autoware_path_optimizer", "활성", "/planning/scenario_planning/lane_driving/motion_planning/path_smoother/path\n/localization/kinematic_state", "/planning/scenario_planning/lane_driving/motion_planning/path_optimizer/trajectory", "차량 운동학을 고려한 trajectory 생성", "motion_planning.launch.xml"),
    ("Decision", "Motion velocity", "autoware_motion_velocity_planner_node_universe", "활성", "/planning/scenario_planning/lane_driving/motion_planning/path_optimizer/trajectory\n/perception/object_recognition/objects\n/perception/obstacle_segmentation/pointcloud\n/localization/kinematic_state", "/planning/scenario_planning/lane_driving/motion_planning/motion_velocity_planner/trajectory", "동적 장애물 정지와 속도 제한 반영", "motion_planning.launch.xml"),
    ("Decision", "Obstacle cruise", "autoware_obstacle_cruise_planner", "활성", "trajectory\nPredictedObjects\npointcloud\nodometry", "/planning/scenario_planning/lane_driving/trajectory", "전방 객체 감속·정지·추종 속도 반영", "motion_planning.launch.xml"),
    ("Decision", "Scenario", "autoware_scenario_selector", "활성", "/planning/scenario_planning/lane_driving/trajectory\n/planning/scenario_planning/parking/trajectory", "/planning/scenario_planning/scenario_selector/trajectory", "차선 주행 또는 주차 trajectory 선택", "scenario_planning.launch.xml"),
    ("Decision", "Velocity smoothing", "autoware_velocity_smoother", "활성", "/planning/scenario_planning/scenario_selector/trajectory\n/localization/acceleration", "/planning/scenario_planning/velocity_smoother/trajectory", "속도·가속도·jerk 제한 평활화", "scenario_planning.launch.xml"),
    ("Decision", "Validation", "autoware_planning_validator", "활성", "velocity_smoother/trajectory", "/planning/scenario_planning/trajectory", "최종 trajectory 유효성 검사 후 Control로 발행", "planning.launch.xml"),
    ("Decision", "Evaluation", "autoware_planning_evaluator", "활성", "planning topics", "/planning/planning_evaluator/*", "Planning 결과 평가 및 metric", "planning.launch.xml"),
    ("Control", "Vehicle", "tier4_vehicle_launch", "활성", "/control/command/*", "/vehicle/status/*", "차량 인터페이스 및 차량 상태 계층", "adsw_control.launch.xml"),
    ("Control", "Trajectory following", "autoware_trajectory_follower_node", "활성", "/planning/scenario_planning/trajectory\n/localization/kinematic_state\n/vehicle/status/steering_status\n/localization/acceleration", "/control/trajectory_follower/control_cmd\n/control/trajectory_follower/lateral/predicted_trajectory", "기준 trajectory와 차량 상태 오차로 조향·가감속 명령 생성", "control.launch.xml"),
    ("Control", "Shift", "autoware_shift_decider", "활성", "trajectory follower cmd\n/autoware/state", "/control/shift_decider/gear_cmd", "주행 상태에 맞는 기어 결정", "control.launch.xml"),
    ("Control", "Command gate", "autoware_vehicle_cmd_gate", "활성", "auto/external/emergency cmd\noperation mode", "/control/command/control_cmd\ngear/turn/hazard cmd", "운전 모드와 emergency 상태를 반영해 최종 차량 명령 선택", "control.launch.xml"),
    ("Control", "Operation mode", "autoware_operation_mode_transition_manager", "활성", "trajectory\ncontrol cmd\nvehicle status", "/control/is_autonomous_available\n/control/control_mode_request", "Auto 활성 가능 여부와 모드 전환 관리", "control.launch.xml"),
    ("Control", "Safety / AEB", "autoware_autonomous_emergency_braking", "활성", "pointcloud\nvelocity\nIMU\npredicted trajectory", "AEB metric\nvirtual wall", "주 경로와 별도의 긴급 제동 감시. 현재 pointcloud 사용", "control.launch.xml"),
    ("Control", "Safety", "autoware_collision_detector", "활성", "PredictedObjects\npointcloud\nodometry", "collision diagnostics", "현재 차량 주변 충돌 위험 감시", "control.launch.xml"),
    ("Control", "Safety", "autoware_obstacle_collision_checker", "비활성", "trajectory\npointcloud\nodometry", "collision check result", "현재 구성에서는 실행하지 않음", "control.launch.xml"),
    ("Control", "Safety", "autoware_predicted_path_checker", "비활성", "PredictedObjects\ntrajectory\nodometry", "path check result", "현재 구성에서는 실행하지 않음", "control.launch.xml"),
    ("Control", "API", "tier4_autoware_api_launch", "활성", "API service request", "/api/*", "RViz 및 외부 도구의 Autoware 상태·모드 API 제공", "tier4_autoware_api_component.launch.xml"),
    ("Control", "Vehicle simulation", "autoware_simple_planning_simulator", "활성", "/control/command/control_cmd\ngear cmd\n/initialpose3d", "/localization/kinematic_state\n/localization/acceleration\n/vehicle/status/*\n/tf", "제어 명령을 차량 운동으로 반영하고 상태를 피드백", "simple_planning_simulator.launch.py"),
]


NODE_DETAILS = {
    ("Perception", "UI / RViz"): ("Visualization / RViz", "rviz2; tier4_dummy_object_rviz_plugin", "/rviz2"),
    ("Perception", "Global"): ("Common / Parameter", "autoware_global_parameter_loader", "노드 없음 (launch parameter 설정)"),
    ("Perception", "Map"): ("Map", "tier4_map_launch", "map loader/visualizer 노드 그룹"),
    ("Perception", "Sensing"): ("Sensing", "tier4_sensing_launch", "sensing 노드 그룹"),
    ("Perception", "Localization"): ("Localization", "tier4_localization_launch", "localization 노드 그룹"),
    ("Perception", "Dummy detection"): ("Perception", "autoware_dummy_perception_publisher", "/simulation/dummy_perception_publisher"),
    ("Perception", "Shape"): ("Perception", "autoware_shape_estimation", "/simulation/shape_estimation"),
    ("Perception", "Detection"): ("Perception", "autoware_detected_object_feature_remover", "/simulation/detected_object_feature_remover"),
    ("Perception", "Tracking"): ("Perception", "autoware_multi_object_tracker", "/perception/object_recognition/multi_object_tracker"),
    ("Perception", "Prediction"): ("Perception", "autoware_map_based_prediction", "/perception/object_recognition/map_based_prediction"),
    ("Perception", "Perception stack"): ("Perception", "tier4_perception_launch", "perception 노드 그룹"),
    ("Perception", "Simulation helper"): ("Simulator", "obigo_launch", "planning_sim_empty_occupancy_grid; planning_sim_localization_state"),
    ("Decision", "System"): ("System", "tier4_system_launch", "system 노드 그룹"),
    ("Decision", "Mission planning"): ("Planning", "autoware_mission_planner_universe", "mission_planner"),
    ("Decision", "Route interface"): ("Planning", "autoware_mission_planner_universe", "route_selector"),
    ("Decision", "Behavior path"): ("Planning", "autoware_behavior_path_planner", "/planning/scenario_planning/lane_driving/behavior_planning/behavior_path_planner"),
    ("Decision", "Behavior velocity"): ("Planning", "autoware_behavior_velocity_planner", "/planning/scenario_planning/lane_driving/behavior_planning/behavior_velocity_planner"),
    ("Decision", "Path smoothing"): ("Planning", "autoware_path_smoother", "/planning/scenario_planning/lane_driving/motion_planning/elastic_band_smoother"),
    ("Decision", "Path optimization"): ("Planning", "autoware_path_optimizer", "/planning/scenario_planning/lane_driving/motion_planning/path_optimizer"),
    ("Decision", "Motion velocity"): ("Planning", "autoware_motion_velocity_planner_node_universe", "/planning/scenario_planning/lane_driving/motion_planning/motion_velocity_planner"),
    ("Decision", "Obstacle cruise"): ("Planning", "autoware_obstacle_cruise_planner", "/planning/scenario_planning/lane_driving/motion_planning/obstacle_cruise_planner"),
    ("Decision", "Scenario"): ("Planning", "autoware_scenario_selector", "/planning/scenario_planning/scenario_selector"),
    ("Decision", "Velocity smoothing"): ("Planning", "autoware_velocity_smoother", "/planning/scenario_planning/velocity_smoother"),
    ("Decision", "Validation"): ("Planning", "autoware_planning_validator", "/planning/planning_validator"),
    ("Decision", "Evaluation"): ("Planning", "autoware_planning_evaluator", "planning_evaluator"),
    ("Control", "Vehicle"): ("Vehicle Interface", "tier4_vehicle_launch", "vehicle interface 노드 그룹"),
    ("Control", "Trajectory following"): ("Control", "autoware_trajectory_follower_node", "/control/trajectory_follower/controller_node_exe"),
    ("Control", "Shift"): ("Control", "autoware_shift_decider", "shift_decider"),
    ("Control", "Command gate"): ("Control", "autoware_vehicle_cmd_gate", "/control/vehicle_cmd_gate"),
    ("Control", "Operation mode"): ("Control", "autoware_operation_mode_transition_manager", "operation_mode_transition_manager"),
    ("Control", "Safety / AEB"): ("Control", "autoware_autonomous_emergency_braking", "/control/autonomous_emergency_braking"),
    ("Control", "Safety"): ("Control", "복수 안전 패키지", "collision_detector / obstacle_collision_checker / predicted_path_checker"),
    ("Control", "API"): ("Control", "tier4_autoware_api_launch", "AD API 노드 그룹"),
    ("Control", "Vehicle simulation"): ("Simulator", "autoware_simple_planning_simulator", "/simulation/simple_planning_simulator"),
}


def node_rows():
    rows = []
    for partition, function, old, status, inputs, outputs, role, evidence in MODULE_ROWS:
        component, package, node = NODE_DETAILS[(partition, function)]
        if partition == "Control" and function == "Safety":
            package = old
            node = old.removeprefix("autoware_")
        rows.append(
            (
                partition,
                component,
                function,
                package,
                node,
                status,
                inputs,
                outputs,
                role,
                evidence,
            )
        )
    return rows


TOPIC_ROWS_BASE = [
    ("T01", "RViz", "Dummy object", "/simulation/dummy_perception_publisher/object_info", "tier4_simulation_msgs/msg/DummyObject", "RViz dummy object plugin", "Perception dummy_perception_publisher", "RViz -> Perception", "주 경로", "ADD/MODIFY/DELETE/DELETEALL"),
    ("T02", "Perception", "Ground truth debug", "/simulation/dummy_perception_publisher/output/debug/ground_truth_objects", "autoware_perception_msgs/msg/TrackedObjects", "dummy_perception_publisher", "RViz / debug", "Perception 내부", "검증", "모의 객체 ground truth"),
    ("T03", "Perception", "Pointcloud", "/perception/obstacle_segmentation/pointcloud", "sensor_msgs/msg/PointCloud2", "dummy_perception_publisher", "Decision planners, Control AEB/checkers", "Perception -> Decision/Control", "주 경로 + 안전", "더미 객체 점군"),
    ("T04", "Perception", "Detection", "/perception/object_recognition/detection/labeled_clusters", "tier4_perception_msgs/msg/DetectedObjectsWithFeature", "dummy_perception_publisher", "shape_estimation", "Perception 내부", "주 경로", "초기 모의 검출"),
    ("T05", "Perception", "Shape", "/perception/object_recognition/detection/objects_with_feature", "tier4_perception_msgs/msg/DetectedObjectsWithFeature", "shape_estimation", "feature_remover", "Perception 내부", "주 경로", "형상 추정 결과"),
    ("T06", "Perception", "Detection", "/perception/object_recognition/detection/objects", "autoware_perception_msgs/msg/DetectedObjects", "feature_remover", "multi_object_tracker", "Perception 내부", "주 경로", "표준 검출 객체"),
    ("T07", "Perception", "Tracking", "/perception/object_recognition/tracking/objects", "autoware_perception_msgs/msg/TrackedObjects", "multi_object_tracker", "map_based_prediction", "Perception 내부", "주 경로", "ID·속도 포함 추적 객체"),
    ("T08", "Perception", "Prediction", "/perception/object_recognition/objects", "autoware_perception_msgs/msg/PredictedObjects", "map_based_prediction", "Decision planners, Control safety, RViz", "Perception -> Decision/Control", "주 경로 + 안전", "Perception 대표 객체 출력"),
    ("T09", "Perception", "Map", "/map/vector_map", "autoware_map_msgs/msg/LaneletMapBin", "map loader", "Perception prediction, Decision planners, simulator", "Perception -> 전체", "공통 입력", "Lanelet2 HD Map"),
    ("T10", "RViz", "Localization input", "/initialpose3d", "geometry_msgs/msg/PoseWithCovarianceStamped", "RViz Initial Pose", "Localization, simple simulator", "RViz -> Perception/Control", "초기화", "차량 초기 자세"),
    ("T11", "RViz", "Mission input", "/planning/mission_planning/goal", "geometry_msgs/msg/PoseStamped", "RViz Goal", "Mission planner", "RViz -> Decision", "경로 생성", "목적지 입력"),
    ("T12", "Decision", "Mission planning", "/planning/mission_planning/route", "autoware_planning_msgs/msg/LaneletRoute", "mission_planner", "Behavior path planner, scenario selector, RViz", "Decision 내부/출력", "경로 기반", "전역 route. 장애물 추가만으로 재생성되지 않음"),
    ("T13", "Decision", "Behavior path", "/planning/scenario_planning/lane_driving/behavior_planning/path_with_lane_id", "tier4_planning_msgs/msg/PathWithLaneId", "behavior_path_planner", "behavior_velocity_planner", "Decision 내부", "주 경로", "차선 ID 포함 지역 path"),
    ("T14", "Decision", "Behavior velocity", "/planning/scenario_planning/lane_driving/behavior_planning/path", "autoware_planning_msgs/msg/Path", "behavior_velocity_planner", "path_smoother", "Decision 내부", "주 경로", "행동 속도와 정지 반영"),
    ("T15", "Decision", "Path smoothing", "/planning/scenario_planning/lane_driving/motion_planning/path_smoother/path", "autoware_planning_msgs/msg/Path", "path_smoother", "path_optimizer", "Decision 내부", "주 경로", "평활화 경로"),
    ("T16", "Decision", "Path optimization", "/planning/scenario_planning/lane_driving/motion_planning/path_optimizer/trajectory", "autoware_planning_msgs/msg/Trajectory", "path_optimizer", "motion_velocity_planner", "Decision 내부", "주 경로", "운동학적 trajectory"),
    ("T17", "Decision", "Motion velocity", "/planning/scenario_planning/lane_driving/motion_planning/motion_velocity_planner/trajectory", "autoware_planning_msgs/msg/Trajectory", "motion_velocity_planner", "obstacle_cruise_planner", "Decision 내부", "주 경로", "장애물 속도 제약 반영"),
    ("T18", "Decision", "Obstacle cruise", "/planning/scenario_planning/lane_driving/trajectory", "autoware_planning_msgs/msg/Trajectory", "obstacle_cruise_planner", "scenario_selector", "Decision 내부", "주 경로", "차선 주행 trajectory"),
    ("T19", "Decision", "Scenario", "/planning/scenario_planning/scenario_selector/trajectory", "autoware_planning_msgs/msg/Trajectory", "scenario_selector", "velocity_smoother", "Decision 내부", "주 경로", "선택된 시나리오 trajectory"),
    ("T20", "Decision", "Velocity smoothing", "/planning/scenario_planning/velocity_smoother/trajectory", "autoware_planning_msgs/msg/Trajectory", "velocity_smoother", "planning_validator", "Decision 내부", "주 경로", "속도·가속도·jerk 평활화"),
    ("T21", "Decision", "Final planning", "/planning/scenario_planning/trajectory", "autoware_planning_msgs/msg/Trajectory", "planning_validator", "Control trajectory_follower, simulator", "Decision -> Control", "주 경로", "Control의 최종 기준 trajectory"),
    ("T22", "Decision", "Avoidance debug", "/planning/path_candidate/static_obstacle_avoidance", "autoware_planning_msgs/msg/Path", "behavior_path_planner", "RViz / debug", "Decision 내부", "진단", "정적 장애물 회피 후보 path"),
    ("T23", "Decision", "Avoidance factor", "/planning/planning_factors/static_obstacle_avoidance", "tier4_planning_msgs/msg/PlanningFactorArray", "behavior_path_planner", "RViz / debug", "Decision 내부", "진단", "회피 판단 factor"),
    ("T24", "Control", "Trajectory follower", "/control/trajectory_follower/control_cmd", "autoware_control_msgs/msg/Control", "trajectory_follower", "vehicle_cmd_gate, shift_decider", "Control 내부", "주 경로", "제어기 원시 조향·가감속 명령"),
    ("T25", "Control", "Final command", "/control/command/control_cmd", "autoware_control_msgs/msg/Control", "vehicle_cmd_gate", "simple_planning_simulator", "Control -> Simulator", "주 경로", "최종 차량 제어 명령"),
    ("T26", "Control", "AEB", "/control/autonomous_emergency_braking/metrics", "tier4_metric_msgs/msg/MetricArray", "AEB", "debug / evaluator", "Control 내부", "병렬 안전", "AEB 판단 metric"),
    ("T27", "Control", "AEB", "/control/autonomous_emergency_braking/virtual_wall", "visualization_msgs/msg/MarkerArray", "AEB", "RViz", "Control -> RViz", "병렬 안전", "AEB 정지 위치 표시"),
    ("T28", "Control", "Operation mode", "/api/operation_mode/state", "autoware_adapi_v1_msgs/msg/OperationModeState", "Autoware API", "RViz / external client", "Control -> RViz", "상태", "Auto 상태"),
    ("T29", "Control", "Vehicle feedback", "/localization/kinematic_state", "nav_msgs/msg/Odometry", "simple_planning_simulator", "Decision planners, Control", "Control -> Decision/Control", "피드백", "차량 pose·속도"),
    ("T30", "Control", "Vehicle feedback", "/localization/acceleration", "geometry_msgs/msg/AccelWithCovarianceStamped", "simple_planning_simulator", "Decision planners, Control", "Control -> Decision/Control", "피드백", "차량 가속도"),
    ("T31", "Control", "Vehicle feedback", "/vehicle/status/velocity_status", "autoware_vehicle_msgs/msg/VelocityReport", "simple_planning_simulator", "Control / state manager", "Control 내부", "피드백", "차량 속도 보고"),
    ("T32", "Control", "Vehicle feedback", "/vehicle/status/steering_status", "autoware_vehicle_msgs/msg/SteeringReport", "simple_planning_simulator", "trajectory_follower / state manager", "Control 내부", "피드백", "현재 조향각"),
    ("T33", "Control", "Vehicle feedback", "/vehicle/status/control_mode", "autoware_vehicle_msgs/msg/ControlModeReport", "simple_planning_simulator", "operation mode manager", "Control 내부", "피드백", "차량 제어 모드"),
    ("T34", "공통", "TF", "/tf", "tf2_msgs/msg/TFMessage", "simple simulator 및 TF nodes", "전체 파티션, RViz", "공통", "피드백", "차량 좌표계 갱신"),
    ("T35", "공통", "TF", "/tf_static", "tf2_msgs/msg/TFMessage", "map/static TF nodes", "전체 파티션, RViz", "공통", "공통 입력", "정적 좌표계"),
    ("T36", "Decision", "System state", "/autoware/state", "autoware_system_msgs/msg/AutowareState", "system state monitor", "Control, RViz", "Decision -> Control/RViz", "상태", "Autoware 상태"),
]


CONNECTION_ROWS = [
    (
        "P01", "주 경로",
        "Perception 또는 외부 PC RViz", "Visualization / RViz",
        "tier4_dummy_object_rviz_plugin", "/rviz2", "Publisher",
        "/simulation/dummy_perception_publisher/object_info",
        "tier4_simulation_msgs/msg/DummyObject",
        "Perception", "Perception",
        "autoware_dummy_perception_publisher", "/simulation/dummy_perception_publisher",
        "Subscription", "/simulation/dummy_perception_publisher/object_info",
        "사용자가 배치·이동·삭제한 더미 객체를 모의 센서 객체로 변환",
        "src/universe/autoware.universe/simulator/autoware_dummy_perception_publisher/launch/dummy_perception_publisher.launch.xml",
    ),
    (
        "P02", "주 경로",
        "Perception", "Perception",
        "autoware_dummy_perception_publisher", "/simulation/dummy_perception_publisher", "Publisher",
        "/perception/object_recognition/detection/labeled_clusters",
        "tier4_perception_msgs/msg/DetectedObjectsWithFeature",
        "Perception", "Perception",
        "autoware_shape_estimation", "/simulation/shape_estimation",
        "Subscription", "/perception/object_recognition/detection/labeled_clusters",
        "검출 클러스터의 객체 형상을 추정",
        "src/universe/autoware.universe/simulator/autoware_dummy_perception_publisher/launch/dummy_perception_publisher.launch.xml",
    ),
    (
        "P03", "주 경로",
        "Perception", "Perception",
        "autoware_shape_estimation", "/simulation/shape_estimation", "Publisher",
        "/perception/object_recognition/detection/objects_with_feature",
        "tier4_perception_msgs/msg/DetectedObjectsWithFeature",
        "Perception", "Perception",
        "autoware_detected_object_feature_remover", "/simulation/detected_object_feature_remover",
        "Subscription", "/perception/object_recognition/detection/objects_with_feature",
        "형상 정보가 포함된 검출 객체에서 특징 필드를 제거할 준비",
        "src/universe/autoware.universe/simulator/autoware_dummy_perception_publisher/launch/dummy_perception_publisher.launch.xml",
    ),
    (
        "P04", "주 경로",
        "Perception", "Perception",
        "autoware_detected_object_feature_remover", "/simulation/detected_object_feature_remover", "Publisher",
        "/perception/object_recognition/detection/objects",
        "autoware_perception_msgs/msg/DetectedObjects",
        "Perception", "Perception",
        "autoware_multi_object_tracker", "/perception/object_recognition/multi_object_tracker",
        "Subscription", "/perception/object_recognition/detection/objects",
        "프레임 사이의 객체를 연결하여 식별자·위치·속도를 추적",
        "src/universe/autoware.universe/obigo_launch/launch/components/perception_simulator_component.launch.xml",
    ),
    (
        "P05", "주 경로",
        "Perception", "Perception",
        "autoware_multi_object_tracker", "/perception/object_recognition/multi_object_tracker", "Publisher",
        "/perception/object_recognition/tracking/objects",
        "autoware_perception_msgs/msg/TrackedObjects",
        "Perception", "Perception",
        "autoware_map_based_prediction", "/perception/object_recognition/map_based_prediction",
        "Subscription", "/perception/object_recognition/tracking/objects",
        "지도와 추적 결과를 사용하여 객체의 미래 경로를 예측",
        "src/universe/autoware.universe/obigo_launch/launch/components/perception_simulator_component.launch.xml",
    ),
    (
        "P06", "장애물 입력",
        "Perception", "Perception",
        "autoware_map_based_prediction", "/perception/object_recognition/map_based_prediction", "Publisher",
        "/perception/object_recognition/objects",
        "autoware_perception_msgs/msg/PredictedObjects",
        "Decision", "Planning",
        "autoware_behavior_path_planner",
        "/planning/scenario_planning/lane_driving/behavior_planning/behavior_path_planner",
        "Subscription", "/perception/object_recognition/objects",
        "차선 수준 경로와 정적 장애물 회피 가능성을 판단",
        "src/universe/autoware.universe/launch/tier4_planning_launch/launch/scenario_planning/lane_driving/behavior_planning/behavior_planning.launch.xml",
    ),
    (
        "P07", "장애물 입력",
        "Perception", "Perception",
        "autoware_map_based_prediction", "/perception/object_recognition/map_based_prediction", "Publisher",
        "/perception/object_recognition/objects",
        "autoware_perception_msgs/msg/PredictedObjects",
        "Decision", "Planning",
        "autoware_behavior_velocity_planner",
        "/planning/scenario_planning/lane_driving/behavior_planning/behavior_velocity_planner",
        "Subscription", "/perception/object_recognition/objects",
        "교차로·횡단보도 등 행동 규칙에 장애물 정보를 반영",
        "src/universe/autoware.universe/launch/tier4_planning_launch/launch/scenario_planning/lane_driving/behavior_planning/behavior_planning.launch.xml",
    ),
    (
        "P08", "장애물 입력",
        "Perception", "Perception",
        "autoware_map_based_prediction", "/perception/object_recognition/map_based_prediction", "Publisher",
        "/perception/object_recognition/objects",
        "autoware_perception_msgs/msg/PredictedObjects",
        "Decision", "Planning",
        "autoware_motion_velocity_planner_node_universe",
        "/planning/scenario_planning/lane_driving/motion_planning/motion_velocity_planner",
        "Subscription", "/perception/object_recognition/objects",
        "동적 장애물 정지와 속도 제한을 계산",
        "src/universe/autoware.universe/launch/tier4_planning_launch/launch/scenario_planning/lane_driving/motion_planning/motion_planning.launch.xml",
    ),
    (
        "P09", "장애물 입력",
        "Perception", "Perception",
        "autoware_map_based_prediction", "/perception/object_recognition/map_based_prediction", "Publisher",
        "/perception/object_recognition/objects",
        "autoware_perception_msgs/msg/PredictedObjects",
        "Decision", "Planning",
        "autoware_obstacle_cruise_planner",
        "/planning/scenario_planning/lane_driving/motion_planning/obstacle_cruise_planner",
        "Subscription", "/perception/object_recognition/objects",
        "전방 객체에 대한 감속·정지·추종 속도를 계산",
        "src/universe/autoware.universe/launch/tier4_planning_launch/launch/scenario_planning/lane_driving/motion_planning/motion_planning.launch.xml",
    ),
    (
        "P10", "장애물 입력",
        "Perception", "Perception",
        "autoware_dummy_perception_publisher", "/simulation/dummy_perception_publisher", "Publisher",
        "/perception/obstacle_segmentation/pointcloud",
        "sensor_msgs/msg/PointCloud2",
        "Decision", "Planning",
        "autoware_behavior_velocity_planner",
        "/planning/scenario_planning/lane_driving/behavior_planning/behavior_velocity_planner",
        "Subscription", "/perception/obstacle_segmentation/pointcloud",
        "모의 장애물 점군을 행동 속도 계획에 반영",
        "src/universe/autoware.universe/launch/tier4_planning_launch/launch/scenario_planning/lane_driving/behavior_planning/behavior_planning.launch.xml",
    ),
    (
        "P11", "장애물 입력",
        "Perception", "Perception",
        "autoware_dummy_perception_publisher", "/simulation/dummy_perception_publisher", "Publisher",
        "/perception/obstacle_segmentation/pointcloud",
        "sensor_msgs/msg/PointCloud2",
        "Decision", "Planning",
        "autoware_motion_velocity_planner_node_universe",
        "/planning/scenario_planning/lane_driving/motion_planning/motion_velocity_planner",
        "Subscription", "/perception/obstacle_segmentation/pointcloud",
        "모의 장애물 점군을 동적 장애물 정지 계산에 반영",
        "src/universe/autoware.universe/launch/tier4_planning_launch/launch/scenario_planning/lane_driving/motion_planning/motion_planning.launch.xml",
    ),
    (
        "P12", "장애물 입력",
        "Perception", "Perception",
        "autoware_dummy_perception_publisher", "/simulation/dummy_perception_publisher", "Publisher",
        "/perception/obstacle_segmentation/pointcloud",
        "sensor_msgs/msg/PointCloud2",
        "Decision", "Planning",
        "autoware_obstacle_cruise_planner",
        "/planning/scenario_planning/lane_driving/motion_planning/obstacle_cruise_planner",
        "Subscription", "/perception/obstacle_segmentation/pointcloud",
        "모의 장애물 점군을 전방 객체 감속·정지 계산에 반영",
        "src/universe/autoware.universe/launch/tier4_planning_launch/launch/scenario_planning/lane_driving/motion_planning/motion_planning.launch.xml",
    ),
    (
        "D01", "주 경로",
        "Decision", "Planning",
        "autoware_behavior_path_planner",
        "/planning/scenario_planning/lane_driving/behavior_planning/behavior_path_planner",
        "Publisher",
        "/planning/scenario_planning/lane_driving/behavior_planning/path_with_lane_id",
        "tier4_planning_msgs/msg/PathWithLaneId",
        "Decision", "Planning",
        "autoware_behavior_velocity_planner",
        "/planning/scenario_planning/lane_driving/behavior_planning/behavior_velocity_planner",
        "Subscription",
        "/planning/scenario_planning/lane_driving/behavior_planning/path_with_lane_id",
        "차선 식별자가 포함된 경로에 행동 속도와 정지 조건을 반영",
        "src/universe/autoware.universe/launch/tier4_planning_launch/launch/scenario_planning/lane_driving/behavior_planning/behavior_planning.launch.xml",
    ),
    (
        "D02", "주 경로",
        "Decision", "Planning",
        "autoware_behavior_velocity_planner",
        "/planning/scenario_planning/lane_driving/behavior_planning/behavior_velocity_planner",
        "Publisher",
        "/planning/scenario_planning/lane_driving/behavior_planning/path",
        "autoware_planning_msgs/msg/Path",
        "Decision", "Planning",
        "autoware_path_smoother",
        "/planning/scenario_planning/lane_driving/motion_planning/elastic_band_smoother",
        "Subscription",
        "/planning/scenario_planning/lane_driving/behavior_planning/path",
        "행동 계획 경로의 형상을 평활화",
        "src/universe/autoware.universe/launch/tier4_planning_launch/launch/scenario_planning/lane_driving/motion_planning/motion_planning.launch.xml",
    ),
    (
        "D03", "주 경로",
        "Decision", "Planning",
        "autoware_path_smoother",
        "/planning/scenario_planning/lane_driving/motion_planning/elastic_band_smoother",
        "Publisher",
        "/planning/scenario_planning/lane_driving/motion_planning/path_smoother/path",
        "autoware_planning_msgs/msg/Path",
        "Decision", "Planning",
        "autoware_path_optimizer",
        "/planning/scenario_planning/lane_driving/motion_planning/path_optimizer",
        "Subscription",
        "/planning/scenario_planning/lane_driving/motion_planning/path_smoother/path",
        "차량 운동학을 만족하는 궤적으로 최적화",
        "src/universe/autoware.universe/launch/tier4_planning_launch/launch/scenario_planning/lane_driving/motion_planning/motion_planning.launch.xml",
    ),
    (
        "D04", "주 경로",
        "Decision", "Planning",
        "autoware_path_optimizer",
        "/planning/scenario_planning/lane_driving/motion_planning/path_optimizer",
        "Publisher",
        "/planning/scenario_planning/lane_driving/motion_planning/path_optimizer/trajectory",
        "autoware_planning_msgs/msg/Trajectory",
        "Decision", "Planning",
        "autoware_motion_velocity_planner_node_universe",
        "/planning/scenario_planning/lane_driving/motion_planning/motion_velocity_planner",
        "Subscription",
        "/planning/scenario_planning/lane_driving/motion_planning/path_optimizer/trajectory",
        "최적화된 궤적에 장애물과 속도 제한을 반영",
        "src/universe/autoware.universe/launch/tier4_planning_launch/launch/scenario_planning/lane_driving/motion_planning/motion_planning.launch.xml",
    ),
    (
        "D05", "주 경로",
        "Decision", "Planning",
        "autoware_motion_velocity_planner_node_universe",
        "/planning/scenario_planning/lane_driving/motion_planning/motion_velocity_planner",
        "Publisher",
        "/planning/scenario_planning/lane_driving/motion_planning/motion_velocity_planner/trajectory",
        "autoware_planning_msgs/msg/Trajectory",
        "Decision", "Planning",
        "autoware_obstacle_cruise_planner",
        "/planning/scenario_planning/lane_driving/motion_planning/obstacle_cruise_planner",
        "Subscription",
        "/planning/scenario_planning/lane_driving/motion_planning/motion_velocity_planner/trajectory",
        "전방 객체 감속·정지·추종 속도를 최종 반영",
        "src/universe/autoware.universe/launch/tier4_planning_launch/launch/scenario_planning/lane_driving/motion_planning/motion_planning.launch.xml",
    ),
    (
        "D06", "주 경로",
        "Decision", "Planning",
        "autoware_obstacle_cruise_planner",
        "/planning/scenario_planning/lane_driving/motion_planning/obstacle_cruise_planner",
        "Publisher",
        "/planning/scenario_planning/lane_driving/trajectory",
        "autoware_planning_msgs/msg/Trajectory",
        "Decision", "Planning",
        "autoware_scenario_selector",
        "/planning/scenario_planning/scenario_selector",
        "Subscription",
        "/planning/scenario_planning/lane_driving/trajectory",
        "차선 주행과 주차 중 현재 시나리오의 궤적을 선택",
        "src/universe/autoware.universe/launch/tier4_planning_launch/launch/scenario_planning/scenario_planning.launch.xml",
    ),
    (
        "D07", "주 경로",
        "Decision", "Planning",
        "autoware_scenario_selector",
        "/planning/scenario_planning/scenario_selector",
        "Publisher",
        "/planning/scenario_planning/scenario_selector/trajectory",
        "autoware_planning_msgs/msg/Trajectory",
        "Decision", "Planning",
        "autoware_velocity_smoother",
        "/planning/scenario_planning/velocity_smoother",
        "Subscription",
        "/planning/scenario_planning/scenario_selector/trajectory",
        "선택된 궤적의 속도·가속도·가가속도를 평활화",
        "src/universe/autoware.universe/launch/tier4_planning_launch/launch/scenario_planning/scenario_planning.launch.xml",
    ),
    (
        "D08", "주 경로",
        "Decision", "Planning",
        "autoware_velocity_smoother",
        "/planning/scenario_planning/velocity_smoother",
        "Publisher",
        "/planning/scenario_planning/velocity_smoother/trajectory",
        "autoware_planning_msgs/msg/Trajectory",
        "Decision", "Planning",
        "autoware_planning_validator",
        "/planning/planning_validator",
        "Subscription",
        "/planning/scenario_planning/velocity_smoother/trajectory",
        "최종 궤적의 유효성을 검사",
        "src/universe/autoware.universe/launch/tier4_planning_launch/launch/planning.launch.xml",
    ),
    (
        "D09", "주 경로",
        "Decision", "Planning",
        "autoware_planning_validator",
        "/planning/planning_validator",
        "Publisher",
        "/planning/scenario_planning/trajectory",
        "autoware_planning_msgs/msg/Trajectory",
        "Control", "Control",
        "autoware_trajectory_follower_node",
        "/control/trajectory_follower/controller_node_exe",
        "Subscription",
        "/planning/scenario_planning/trajectory",
        "기준 궤적과 현재 차량 상태의 오차로 조향·가감속 명령을 계산",
        "src/universe/autoware.universe/launch/tier4_control_launch/launch/control.launch.xml",
    ),
    (
        "C01", "주 경로",
        "Control", "Control",
        "autoware_trajectory_follower_node",
        "/control/trajectory_follower/controller_node_exe",
        "Publisher",
        "/control/trajectory_follower/control_cmd",
        "autoware_control_msgs/msg/Control",
        "Control", "Control",
        "autoware_vehicle_cmd_gate",
        "/control/vehicle_cmd_gate",
        "Subscription",
        "/control/trajectory_follower/control_cmd",
        "자율·외부·긴급 명령과 운전 모드를 비교하여 최종 차량 명령을 선택",
        "src/universe/autoware.universe/launch/tier4_control_launch/launch/control.launch.xml",
    ),
    (
        "C02", "주 경로",
        "Control", "Control",
        "autoware_vehicle_cmd_gate",
        "/control/vehicle_cmd_gate",
        "Publisher",
        "/control/command/control_cmd",
        "autoware_control_msgs/msg/Control",
        "Control", "Simulator",
        "autoware_simple_planning_simulator",
        "/simulation/simple_planning_simulator",
        "Subscription",
        "/control/command/control_cmd",
        "최종 제어 명령을 차량 운동 모델에 적용",
        "src/universe/autoware.universe/simulator/autoware_simple_planning_simulator/launch/simple_planning_simulator.launch.py",
    ),
    (
        "F01", "차량 상태 피드백",
        "Control", "Simulator",
        "autoware_simple_planning_simulator",
        "/simulation/simple_planning_simulator",
        "Publisher",
        "/localization/kinematic_state",
        "nav_msgs/msg/Odometry",
        "Decision", "Planning",
        "autoware_behavior_path_planner",
        "/planning/scenario_planning/lane_driving/behavior_planning/behavior_path_planner",
        "Subscription",
        "/localization/kinematic_state",
        "갱신된 차량 위치와 속도를 다음 경로 계획 주기에 사용",
        "src/universe/autoware.universe/launch/tier4_planning_launch/launch/scenario_planning/lane_driving/behavior_planning/behavior_planning.launch.xml",
    ),
    (
        "F02", "차량 상태 피드백",
        "Control", "Simulator",
        "autoware_simple_planning_simulator",
        "/simulation/simple_planning_simulator",
        "Publisher",
        "/localization/kinematic_state",
        "nav_msgs/msg/Odometry",
        "Control", "Control",
        "autoware_trajectory_follower_node",
        "/control/trajectory_follower/controller_node_exe",
        "Subscription",
        "/localization/kinematic_state",
        "현재 차량 상태와 기준 궤적의 오차를 다음 제어 주기에 사용",
        "src/universe/autoware.universe/launch/tier4_control_launch/launch/control.launch.xml",
    ),
    (
        "S01", "병렬 안전",
        "Perception", "Perception",
        "autoware_dummy_perception_publisher",
        "/simulation/dummy_perception_publisher",
        "Publisher",
        "/perception/obstacle_segmentation/pointcloud",
        "sensor_msgs/msg/PointCloud2",
        "Control", "Control",
        "autoware_autonomous_emergency_braking",
        "/control/autonomous_emergency_braking",
        "Subscription",
        "/perception/obstacle_segmentation/pointcloud",
        "주 경로와 별도로 장애물 점군을 이용하여 긴급 제동을 감시",
        "src/universe/autoware.universe/launch/tier4_control_launch/launch/control.launch.xml",
    ),
    (
        "S02", "병렬 안전",
        "Perception", "Perception",
        "autoware_map_based_prediction",
        "/perception/object_recognition/map_based_prediction",
        "Publisher",
        "/perception/object_recognition/objects",
        "autoware_perception_msgs/msg/PredictedObjects",
        "Control", "Control",
        "autoware_autonomous_emergency_braking",
        "/control/autonomous_emergency_braking",
        "Subscription",
        "/perception/object_recognition/objects",
        "예측 객체를 사용하여 긴급 제동 조건을 보조 판단",
        "src/universe/autoware.universe/launch/tier4_control_launch/launch/control.launch.xml",
    ),
    (
        "S03", "병렬 안전",
        "Perception", "Perception",
        "autoware_dummy_perception_publisher",
        "/simulation/dummy_perception_publisher",
        "Publisher",
        "/perception/obstacle_segmentation/pointcloud",
        "sensor_msgs/msg/PointCloud2",
        "Control", "Control",
        "autoware_collision_detector",
        "/control/collision_detector",
        "Subscription",
        "/perception/obstacle_segmentation/pointcloud",
        "현재 차량 주변의 충돌 위험을 독립적으로 감시",
        "src/universe/autoware.universe/launch/tier4_control_launch/launch/control.launch.xml",
    ),
    (
        "S04", "병렬 안전",
        "Perception", "Perception",
        "autoware_map_based_prediction",
        "/perception/object_recognition/map_based_prediction",
        "Publisher",
        "/perception/object_recognition/objects",
        "autoware_perception_msgs/msg/PredictedObjects",
        "Control", "Control",
        "autoware_collision_detector",
        "/control/collision_detector",
        "Subscription",
        "/perception/object_recognition/objects",
        "예측 객체와 차량 상태를 사용하여 충돌 위험을 독립적으로 감시",
        "src/universe/autoware.universe/launch/tier4_control_launch/launch/control.launch.xml",
    ),
]


VEHICLE_AUXILIARY_ROWS = [
    (
        "Perception",
        "Decision",
        "Map",
        "Planning",
        "autoware_map_loader",
        "autoware_mission_planner_universe",
        "/map/lanelet2_map_loader",
        "/planning/mission_planning/mission_planner",
        "/map/vector_map",
    ),
    (
        "Perception",
        "Decision",
        "Map",
        "Planning",
        "autoware_map_loader",
        "autoware_behavior_path_planner",
        "/map/lanelet2_map_loader",
        "/planning/scenario_planning/lane_driving/behavior_planning/behavior_path_planner",
        "/map/vector_map",
    ),
    (
        "Perception",
        "Perception",
        "Map",
        "Perception",
        "autoware_map_loader",
        "autoware_map_based_prediction",
        "/map/lanelet2_map_loader",
        "/perception/object_recognition/map_based_prediction",
        "/map/vector_map",
    ),
    (
        "외부 PC RViz",
        "Control",
        "Visualization / RViz",
        "Simulator",
        "rviz2",
        "autoware_simple_planning_simulator",
        "/rviz2",
        "/simulation/simple_planning_simulator",
        "/initialpose3d",
    ),
    (
        "외부 PC RViz",
        "Control",
        "Visualization / RViz",
        "AD API",
        "rviz2",
        "autoware_adapi_adaptors",
        "/rviz2",
        "/default_adapi/helpers/routing_adaptor",
        "/planning/mission_planning/goal",
    ),
    (
        "Decision",
        "Decision",
        "Planning",
        "Planning",
        "autoware_mission_planner_universe",
        "autoware_behavior_path_planner",
        "/planning/mission_planning/mission_planner",
        "/planning/scenario_planning/lane_driving/behavior_planning/behavior_path_planner",
        "/planning/mission_planning/route",
    ),
    (
        "Control",
        "Decision",
        "Simulator",
        "Planning",
        "autoware_simple_planning_simulator",
        "autoware_velocity_smoother",
        "/simulation/simple_planning_simulator",
        "/planning/scenario_planning/velocity_smoother",
        "/localization/acceleration",
    ),
    (
        "Control",
        "Control",
        "Simulator",
        "Control",
        "autoware_simple_planning_simulator",
        "autoware_trajectory_follower_node",
        "/simulation/simple_planning_simulator",
        "/control/trajectory_follower/controller_node_exe",
        "/vehicle/status/steering_status",
    ),
]


def summarize_connection(row):
    source_partition = row[2]
    target_partition = row[9]
    if "외부 PC RViz" in source_partition:
        source_partition = "외부 PC RViz"
    return (
        source_partition,
        target_partition,
        row[3],
        row[10],
        row[4],
        row[11],
        row[5],
        row[12],
        row[7],
    )


def obstacle_flow_rows():
    return [
        summarize_connection(row)
        for row in CONNECTION_ROWS
        if str(row[0]).startswith(("P", "S"))
    ]


def vehicle_flow_rows():
    main_rows = [
        summarize_connection(row)
        for row in CONNECTION_ROWS
        if str(row[0]).startswith(("D", "C", "F"))
    ]
    return VEHICLE_AUXILIARY_ROWS[:6] + main_rows + VEHICLE_AUXILIARY_ROWS[6:]


def topic_rows():
    rows = []
    seen = set()
    for row in obstacle_flow_rows() + vehicle_flow_rows():
        if row not in seen:
            seen.add(row)
            rows.append(row)
    return rows


INTERFACE_ROWS = [
    ("RViz", "Perception", "/simulation/dummy_perception_publisher/object_info", "DummyObject", "더미 장애물 생성·이동·삭제", "동일 ROS_DOMAIN_ID"),
    ("RViz", "Decision", "/planning/mission_planning/goal", "PoseStamped", "목적지 입력", "Mission Planner가 route 생성"),
    ("Perception", "Decision", "/perception/object_recognition/objects", "PredictedObjects", "추적·예측된 객체", "장애물 처리 핵심 인터페이스"),
    ("Perception", "Decision/Control", "/perception/obstacle_segmentation/pointcloud", "PointCloud2", "모의 장애물 점군", "Planning 및 AEB 병렬 입력"),
    ("Decision", "Control", "/planning/scenario_planning/trajectory", "Trajectory", "위치·자세·속도가 포함된 최종 주행 궤적", "Control의 기준 입력"),
    ("Control", "Vehicle simulator", "/control/command/control_cmd", "Control", "최종 조향·가감속 명령", "현재 구성은 실제 차량 대신 simulator"),
    ("Vehicle simulator", "Decision/Control", "/localization/kinematic_state", "Odometry", "차량 pose와 속도 피드백", "다음 계산 cycle에 사용"),
    ("Vehicle simulator", "Decision/Control", "/localization/acceleration", "AccelWithCovarianceStamped", "차량 가속도 피드백", "속도 계획 및 제어에 사용"),
    ("Vehicle simulator", "Control", "/vehicle/status/steering_status", "SteeringReport", "현재 조향 상태", "trajectory follower 입력"),
]


EVIDENCE_ROWS = [
    ("37.6 s", "RViz Bus ADD", "object_info", "장애물 입력 시작"),
    ("47.5 s", "Auto 전환", "/api/operation_mode/state", "Autonomous mode"),
    ("48.5 s", "주행 명령 시작", "/control/command/control_cmd", "차량 이동 시작"),
    ("61.3 s", "정지 명령", "Planning trajectory + control_cmd", "Planning 정지 trajectory 추종"),
    ("62.6 s", "차량 정지", "/vehicle/status/velocity_status", "속도 0 근처"),
    ("75.8 s", "Bus DELETEALL", "object_info", "장애물 삭제"),
    ("77.0 s", "재출발", "/control/command/control_cmd", "전방 trajectory 재개"),
    ("82.8 s", "두 번째 Bus ADD", "object_info", "두 번째 장애물 입력"),
    ("84.9 s", "두 번째 정지", "Planning trajectory + control_cmd", "재정지"),
    ("89.4 s", "Bus 삭제", "object_info", "두 번째 장애물 삭제"),
    ("90.5 s", "재출발", "/control/command/control_cmd", "주행 재개"),
]


def build_overview(sheet):
    merge_text(sheet, "A1:J2", "Autoware Partition Data Flow", bg=COLORS["navy"], size=20)
    merge_text(
        sheet,
        "A3:J3",
        "현재 katech-partition의 컴포넌트 기반 구성 및 dummy_obstacle_20260722_173416 rosbag 기준",
        bg=COLORS["light"],
        fg=COLORS["dark"],
        size=10,
    )
    merge_text(sheet, "A5:B7", "RViz\n장애물 입력", bg=COLORS["rviz_dark"], size=13)
    merge_text(sheet, "C5:C7", "→", bg=COLORS["white"], fg=COLORS["dark"], size=20)
    merge_text(sheet, "D5:E7", "Perception\n검출·추적·예측", bg=COLORS["perception_dark"], size=13)
    merge_text(sheet, "F5:F7", "→", bg=COLORS["white"], fg=COLORS["dark"], size=20)
    merge_text(sheet, "G5:H7", "Decision\n경로·속도 계획", bg=COLORS["decision_dark"], size=13)
    merge_text(sheet, "I5:I7", "→", bg=COLORS["white"], fg=COLORS["dark"], size=20)
    merge_text(sheet, "J5:J7", "Control\n차량 명령", bg=COLORS["control_dark"], size=12)
    merge_text(sheet, "G9:J10", "차량 시뮬레이터 상태 피드백 → Decision / Control", bg=COLORS["feedback_dark"], size=11)

    merge_text(sheet, "A12:J12", "핵심 파티션 인터페이스", bg=COLORS["dark"], size=12)
    rows = [
        ("구간", "핵심 토픽", "의미"),
        ("RViz → Perception", "/simulation/dummy_perception_publisher/object_info", "더미 장애물 입력"),
        ("Perception → Decision", "/perception/object_recognition/objects", "PredictedObjects"),
        ("Decision → Control", "/planning/scenario_planning/trajectory", "최종 주행 trajectory"),
        ("Control → Simulator", "/control/command/control_cmd", "조향·가감속 명령"),
        ("Simulator → Decision/Control", "/localization/kinematic_state", "차량 pose·속도 피드백"),
    ]
    table = sheet.getCellRangeByPosition(0, 12, 9, 17)
    style_range(table, size=10)
    add_borders(table)
    for excel_row, values in enumerate(rows, start=13):
        sheet.getCellRangeByName(f"A{excel_row}:B{excel_row}").merge(True)
        sheet.getCellRangeByName(f"C{excel_row}:G{excel_row}").merge(True)
        sheet.getCellRangeByName(f"H{excel_row}:J{excel_row}").merge(True)
        set_text(sheet.getCellRangeByName(f"A{excel_row}:B{excel_row}").getCellByPosition(0, 0), values[0])
        set_text(sheet.getCellRangeByName(f"C{excel_row}:G{excel_row}").getCellByPosition(0, 0), values[1])
        set_text(sheet.getCellRangeByName(f"H{excel_row}:J{excel_row}").getCellByPosition(0, 0), values[2])
    style_range(sheet.getCellRangeByName("A13:J13"), bg=COLORS["navy"], fg=COLORS["white"], bold=True, center=True)

    merge_text(sheet, "A20:J20", "읽는 방법", bg=COLORS["dark"], size=12)
    notes = [
        "1. 현재 구조는 기능 영역을 세 이미지로 묶는 컴포넌트 기반 파티셔닝입니다.",
        "2. '컴포넌트_구성'은 기능 경계, '소스_범위'는 JSON folders, '패키지_목록'은 실제 포함 결과입니다.",
        "3. '주요_노드'와 '토픽_목록'은 패키지, 런타임 노드, Publisher/Subscriber를 서로 분리합니다.",
        "4. '장애물_통신_연결'은 한 행을 Publisher → 토픽 → Subscription 연결 하나로 읽습니다.",
        "5. 현재 시험에서 확인된 결과는 자동 우회가 아니라 Planning 정지 trajectory에 따른 감속·정지입니다.",
    ]
    for idx, note in enumerate(notes, start=21):
        merge_text(sheet, f"A{idx}:J{idx}", note, bg=COLORS["light"], fg=COLORS["dark"], size=10, bold=False)
    for idx, width in enumerate([2800, 2800, 1500, 3000, 3000, 1500, 3200, 3200, 1500, 3200]):
        sheet.getColumns().getByIndex(idx).Width = width
    sheet.getRows().getByIndex(0).Height = 850
    sheet.getRows().getByIndex(1).Height = 850
    sheet.TabColor = COLORS["navy"]


def build_components(doc, sheet):
    merge_text(sheet, "A1:D2", "파티션별 컴포넌트 구성", bg=COLORS["navy"], size=17)
    headers = ("파티션", "컴포넌트", "현재 Planning Simulation 상태", "역할")
    rows = [headers] + COMPONENT_SUMMARY_ROWS
    set_rows(sheet, 3, rows)
    setup_table(
        doc,
        sheet,
        3,
        rows,
        [2800, 5200, 6200, 11500],
        "component_table",
    )
    color_partition_rows(sheet, 4, COMPONENT_SUMMARY_ROWS)
    for r in range(4, 4 + len(COMPONENT_SUMMARY_ROWS)):
        sheet.getRows().getByIndex(r).OptimalHeight = True
    sheet.TabColor = COLORS["perception_dark"]


def build_sources(doc, sheet, source_rows):
    merge_text(sheet, "A1:F2", "partition_config JSON 소스 포함 범위", bg=COLORS["navy"], size=17)
    headers = ("파티션", "소스 영역", "JSON folders 경로", "패키지 수", "포함 목적", "설정 파일")
    rows = [headers] + source_rows
    set_rows(sheet, 3, rows)
    setup_table(doc, sheet, 3, rows, [2400, 3600, 10500, 2200, 7200, 6200], "source_table")
    color_partition_rows(sheet, 4, source_rows)
    for r in range(4, 4 + len(source_rows)):
        sheet.getRows().getByIndex(r).OptimalHeight = True
    sheet.TabColor = COLORS["feedback_dark"]


def build_packages(doc, sheet, package_rows):
    merge_text(sheet, "A1:F2", "파티션별 실제 포함 ROS 2 패키지", bg=COLORS["navy"], size=17)
    headers = ("파티션", "컴포넌트", "ROS 2 패키지", "소스 경로", "포함 근거", "설정 파일")
    rows = [headers] + package_rows
    set_rows(sheet, 3, rows)
    setup_table(doc, sheet, 3, rows, [2400, 3600, 6500, 12500, 4200, 6200], "package_table")
    color_partition_rows(sheet, 4, package_rows)
    sheet.TabColor = COLORS["perception_dark"]


def build_nodes(doc, sheet):
    runtime_rows = node_rows()
    merge_text(sheet, "A1:J2", "파티션별 주요 런타임 노드", bg=COLORS["navy"], size=17)
    headers = (
        "파티션",
        "컴포넌트",
        "기능 그룹",
        "ROS 2 패키지",
        "노드 / 런타임 구성",
        "상태",
        "주요 입력",
        "주요 출력",
        "역할",
        "근거 파일",
    )
    rows = [headers] + runtime_rows
    set_rows(sheet, 3, rows)
    setup_table(
        doc,
        sheet,
        3,
        rows,
        [2400, 3500, 3200, 6500, 6200, 1800, 6500, 7000, 7500, 5800],
        "node_table",
    )
    color_partition_rows(sheet, 4, runtime_rows)
    for r in range(4, 4 + len(runtime_rows)):
        sheet.getRows().getByIndex(r).OptimalHeight = True
    sheet.TabColor = COLORS["perception_dark"]


def build_topics(doc, sheet):
    runtime_rows = topic_rows()
    merge_text(sheet, "A1:I2", "주요 토픽 목록", bg=COLORS["navy"], size=17)
    rows = [COMMUNICATION_HEADERS] + runtime_rows
    set_rows(sheet, 3, rows)
    setup_table(
        doc,
        sheet,
        3,
        rows,
        [2700, 2700, 3800, 3800, 6500, 6500, 9000, 9000, 11000],
        "topic_table",
    )
    color_partition_rows(sheet, 4, runtime_rows)
    color_partition_rows(sheet, 4, runtime_rows, 1)
    sheet.TabColor = COLORS["decision_dark"]


def build_flow(doc, sheet):
    runtime_rows = obstacle_flow_rows()
    merge_text(sheet, "A1:I2", "장애물 통신 흐름", bg=COLORS["navy"], size=17)
    rows = [COMMUNICATION_HEADERS] + runtime_rows
    set_rows(sheet, 3, rows)
    setup_table(
        doc,
        sheet,
        3,
        rows,
        [2700, 2700, 3800, 3800, 6500, 6500, 9000, 9000, 11000],
        "flow_table",
    )
    color_partition_rows(sheet, 4, runtime_rows)
    color_partition_rows(sheet, 4, runtime_rows, 1)
    for r in range(4, 4 + len(runtime_rows)):
        sheet.getRows().getByIndex(r).OptimalHeight = True
    sheet.TabColor = COLORS["rviz_dark"]


def build_vehicle_flow(doc, sheet):
    runtime_rows = vehicle_flow_rows()
    merge_text(sheet, "A1:I2", "차량 운행 흐름", bg=COLORS["navy"], size=17)
    rows = [COMMUNICATION_HEADERS] + runtime_rows
    set_rows(sheet, 3, rows)
    setup_table(
        doc,
        sheet,
        3,
        rows,
        [2700, 2700, 3800, 3800, 6500, 6500, 9000, 9000, 11000],
        "vehicle_flow_table",
    )
    color_partition_rows(sheet, 4, runtime_rows)
    color_partition_rows(sheet, 4, runtime_rows, 1)
    for r in range(4, 4 + len(runtime_rows)):
        sheet.getRows().getByIndex(r).OptimalHeight = True
    sheet.TabColor = COLORS["control_dark"]


def build_interfaces(doc, sheet):
    merge_text(sheet, "A1:F2", "파티션 간 인터페이스", bg=COLORS["navy"], size=17)
    headers = ("Source", "Target", "토픽", "메시지", "전달 데이터", "비고")
    rows = [headers] + INTERFACE_ROWS
    set_rows(sheet, 3, rows)
    setup_table(doc, sheet, 3, rows, [3200, 3500, 9500, 6200, 7200, 6500], "interface_table")
    sheet.TabColor = COLORS["control_dark"]


def build_evidence(doc, sheet, counts):
    merge_text(sheet, "A1:D2", "장애물 시험 근거", bg=COLORS["navy"], size=17)
    merge_text(sheet, "A3:D3", "rosbag: dummy_obstacle_20260722_173416", bg=COLORS["light"], fg=COLORS["dark"], size=10)
    headers = ("기록 시각", "이벤트", "확인 토픽", "판단")
    rows = [headers] + EVIDENCE_ROWS
    set_rows(sheet, 4, rows)
    setup_table(doc, sheet, 4, rows, [2600, 5200, 9000, 7500], "evidence_table")
    start = 4 + len(rows) + 2
    merge_text(sheet, f"A{start + 1}:D{start + 1}", "주요 토픽 메시지 수", bg=COLORS["dark"], size=11)
    summary = [
        ("토픽", "메시지 수", "토픽", "메시지 수"),
        ("DummyObject 입력", counts.get("/simulation/dummy_perception_publisher/object_info", ""), "DetectedObjects", counts.get("/perception/object_recognition/detection/objects", "")),
        ("TrackedObjects", counts.get("/perception/object_recognition/tracking/objects", ""), "PredictedObjects", counts.get("/perception/object_recognition/objects", "")),
        ("Final trajectory", counts.get("/planning/scenario_planning/trajectory", ""), "Final control cmd", counts.get("/control/command/control_cmd", "")),
        ("Vehicle odometry", counts.get("/localization/kinematic_state", ""), "Vehicle velocity", counts.get("/vehicle/status/velocity_status", "")),
    ]
    set_rows(sheet, start + 1, summary)
    summary_range = sheet.getCellRangeByPosition(0, start + 1, 3, start + len(summary))
    style_range(summary_range, size=9)
    add_borders(summary_range)
    style_range(sheet.getCellRangeByPosition(0, start + 1, 3, start + 1), bg=COLORS["navy"], fg=COLORS["white"], bold=True, center=True)
    sheet.TabColor = COLORS["feedback_dark"]


def postprocess_xlsx(output: Path):
    """Add Excel-native filters, frozen panes, and fit-to-width print settings."""
    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ET.register_namespace("", main_ns)
    ET.register_namespace(
        "r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    )
    ET.register_namespace(
        "xdr", "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
    )
    ET.register_namespace("x14", "http://schemas.microsoft.com/office/spreadsheetml/2009/9/main")
    ET.register_namespace(
        "mc", "http://schemas.openxmlformats.org/markup-compatibility/2006"
    )
    ns = f"{{{main_ns}}}"
    settings = {
        "xl/worksheets/sheet1.xml": (f"A4:D{4 + len(COMPONENT_SUMMARY_ROWS)}", 4),
        "xl/worksheets/sheet2.xml": (f"A4:I{4 + len(topic_rows())}", 4),
        "xl/worksheets/sheet3.xml": (f"A4:I{4 + len(obstacle_flow_rows())}", 4),
        "xl/worksheets/sheet4.xml": (f"A4:I{4 + len(vehicle_flow_rows())}", 4),
    }
    temp_output = output.with_suffix(".tmp.xlsx")
    with zipfile.ZipFile(output, "r") as source, zipfile.ZipFile(
        temp_output, "w", zipfile.ZIP_DEFLATED
    ) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename.startswith("xl/worksheets/sheet") and item.filename.endswith(".xml"):
                root = ET.fromstring(data)
                sheet_pr = root.find(f"{ns}sheetPr")
                if sheet_pr is not None:
                    setup_pr = sheet_pr.find(f"{ns}pageSetUpPr")
                    if setup_pr is not None:
                        setup_pr.set("fitToPage", "true")
                page_setup = root.find(f"{ns}pageSetup")
                if page_setup is not None:
                    page_setup.set("orientation", "landscape")
                    page_setup.set("fitToWidth", "1")
                    page_setup.set("fitToHeight", "0")

                if item.filename in settings:
                    filter_ref, split_row = settings[item.filename]
                    sheet_view = root.find(f"{ns}sheetViews/{ns}sheetView")
                    if sheet_view is not None:
                        for old in list(sheet_view):
                            if old.tag in (f"{ns}pane", f"{ns}selection"):
                                sheet_view.remove(old)
                        pane = ET.Element(
                            f"{ns}pane",
                            {
                                "ySplit": str(split_row),
                                "topLeftCell": f"A{split_row + 1}",
                                "activePane": "bottomLeft",
                                "state": "frozen",
                            },
                        )
                        selection = ET.Element(
                            f"{ns}selection",
                            {
                                "pane": "bottomLeft",
                                "activeCell": f"A{split_row + 1}",
                                "sqref": f"A{split_row + 1}",
                            },
                        )
                        sheet_view.append(pane)
                        sheet_view.append(selection)
                    old_filter = root.find(f"{ns}autoFilter")
                    if old_filter is not None:
                        root.remove(old_filter)
                    auto_filter = ET.Element(f"{ns}autoFilter", {"ref": filter_ref})
                    sheet_data = root.find(f"{ns}sheetData")
                    root.insert(list(root).index(sheet_data) + 1, auto_filter)
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            target.writestr(item, data)
    os.replace(temp_output, output)


def create_workbook(output: Path):
    desktop, process, profile = connect_office()
    doc = None
    try:
        doc = desktop.loadComponentFromURL("private:factory/scalc", "_blank", 0, (prop("Hidden", True),))
        sheets = doc.getSheets()
        first = sheets.getElementNames()[0]
        sheets.getByName(first).Name = "컴포넌트_구성"
        for index, name in enumerate(
            (
                "토픽_목록",
                "장애물_통신_흐름",
                "차량_운행_흐름",
            ),
            start=1,
        ):
            sheets.insertNewByName(name, index)

        build_components(doc, sheets.getByName("컴포넌트_구성"))
        build_topics(doc, sheets.getByName("토픽_목록"))
        build_flow(doc, sheets.getByName("장애물_통신_흐름"))
        build_vehicle_flow(doc, sheets.getByName("차량_운행_흐름"))

        doc.getCurrentController().setActiveSheet(sheets.getByName("컴포넌트_구성"))
        output.parent.mkdir(parents=True, exist_ok=True)
        doc.storeAsURL(
            uno.systemPathToFileUrl(str(output.resolve())),
            (prop("FilterName", "Calc MS Excel 2007 XML"), prop("Overwrite", True)),
        )
        doc.close(True)
        doc = None
        postprocess_xlsx(output)

        check = desktop.loadComponentFromURL(
            uno.systemPathToFileUrl(str(output.resolve())), "_blank", 0, (prop("Hidden", True),)
        )
        names = tuple(check.getSheets().getElementNames())
        expected = (
            "컴포넌트_구성",
            "토픽_목록",
            "장애물_통신_흐름",
            "차량_운행_흐름",
        )
        if names != expected:
            raise RuntimeError(f"Unexpected sheet names: {names}")
        if (
            check.getSheets()
            .getByName("장애물_통신_흐름")
            .getCellByPosition(4, 4)
            .String
            != "tier4_dummy_object_rviz_plugin"
        ):
            raise RuntimeError("Obstacle flow sheet validation failed")
        check.close(True)
        print(f"Created: {output}")
        print(f"Sheets: {', '.join(names)}")
        print(
            f"Component rows: {len(COMPONENT_SUMMARY_ROWS)}, "
            f"topic rows: {len(topic_rows())}, "
            f"obstacle flow rows: {len(obstacle_flow_rows())}, "
            f"vehicle flow rows: {len(vehicle_flow_rows())}"
        )
    finally:
        if doc is not None:
            try:
                doc.close(True)
            except Exception:
                pass
        try:
            desktop.terminate()
        except Exception:
            pass
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=5)
        shutil.rmtree(profile, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    create_workbook(args.output)


if __name__ == "__main__":
    main()
