#pragma once

#include <QtCore/QObject>
#include <QtCore/QPointer>
#include <QtCore/QProcess>
#include <QtCore/QString>
#include <QtCore/QVariantList>
#include <QtCore/QVariantMap>

class LibraryController;
class SettingsController;

class JobController : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool running READ running NOTIFY jobStateChanged)
    Q_PROPERTY(QString stage READ stage NOTIFY jobStateChanged)
    Q_PROPERTY(QString logText READ logText NOTIFY logTextChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY jobStateChanged)
    Q_PROPERTY(QString lastResult READ lastResult NOTIFY jobStateChanged)
    Q_PROPERTY(int queuedJobCount READ queuedJobCount NOTIFY jobStateChanged)

public:
    explicit JobController(SettingsController *settings, LibraryController *library, QObject *parent = nullptr);

    bool running() const;
    QString stage() const;
    QString logText() const;
    QString lastError() const;
    QString lastResult() const;
    int queuedJobCount() const;

    Q_INVOKABLE void clearLog();
    Q_INVOKABLE void cancel();
    Q_INVOKABLE void runDoctor();
    Q_INVOKABLE void runLibraryStatus();
    Q_INVOKABLE void transcribeSelected(const QVariantMap &item);
    Q_INVOKABLE void transcribeAudio(const QString &audioPath);
    Q_INVOKABLE void qaSelected(const QVariantMap &item);
    Q_INVOKABLE void repairSelected(const QVariantMap &item, bool planOnly = false);
    Q_INVOKABLE void cloudPrepareSelected(const QVariantMap &item);
    Q_INVOKABLE void cloudSummarizeSelected(const QVariantMap &item);
    Q_INVOKABLE void cloudTitleSelected(const QVariantMap &item);
    Q_INVOKABLE void cloudGlossaryReviewSelected(const QVariantMap &item);
    Q_INVOKABLE void cloudPolishSelected(const QVariantMap &item);
    Q_INVOKABLE void exportSrtForFile(const QString &path, bool overwrite);
    Q_INVOKABLE void exportSrtForSelected(const QVariantMap &item, bool overwrite);
    Q_INVOKABLE void importXiaoyuzhou(const QString &url, const QString &groupName, bool download);
    Q_INVOKABLE void addSubscription(const QString &url, const QString &groupName, int limit);
    Q_INVOKABLE void refreshSubscriptions(bool refreshAll, const QString &subscriptionId, int limit);
    Q_INVOKABLE void removeSubscription(const QString &subscriptionId);
    Q_INVOKABLE void listSubscriptions();
    Q_INVOKABLE void configList();
    Q_INVOKABLE void configInspect();
    Q_INVOKABLE void configGet(const QString &key);
    Q_INVOKABLE void configSet(const QString &key, const QVariant &value);
    Q_INVOKABLE void runBatchTranscribe(const QVariantList &items);

signals:
    void jobStateChanged();
    void logTextChanged();
    void jobFinished(bool success);

private:
    struct JobRequest
    {
        QString stage;
        QString method;
        QVariantMap params;
        bool refreshLibrary = true;
    };

    void enqueueServiceJob(const QString &stage, const QString &method, const QVariantMap &params, bool refreshLibrary = true);
    void startNextJob();
    void appendLog(const QString &text);
    void failBeforeStart(const QString &message);
    QVariantMap selectedOutputParams(const QVariantMap &item) const;
    QVariantMap selectedAudioParams(const QVariantMap &item) const;
    QString selectedOutputPath(const QVariantMap &item) const;
    QString selectedAudioPath(const QVariantMap &item) const;
    QString localPromptFile(const QString &fileName, const QString &fallbackText) const;

    SettingsController *m_settings = nullptr;
    LibraryController *m_library = nullptr;
    QPointer<QProcess> m_process;
    QList<JobRequest> m_queue;
    JobRequest m_currentJob;
    bool m_running = false;
    QString m_stage = "Idle";
    QString m_logText;
    QString m_lastError;
    QString m_lastResult;
    QString m_currentOutput;
};

