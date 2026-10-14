#include "SettingsController.h"
#include <QtCore/QCoreApplication>
#include <QtCore/QDebug>
#include <QtCore/QDir>
#include <QtCore/QFile>
#include <QtCore/QSettings>
#include <QtCore/QTemporaryDir>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    QTemporaryDir directory;
    if (!directory.isValid()) return 1;
    QSettings::setDefaultFormat(QSettings::IniFormat);
    QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, directory.path());
    QSettings preferences("Audio2Text", "Audio2TextQt");
    preferences.setValue("dataRoot", directory.path());
    preferences.sync();
    auto require = [](bool condition, const char *message) {
        if (!condition) qCritical() << message;
        return condition;
    };
    SettingsController defaults;
    if (!require(defaults.appearanceMode() == "system", "Appearance must follow the system by default")) return 1;
    if (!require(defaults.transcriptionLanguages().isEmpty() && defaults.summaryLanguage() == "zh", "Invalid defaults")) return 1;
    QFile file(QDir(directory.path()).filePath("config.toml"));
    if (!file.open(QIODevice::WriteOnly)) return 1;
    file.write("[local]\nlanguage = \"jp\"\nbackend = \"recording\"\n[profiles.custom]\nchunk_length = 42\n");
    file.close();
    defaults.reloadCloudConfig();
    if (!require(defaults.transcriptionLanguages() == QStringList{"ja"}, "Legacy language not migrated")) return 1;
    defaults.setTranscriptionLanguages({"zh", "en", "zh"});
    defaults.setSummaryLanguage("en");
    defaults.setSummaryPrompt("Custom structure.");
    SettingsController reloaded;
    if (!require(reloaded.transcriptionLanguages() == QStringList{"zh", "en"} && reloaded.summaryLanguage() == "en", "Languages did not round trip")) return 1;
    if (!require(reloaded.summaryPrompt() == "Custom structure.", "Custom prompt changed")) return 1;
    if (!file.open(QIODevice::ReadOnly)) return 1;
    const auto text = file.readAll();
    file.close();
    if (!require(text.contains("backend = \"recording\"") && text.contains("[profiles.custom]") && !text.contains("language = \"jp\""), "Unrelated config lost or legacy key retained")) return 1;
    reloaded.setTranscriptionLanguages({});
    reloaded.reloadCloudConfig();
    if (!require(reloaded.transcriptionLanguages().isEmpty(), "Empty array did not mean auto")) return 1;
    if (!require(reloaded.languageOptions().size() == 16, "Language catalog incomplete")) return 1;
    defaults.setAppearanceMode("dark");
    SettingsController darkLaunch;
    if (!require(darkLaunch.appearanceMode() == "dark", "Dark appearance was not saved")) return 1;
    darkLaunch.setAppearanceMode("light");
    SettingsController lightLaunch;
    if (!require(lightLaunch.appearanceMode() == "light", "Light appearance was not saved")) return 1;
    lightLaunch.setAppearanceMode("invalid");
    if (!require(lightLaunch.appearanceMode() == "light", "Unsupported appearance was accepted")) return 1;
    lightLaunch.setAppearanceMode("system");
    SettingsController systemLaunch;
    if (!require(systemLaunch.appearanceMode() == "system", "System appearance was not restored")) return 1;
    return 0;
}
