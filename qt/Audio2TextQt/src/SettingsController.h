#pragma once

#include <QtCore/QObject>
#include <QtCore/QProcessEnvironment>
#include <QtCore/QSettings>
#include <QtCore/QString>
#include <QtCore/QVariantMap>
#include <QtCore/QUrl>

class SettingsController : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString dataRoot READ dataRoot WRITE setDataRoot NOTIFY settingsChanged)
    Q_PROPERTY(QString libraryRootOverride READ libraryRootOverride WRITE setLibraryRootOverride NOTIFY settingsChanged)
    Q_PROPERTY(QString resolvedLibraryRoot READ resolvedLibraryRoot NOTIFY settingsChanged)
    Q_PROPERTY(QString atotPath READ atotPath WRITE setAtotPath NOTIFY settingsChanged)
    Q_PROPERTY(QString vcpkgRoot READ vcpkgRoot WRITE setVcpkgRoot NOTIFY settingsChanged)
    Q_PROPERTY(bool localOnly READ localOnly WRITE setLocalOnly NOTIFY settingsChanged)
    Q_PROPERTY(double cloudChunkMinutes READ cloudChunkMinutes WRITE setCloudChunkMinutes NOTIFY settingsChanged)
    Q_PROPERTY(QString modelAlias READ modelAlias WRITE setModelAlias NOTIFY settingsChanged)
    Q_PROPERTY(QString configPath READ configPath NOTIFY settingsChanged)
    Q_PROPERTY(QString cloudApiBase READ cloudApiBase WRITE setCloudApiBase NOTIFY settingsChanged)
    Q_PROPERTY(QString cloudApiKey READ cloudApiKey WRITE setCloudApiKey NOTIFY settingsChanged)
    Q_PROPERTY(QString cloudModel READ cloudModel WRITE setCloudModel NOTIFY settingsChanged)
    Q_PROPERTY(QString cloudTimeout READ cloudTimeout WRITE setCloudTimeout NOTIFY settingsChanged)
    Q_PROPERTY(QString cloudTemperature READ cloudTemperature WRITE setCloudTemperature NOTIFY settingsChanged)
    Q_PROPERTY(QString cloudMaxTokens READ cloudMaxTokens WRITE setCloudMaxTokens NOTIFY settingsChanged)
    Q_PROPERTY(QString cloudModelOptions READ cloudModelOptions WRITE setCloudModelOptions NOTIFY settingsChanged)
    Q_PROPERTY(QString summaryPrompt READ summaryPrompt WRITE setSummaryPrompt NOTIFY settingsChanged)
    Q_PROPERTY(QString titlePrompt READ titlePrompt WRITE setTitlePrompt NOTIFY settingsChanged)
    Q_PROPERTY(bool cloudConfigured READ cloudConfigured NOTIFY settingsChanged)

public:
    explicit SettingsController(QObject *parent = nullptr);

    QString dataRoot() const;
    void setDataRoot(const QString &value);

    QString libraryRootOverride() const;
    void setLibraryRootOverride(const QString &value);

    QString resolvedLibraryRoot() const;

    QString atotPath() const;
    void setAtotPath(const QString &value);

    QString vcpkgRoot() const;
    void setVcpkgRoot(const QString &value);

    bool localOnly() const;
    void setLocalOnly(bool value);

    double cloudChunkMinutes() const;
    void setCloudChunkMinutes(double value);

    QString modelAlias() const;
    void setModelAlias(const QString &value);

    QString configPath() const;

    QString cloudApiBase() const;
    void setCloudApiBase(const QString &value);

    QString cloudApiKey() const;
    void setCloudApiKey(const QString &value);

    QString cloudModel() const;
    void setCloudModel(const QString &value);

    QString cloudTimeout() const;
    void setCloudTimeout(const QString &value);

    QString cloudTemperature() const;
    void setCloudTemperature(const QString &value);

    QString cloudMaxTokens() const;
    void setCloudMaxTokens(const QString &value);

    QString cloudModelOptions() const;
    void setCloudModelOptions(const QString &value);

    QString summaryPrompt() const;
    void setSummaryPrompt(const QString &value);

    QString titlePrompt() const;
    void setTitlePrompt(const QString &value);

    bool cloudConfigured() const;

    Q_INVOKABLE void setDataRootUrl(const QUrl &url);
    Q_INVOKABLE void setLibraryRootUrl(const QUrl &url);
    Q_INVOKABLE void setAtotPathUrl(const QUrl &url);
    Q_INVOKABLE void resetDefaults();
    Q_INVOKABLE void reloadCloudConfig();
    Q_INVOKABLE bool saveCloudConfig();
    Q_INVOKABLE QVariantMap detectTools() const;
    Q_INVOKABLE QString resolvedAtotExecutable() const;

    QStringList atotArgumentPrefix() const;
    QProcessEnvironment processEnvironment() const;
    QStringList extraToolDirectories() const;

signals:
    void settingsChanged();

private:
    void load();
    void save();
    void updateValue(QString &field, const QString &value);
    void loadCloudConfig();
    bool saveConfigFile() const;

    QSettings m_settings;
    QString m_dataRoot;
    QString m_libraryRootOverride;
    QString m_atotPath;
    QString m_vcpkgRoot;
    bool m_localOnly = true;
    double m_cloudChunkMinutes = 20.0;
    QString m_modelAlias = "large-v3-turbo";
    QString m_cloudApiBase;
    QString m_cloudApiKey;
    QString m_cloudModel = "gpt-5.4-mini";
    QString m_cloudTimeout = "360";
    QString m_cloudTemperature = "1";
    QString m_cloudMaxTokens = "8192";
    QString m_cloudModelOptions = "gpt-5.4-mini, gpt-5.4, gpt-5.5, gpt-5.6-sol, gpt-5.6-terra, gpt-5.6-luna";
    QString m_summaryPrompt;
    QString m_titlePrompt;
};
