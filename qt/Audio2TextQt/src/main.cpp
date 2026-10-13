#include "JobController.h"
#include "GeoControlsSetup.h"
#include "LibraryController.h"
#include "SettingsController.h"

#include <QtCore/QCommandLineOption>
#include <QtCore/QCommandLineParser>
#include <QtCore/QCoreApplication>
#include <QtCore/QDebug>
#include <QtCore/QStringList>
#include <QtCore/QTimer>
#include <cstdio>
#include <QtGui/QFontDatabase>
#include <QtGui/QGuiApplication>
#include <QtGui/QIcon>
#include <QtQml/QQmlApplicationEngine>
#include <QtQml/QQmlContext>
#include <QtQuickControls2/QQuickStyle>

namespace
{
void messageHandler(QtMsgType type, const QMessageLogContext &, const QString &message)
{
    const QByteArray bytes = message.toLocal8Bit();
    const char *level = "info";
    switch (type)
    {
    case QtDebugMsg:
        level = "debug";
        break;
    case QtInfoMsg:
        level = "info";
        break;
    case QtWarningMsg:
        level = "warning";
        break;
    case QtCriticalMsg:
        level = "critical";
        break;
    case QtFatalMsg:
        level = "fatal";
        break;
    }
    std::fprintf(stderr, "[%s] %s\n", level, bytes.constData());
    std::fflush(stderr);
}

void applyCommandLine(SettingsController &settings, const QCommandLineParser &parser)
{
    const QString dataRoot = parser.value("data-root");
    if (!dataRoot.isEmpty())
    {
        settings.setDataRoot(dataRoot);
    }
    const QString libraryRoot = parser.value("library-root");
    if (!libraryRoot.isEmpty())
    {
        settings.setLibraryRootOverride(libraryRoot);
    }
    const QString atot = parser.value("atot");
    if (!atot.isEmpty())
    {
        settings.setAtotPath(atot);
    }
    const QString vcpkgRoot = parser.value("vcpkg-root");
    if (!vcpkgRoot.isEmpty())
    {
        settings.setVcpkgRoot(vcpkgRoot);
    }
}

bool hasRawArgument(int argc, char *argv[], const QString &argument)
{
    for (int index = 1; index < argc; ++index)
    {
        if (QString::fromLocal8Bit(argv[index]) == argument)
        {
            return true;
        }
    }
    return false;
}

QString rawOptionValue(int argc, char *argv[], const QString &argument)
{
    const QString prefix = argument + "=";
    for (int index = 1; index < argc; ++index)
    {
        const QString current = QString::fromLocal8Bit(argv[index]);
        if (current.startsWith(prefix))
        {
            return current.mid(prefix.size());
        }
        if (current == argument && index + 1 < argc)
        {
            return QString::fromLocal8Bit(argv[index + 1]);
        }
    }
    return {};
}

QFont applicationFont()
{
    QFont font = QFontDatabase::systemFont(QFontDatabase::GeneralFont);
#ifdef Q_OS_MACOS
    const QStringList families = QFontDatabase::families();
    if (families.contains("PingFang SC"))
    {
        font.setFamily("PingFang SC");
    }
    else if (families.contains(".AppleSystemUIFont"))
    {
        font.setFamily(".AppleSystemUIFont");
    }
#endif
    return font;
}
}

