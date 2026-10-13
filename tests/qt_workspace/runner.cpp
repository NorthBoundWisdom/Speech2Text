#include "GeoControlsSetup.h"
#include "JobController.h"
#include "LibraryController.h"
#include "SettingsController.h"

#include <QtCore/QSettings>
#include <QtCore/QTemporaryDir>
#include <QtQml/QQmlContext>
#include <QtQml/QQmlEngine>
#include <QtQuickControls2/QQuickStyle>
#include <QtQuickTest/quicktest.h>

class ControlSetup : public QObject
{
    Q_OBJECT
public slots:
    void applicationAvailable()
    {
        initializeGeoControls();
        QCoreApplication::setOrganizationName("SonaFolioTests");
        QCoreApplication::setOrganizationDomain("sonafolio.test");
        if (!directory.isValid()) qFatal("Cannot isolate Qt control tests.");
        QSettings::setDefaultFormat(QSettings::IniFormat);
        QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, directory.path());
        QSettings preferences("Audio2Text", "Audio2TextQt");
        preferences.setValue("dataRoot", directory.path());
        preferences.sync();
        settings = new SettingsController(this);
        library = new LibraryController(settings, this);
        jobs = new JobController(settings, library, this);
    }
    void qmlEngineAvailable(QQmlEngine *engine)
    {
        configureGeoControlsEngine(engine);
        engine->rootContext()->setContextProperty("settingsController", settings);
        engine->rootContext()->setContextProperty("libraryController", library);
        engine->rootContext()->setContextProperty("jobController", jobs);
        engine->rootContext()->setContextProperty("captureDirectory", qEnvironmentVariable("ATOT_QT_TEST_CAPTURE_DIR"));
    }
private:
    QTemporaryDir directory;
    SettingsController *settings = nullptr;
    LibraryController *library = nullptr;
    JobController *jobs = nullptr;
};

int main(int argc, char **argv)
{
    QCoreApplication::setAttribute(Qt::AA_DontUseNativeMenuBar);
    QQuickStyle::setStyle("Basic");
    ControlSetup setup;
    return quick_test_main_with_setup(argc, argv, "SonaFolioWorkspace", QUICK_TEST_SOURCE_DIR, &setup);
}
#include "runner.moc"
