import os
from pathlib import Path


def test_gate2_qml_is_present_and_mock_only():
    root = Path(__file__).resolve().parents[1]
    qml = (root / "qml" / "Main.qml").read_text(encoding="utf-8")
    assert "VISUAL CONCEPT / MOCK STATE" in qml
    assert "WAITING FOR APPROVAL" in qml
    assert "EventBus" not in qml
    assert "AuthorizationManager" not in qml
    assert "id: motion" in qml
    assert "MOTION PROTOTYPE / DEVELOPMENT ONLY" in qml
    assert "scenario === \"SEQUENTIAL\"" in qml
    assert "scenario === \"PARALLEL\"" in qml
    assert "reducedMotion" in qml
    assert "transferActive" in qml


def test_gate3_controller_remains_qml_only():
    root = Path(__file__).resolve().parents[1]
    qml = (root / "qml" / "Main.qml").read_text(encoding="utf-8")
    prohibited = ("EventBus", "AuthorizationManager", "AuthManager", "subprocess", "writeFile")
    assert not any(token in qml for token in prohibited)


def test_gate2_imports_qt_runtime():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtQml, QtQuick, QtQuick3D
    assert QtQml.QQmlApplicationEngine and QtQuick.QQuickWindow and QtQuick3D.QQuick3D


def test_gate2_qml_loads(qapp):
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlApplicationEngine
    qml = Path(__file__).resolve().parents[1] / "qml" / "Main.qml"
    engine = QQmlApplicationEngine()
    engine.load(QUrl.fromLocalFile(str(qml)))
    assert engine.rootObjects()


def test_gate3_mock_controller_changes_visual_state_only(qapp):
    from PySide6.QtCore import QMetaObject, QObject, QUrl
    from PySide6.QtQml import QQmlApplicationEngine

    qml = Path(__file__).resolve().parents[1] / "qml" / "Main.qml"
    engine = QQmlApplicationEngine()
    engine.load(QUrl.fromLocalFile(str(qml)))
    window = engine.rootObjects()[0]
    controller = window.findChild(QObject, "motionPrototypeController")
    assert controller is not None
    assert QMetaObject.invokeMethod(controller, "demoThinking")
    assert controller.property("coreState") == "THINKING"
    assert controller.property("missionStage") == 2
