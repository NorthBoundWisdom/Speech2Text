import QtQuick
import QtTest
import "../../qt/Audio2TextQt/qml" as App

Item {
    width: 180
    height: 640
    App.ApplicationStatusPanel {
        id: panel
        width: 160
        running: true
        stage: "Refreshing subscriptions and library"
        errorText: "The model endpoint could not complete the request. Check its configured access and retry."
        queuedCount: 3
        libraryMessage: "Library changes are available and the selected documents can be read."
    }
    SignalSpy { id: logs; target: panel; signalName: "logsRequested" }
    TestCase {
        name: "ApplicationStatusPanel"
        when: windowShown
        function init() {
            panel.running = true
            panel.stage = "Refreshing subscriptions and library"
            panel.errorText = "The model endpoint could not complete the request. Check its configured access and retry."
        }
        function test_narrow_titles_and_errors_wrap_without_elision() {
            wait(100)
            let title = findChild(panel, "activityStatusTitle")
            let error = findChild(panel, "taskErrorStatus")
            let library = findChild(panel, "libraryStatusDetail")
            verify(title.height > 20)
            compare(title.elide, Text.ElideNone)
            compare(error.elide, Text.ElideNone)
            verify(error.height > 30)
            verify(library.height > 20)
            verify(panel.implicitHeight > 160)
        }
        function test_idle_and_error_states_are_independent_from_library() {
            panel.running = false
            panel.errorText = ""
            panel.stage = "Idle"
            wait(50)
            compare(findChild(panel, "activityStatusTitle").text, "Idle")
            verify(findChild(panel, "libraryStatusDetail").visible)
            panel.errorText = "Library task failed"
            wait(50)
            compare(findChild(panel, "activityStatusTitle").text, "Task failed")
        }
    }
}