int main(int argc, char *argv[])
{
    const bool rawSmokeQuit = hasRawArgument(argc, argv, "--smoke-quit") || hasRawArgument(argc, argv, "-s");
    const bool rawLibraryProbe = hasRawArgument(argc, argv, "--library-probe");
    const QString rawDataRoot = rawOptionValue(argc, argv, "--data-root");
    const QString rawLibraryRoot = rawOptionValue(argc, argv, "--library-root");
    const QString rawAtot = rawOptionValue(argc, argv, "--atot");
    const QString rawVcpkgRoot = rawOptionValue(argc, argv, "--vcpkg-root");

    qInstallMessageHandler(messageHandler);
    QCoreApplication::setAttribute(Qt::AA_DontUseNativeMenuBar);
    QQuickStyle::setStyle("Basic");
    QGuiApplication app(argc, argv);
    initializeGeoControls();
    QCoreApplication::setOrganizationName("Audio2Text");
    QCoreApplication::setOrganizationDomain("audio2text.local");
    QCoreApplication::setApplicationName("SonaFolio");
    QCoreApplication::setApplicationVersion(AUDIO2TEXTQT_VERSION);
    QGuiApplication::setFont(applicationFont());
    QGuiApplication::setWindowIcon(QIcon(":/Audio2TextQt/resources/app-icon.png"));

    QCommandLineParser parser;
    parser.setApplicationDescription("SonaFolio Qt/QML client");
    parser.addHelpOption();
    parser.addVersionOption();
    parser.addOption({{"s", "smoke-quit"}, "Load QML, refresh once, and quit."});
    parser.addOption({"library-probe", "Scan the configured library once, print a summary, and quit."});
    parser.addOption({"data-root", "Override the SonaFolio data root for this run.", "path"});
    parser.addOption({"library-root", "Override the Audio2TextLibrary root for this run.", "path"});
    parser.addOption({"atot", "Path to atot, atot.exe, or Audio2TextCli.", "path"});
    parser.addOption({"vcpkg-root", "Path to a local vcpkg root for ffmpeg discovery.", "path"});
    parser.process(app);

    SettingsController settings;
    applyCommandLine(settings, parser);
    if (!rawDataRoot.isEmpty())
    {
        settings.setDataRoot(rawDataRoot);
    }
    if (!rawLibraryRoot.isEmpty())
    {
        settings.setLibraryRootOverride(rawLibraryRoot);
    }
    if (!rawAtot.isEmpty())
    {
        settings.setAtotPath(rawAtot);
    }
    if (!rawVcpkgRoot.isEmpty())
    {
        settings.setVcpkgRoot(rawVcpkgRoot);
    }
    LibraryController library(&settings);
    JobController jobs(&settings, &library);
    const bool smokeQuit = rawSmokeQuit || parser.isSet("smoke-quit");
    const bool libraryProbe = rawLibraryProbe || parser.isSet("library-probe");

    if (libraryProbe)
    {
        library.refresh();
        std::fprintf(
            stderr,
            "SonaFolio Qt library probe: %d episodes, %d groups, %d subscriptions, root=%s\n",
            static_cast<int>(library.items().size()),
            static_cast<int>(library.groups().size()),
            static_cast<int>(library.subscriptions().size()),
            library.libraryRoot().toLocal8Bit().constData());
        std::fflush(stderr);
        return library.items().isEmpty() ? 1 : 0;
    }

    QQmlApplicationEngine engine;
    configureGeoControlsEngine(&engine);
    QObject::connect(&engine, &QQmlApplicationEngine::warnings, &engine, [](const QList<QQmlError> &warnings) {
        for (const QQmlError &warning : warnings)
        {
            qWarning().noquote() << warning.toString();
        }
    });
    engine.addImportPath("qrc:/Audio2TextQt");
    engine.rootContext()->setContextProperty("settingsController", &settings);
    engine.rootContext()->setContextProperty("libraryController", &library);
    engine.rootContext()->setContextProperty("jobController", &jobs);
    engine.load(QUrl("qrc:/Audio2TextQt/qml/Main.qml"));

    if (engine.rootObjects().isEmpty())
    {
        std::fprintf(stderr, "SonaFolio Qt: failed to load qrc:/Audio2TextQt/qml/Main.qml\n");
        std::fflush(stderr);
        return 1;
    }

    if (!smokeQuit)
    {
        QTimer::singleShot(0, &library, &LibraryController::refresh);
    }
    if (smokeQuit)
    {
        std::fprintf(stderr, "SonaFolio Qt: QML smoke loaded.\n");
        std::fflush(stderr);
        QTimer::singleShot(700, &app, &QCoreApplication::quit);
    }

    return app.exec();
}
