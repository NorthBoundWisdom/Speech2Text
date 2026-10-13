#include "GeoControlsSetup.h"

#include <Controls/ThemeHelper.h>
#include <QtCore/QResource>
#include <QtGui/QFontDatabase>
#include <QtGui/QGuiApplication>
#include <QtQml/QQmlEngine>

void qml_register_types_GeoControls();
void qml_register_types_GeoControls_AppShell();

void initializeGeoControls()
{
    // NO_PLUGIN modules keep their resources and registrations in static libraries.
    Q_INIT_RESOURCE(icons);
    Q_INIT_RESOURCE(qmake_GeoControls);
    Q_INIT_RESOURCE(GeoControlsControls_raw_qml_0);
    Q_INIT_RESOURCE(qmake_GeoControls_AppShell);
    Q_INIT_RESOURCE(GeoControlsAppShell_raw_qml_0);
    qml_register_types_GeoControls();
    qml_register_types_GeoControls_AppShell();
}

void configureGeoControlsEngine(QQmlEngine *engine)
{
    engine->addImportPath(QStringLiteral("qrc:/"));
    auto *theme = engine->singletonInstance<QObject *>("GeoControls", "Theme");
    auto *helper = new geocontrols::ThemeHelper(engine);
    QFont font = QGuiApplication::font();
    QFont mono = QFontDatabase::systemFont(QFontDatabase::FixedFont);
#ifdef Q_OS_MACOS
    const QStringList families = QFontDatabase::families();
    if (font.family() == QStringLiteral("Sans Serif") && families.contains("PingFang SC"))
        font.setFamily(QStringLiteral("PingFang SC"));
    if (families.contains("Menlo"))
        mono.setFamily(QStringLiteral("Menlo"));
#endif
    if (!theme || !theme->setProperty("helper", QVariant::fromValue(helper))
        || !theme->setProperty("appFont", font) || !theme->setProperty("monoFont", mono))
    {
        qFatal("SonaFolio Qt: GeoControls theme could not be initialized.");
    }
}
