import QtQuick
import QtTest
import QtQuick.Controls as QQC
import GeoControls 1.0
import "../../qt/Audio2TextQt/qml" as App

Item {
    id: fixture
    width: 1160
    height: 900
    property string boundText: "Initial"
    CustomTextField {
        id: boundField
        visible: false
        width: 300
        text: fixture.boundText
        onTextEdited: fixture.boundText = text
    }

    App.ImportDialog {
        id: importer
        parent: fixture
        x: 20
        y: 20
    }
    App.SettingsDialog {
        id: settings
        parent: fixture
    }
    Component {
        id: shellComponent
        App.Main {
            visible: false
        }
    }

    TestCase {
        name: "GeoControlsIntegration"
        when: windowShown

        function initTestCase() {
            failOnWarning(/.*/);
        }
        function init() {
            importer.close();
            settings.close();
            settingsController.transcriptionLanguages = [];
            settingsController.summaryLanguage = "zh";
            settingsController.cloudChunkMinutes = 10;
            settingsController.localOnly = true;
            settingsController.appearanceMode = "system";
        }
        function cleanup() {
            importer.close();
            settings.close();
            boundField.visible = false;
            settingsController.appearanceMode = "system";
        }
        function capture(item, name) {
            if (captureDirectory.length === 0)
                return;
            let saved = false;
            verify(item.grabToImage(function (result) {
                saved = result.saveToFile(captureDirectory + "/" + name + ".png");
            }));
            tryVerify(function () {
                return saved;
            });
        }

        function test_workspace_shell_loads_without_native_controls() {
            let shell = createTemporaryObject(shellComponent, null);
            verify(shell);
            shell.visible = true;
            verify(waitForRendering(shell.contentItem));
            compare(shell.palette.window, Theme.windowColor);
            capture(findChild(shell, "workspaceBody"), "workspace");
            shell.close();
        }

        function test_toolbar_icons_toggle_columns_and_open_status() {
            let shell = createTemporaryObject(shellComponent, null);
            verify(shell);
            shell.visible = true;
            verify(waitForRendering(shell.contentItem));
            let workspace = findChild(shell, "desktopWorkspace");
            let sources = findChild(shell, "toggleSourcesButton");
            let episodes = findChild(shell, "toggleEpisodeListButton");
            let status = findChild(shell, "applicationStatusButton");
            let popup = findChild(shell, "applicationStatusPopup");
            verify(workspace && sources && episodes && status && popup);
            if (workspace.sourceCollapsed) workspace.toggleSources();
            if (workspace.listCollapsed) workspace.toggleList();
            compare(sources.display, QQC.AbstractButton.IconOnly);
            compare(episodes.display, QQC.AbstractButton.IconOnly);
            verify(sources.icon.source.toString().length > 0);
            verify(episodes.icon.source.toString().length > 0);
            verify(status.icon.source.toString().length > 0);
            mouseClick(sources);
            tryCompare(workspace, "sourceActualWidth", 0);
            compare(sources.Accessible.name, "Show Sources");
            sources.forceActiveFocus();
            keyClick(Qt.Key_Space);
            tryCompare(workspace, "sourceCollapsed", false);
            verify(sources.checked);
            workspace.toggleSources();
            compare(sources.checked, false);
            workspace.toggleSources();
            mouseClick(episodes);
            tryCompare(workspace, "listActualWidth", 0);
            compare(episodes.Accessible.name, "Show Episode List");
            mouseClick(episodes);
            tryCompare(workspace, "listCollapsed", false);
            mouseClick(status);
            tryCompare(popup, "opened", true);
            keyClick(Qt.Key_Escape);
            tryCompare(popup, "opened", false);
            capture(findChild(shell, "libraryToolBar"), "toolbar");
            shell.close();
        }

        function test_import_tabs_and_subscription_limit() {
            importer.open();
            tryCompare(importer, "opened", true);
            mouseClick(findChild(importer, "localImportTab"));
            compare(importer.selectedMode, "local");
            mouseClick(findChild(importer, "subscriptionImportTab"));
            compare(importer.selectedMode, "subscription");
            let limit = findChild(importer, "importSubscriptionLimit");
            compare(limit.value, 20);
            limit.forceActiveFocus();
            keyClick(Qt.Key_Up);
            compare(limit.value, 21);
            compare(limit.realValue, 21);
            capture(findChild(importer, "importDialogBody"), "import");
        }

        function test_languages_and_workflow_commit_to_settings() {
            settings.selectedPage = 1;
            settings.open();
            tryCompare(settings, "opened", true);
            let chinese = findChild(settings.contentItem, "transcriptionLanguage_zh");
            let english = findChild(settings.contentItem, "transcriptionLanguage_en");
            verify(chinese && english);
            mouseClick(chinese);
            mouseClick(english);
            compare(settingsController.transcriptionLanguages.join(","), "zh,en");
            mouseClick(chinese);
            compare(settingsController.transcriptionLanguages.join(","), "en");

            let output = findChild(settings.contentItem, "summaryOutputLanguage");
            output.currentIndex = 1;
            output.activated(1);
            compare(settingsController.summaryLanguage, "en");

            let workflow = findChild(settings.contentItem, "processingWorkflow");
            mouseClick(workflow, workflow.width * 0.75, workflow.height / 2);
            compare(settingsController.localOnly, false);

            let chunk = findChild(settings.contentItem, "cloudChunkMinutes");
            chunk.forceActiveFocus();
            keyClick(Qt.Key_Up);
            compare(settingsController.cloudChunkMinutes, 11);
            capture(findChild(settings, "settingsDialogBody"), "languages");
        }

        function test_all_settings_pages_load() {
            settings.open();
            tryCompare(settings, "opened", true);
            for (let index = 0; index < 5; index++) {
                settings.selectedPage = index;
                verify(waitForRendering(fixture));
            }
        }
        function test_appearance_setting_applies_immediately() {
            settings.selectedPage = 0;
            settings.open();
            tryCompare(settings, "opened", true);
            let appearance = findChild(settings.contentItem, "appearanceMode");
            compare(appearance.currentIndex, 0);
            appearance.currentIndex = 2;
            appearance.activated(2);
            compare(settingsController.appearanceMode, "dark");
            compare(Theme.appearance, 1);
            verify(waitForRendering(fixture));
            capture(findChild(settings, "settingsDialogBody"), "settings-dark");
            settings.close();
            settings.open();
            tryCompare(settings, "opened", true);
            compare(appearance.currentIndex, 2);
            settingsController.appearanceMode = "light";
            compare(appearance.currentIndex, 1);
            compare(Theme.appearance, 0);
            settingsController.appearanceMode = "system";
            compare(appearance.currentIndex, 0);
        }
        function test_external_settings_refresh_after_control_edits() {
            settings.selectedPage = 1;
            settings.open();
            tryCompare(settings, "opened", true);
            let output = findChild(settings.contentItem, "summaryOutputLanguage");
            output.currentIndex = 1;
            output.activated(1);
            let workflow = findChild(settings.contentItem, "processingWorkflow");
            mouseClick(workflow, workflow.width * 0.75, workflow.height / 2);
            let chunk = findChild(settings.contentItem, "cloudChunkMinutes");
            chunk.forceActiveFocus();
            keyClick(Qt.Key_Up);
            settingsController.summaryLanguage = "zh";
            settingsController.localOnly = true;
            settingsController.cloudChunkMinutes = 22;
            compare(output.currentIndex, 0);
            compare(workflow.currentIndex, 0);
            compare(chunk.realValue, 22);
        }
        function test_text_field_retains_external_binding_after_typing() {
            fixture.boundText = "Initial";
            boundField.visible = true;
            boundField.forceActiveFocus();
            boundField.selectAll();
            keyClick(Qt.Key_A);
            compare(fixture.boundText, "a");
            fixture.boundText = "Reloaded";
            compare(boundField.text, "Reloaded");
        }
    }
}
