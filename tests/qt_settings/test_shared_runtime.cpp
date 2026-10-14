#include "AppPaths.h"
#include "LibraryController.h"
#include "SettingsController.h"

#include <cstdio>
#include <cstdlib>

#include <QtCore/QCoreApplication>
#include <QtCore/QDebug>
#include <QtCore/QDir>
#include <QtCore/QFile>
#include <QtCore/QFileInfo>
#include <QtCore/QSettings>
#include <QtCore/QTemporaryDir>

namespace
{
void require(bool condition, const char *message)
{
    if (!condition)
    {
        std::fprintf(stderr, "Shared runtime test failed: %s\n", message);
        std::exit(EXIT_FAILURE);
    }
}

void write(const QString &path, const QByteArray &contents)
{
    require(QDir().mkpath(QFileInfo(path).absolutePath()), "Cannot create fixture directory");
    QFile file(path);
    require(file.open(QIODevice::WriteOnly), "Cannot open fixture");
    require(file.write(contents) == contents.size(), "Cannot write fixture");
}
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    QTemporaryDir directory;
    require(directory.isValid(), "Cannot isolate shared runtime tests");
    QSettings::setDefaultFormat(QSettings::IniFormat);
    QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, directory.path());
    const QString dataRoot = AppPaths::cleanPath(directory.filePath("data"));
    const QString config = QDir(dataRoot).filePath("config.toml");
    QSettings preferences("Audio2Text", "Audio2TextQt");
    preferences.setValue("dataRoot", dataRoot);
    preferences.sync();
    SettingsController settings;
    // An old local library must not override the configured/default iCloud library.
    write(QDir(dataRoot).filePath("Audio2TextLibrary/episodes/decoy/episode.json"), "{\"title\":\"Decoy\"}");
#ifdef Q_OS_WIN
    require(settings.resolvedLibraryRoot() == AppPaths::normalizeLibraryRoot(dataRoot), "Windows default differs from CLI");
#else
    require(settings.resolvedLibraryRoot() == AppPaths::normalizeLibraryRoot(
        QDir::homePath() + "/Library/Mobile Documents/com~apple~CloudDocs/Audio2Text"), "Default differs from Swift and CLI");
#endif
    write(config, "[library]\nstorage = \"local\"\nlocal_root = \"\"\n");
    require(settings.resolvedLibraryRoot() == AppPaths::normalizeLibraryRoot(dataRoot), "Default local root differs from Swift");
    const QString sharedParent = directory.filePath("Shared # library");
    const QString sharedRoot = AppPaths::normalizeLibraryRoot(sharedParent);
    write(config, "[library]\nstorage = 'icloud' # Shared with Swift\nicloud_root = '"
        + sharedParent.toUtf8() + "' # Literal path\n[local]\nasr_model = \"large-v3-turbo\"\n");
    require(settings.resolvedLibraryRoot() == sharedRoot, "Custom iCloud root was not normalized");
    write(QDir(sharedRoot).filePath("episodes/shared/episode.json"),
          "{\"episode_id\":\"shared\",\"title\":\"Shared episode\",\"app_group\":\"Research\"}");
    write(QDir(sharedRoot).filePath("episodes/shared/documents/transcript.md"), "# Shared transcript\n");
    write(QDir(sharedRoot).filePath("groups/research.json"), "{\"id\":\"research\",\"title\":\"Research\"}");
    write(QDir(sharedRoot).filePath("subscriptions/feed.json"), "{\"id\":\"feed\",\"title\":\"Shared feed\"}");
    LibraryController library(&settings);
    library.refresh();
    require(library.items().size() == 1 && library.groups().size() == 2 && library.subscriptions().size() == 1,
            "Qt did not read the shared episodes, groups and subscriptions");
    library.selectItem("shared");
    require(library.documentForSelectedTab("transcript").contains("Shared transcript"), "Shared transcript not readable");
    library.setSelectedRead(true);
    require(AppPaths::readJsonObject(QDir(sharedRoot).filePath("episodes/shared/episode.json")).value("app_read").toBool(),
            "Read state did not update shared metadata");
    require(settings.processEnvironment().value("ATOT_DATA_ROOT") == dataRoot, "CLI runtime uses a different data root");
    require(settings.detectTools().value("modelRoot").toString() == AppPaths::modelRoot(dataRoot), "Model root differs from Swift");

    const QString localParent = directory.filePath("Other library");
    write(config, "[library]\nstorage = \"local\"\nlocal_root = \"" + localParent.toUtf8()
        + "\"\n[local]\nasr_model = \"large-v3\"\n");
    settings.reloadCloudConfig();
    require(library.libraryRoot() == AppPaths::normalizeLibraryRoot(localParent), "External storage change was not refreshed");
    require(settings.modelAlias() == "large-v3", "External model selection was not refreshed");
    write(config, "[library]\nstorage = \"invalid\"\n");
    library.refresh();
    require(library.items().isEmpty() && library.statusMessage().contains("Invalid library.storage"), "Invalid storage was hidden");

    const QString probeDataRoot = AppPaths::cleanPath(directory.filePath("probe-data"));
    settings.applyRuntimePaths(probeDataRoot, sharedRoot, "probe-atot", "probe-vcpkg");
    settings.setLocalOnly(false); // Saving another preference must not persist runtime paths.
    require(settings.resolvedLibraryRoot() == sharedRoot, "Explicit library override did not win");
    require(settings.processEnvironment().value("ATOT_DATA_ROOT") == probeDataRoot, "Runtime data override ignored");
    SettingsController nextLaunch;
    require(nextLaunch.dataRoot() == dataRoot && nextLaunch.libraryRootOverride().isEmpty()
        && nextLaunch.atotPath().isEmpty() && nextLaunch.vcpkgRoot() != "probe-vcpkg", "Runtime paths polluted saved preferences");

    // A library can have subscriptions/groups before its first episode is imported.
    require(QDir(QDir(sharedRoot).filePath("episodes")).removeRecursively(), "Cannot clear fixture episodes");
    library.refresh();
    require(library.items().isEmpty() && library.groups().size() == 2 && library.subscriptions().size() == 1,
            "Empty episode directory hid subscriptions or groups");
    return 0;
}
