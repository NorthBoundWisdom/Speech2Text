#include "JobController.h"

#include "AppPaths.h"
#include "AtotServiceClient.h"
#include "LibraryController.h"
#include "SettingsController.h"

#include <QtCore/QDir>
#include <QtCore/QFile>
#include <QtCore/QFileInfo>
#include <QtCore/QJsonDocument>
#include <QtCore/QJsonObject>
#include <QtCore/QTextStream>

JobController::JobController(SettingsController *settings, LibraryController *library, QObject *parent)
    : QObject(parent),
      m_settings(settings),
      m_library(library)
{
}

bool JobController::running() const
{
    return m_running;
}

QString JobController::stage() const
{
    return m_stage;
}

QString JobController::logText() const
{
    return m_logText;
}

QString JobController::lastError() const
{
    return m_lastError;
}

QString JobController::lastResult() const
{
    return m_lastResult;
}

int JobController::queuedJobCount() const
{
    return m_queue.size();
}

void JobController::clearLog()
{
    m_logText.clear();
    emit logTextChanged();
}

void JobController::cancel()
{
    m_queue.clear();
    if (m_process)
    {
        m_process->kill();
    }
    m_stage = "Cancelled";
    m_running = false;
    emit jobStateChanged();
}

void JobController::runDoctor()
{
    enqueueServiceJob("Doctor", "doctor", {}, false);
}

void JobController::runLibraryStatus()
{
    enqueueServiceJob("Library status", "library_status", {}, false);
}

void JobController::transcribeSelected(const QVariantMap &item)
{
    const QVariantMap params = selectedAudioParams(item);
    if (params.isEmpty())
    {
        return;
    }
    enqueueServiceJob("Transcribe", "transcribe", params, true);
}

void JobController::transcribeAudio(const QString &audioPath)
{
    const QString path = AppPaths::cleanPath(audioPath);
    if (!AppPaths::isExistingNonEmptyFile(path))
    {
        failBeforeStart(QString("Audio file is missing: %1").arg(path));
        return;
    }
    QVariantMap params;
    params["input"] = path;
    params["local_only"] = m_settings->localOnly();
    params["model"] = m_settings->modelAlias();
    enqueueServiceJob("Transcribe local file", "transcribe", params, true);
}

void JobController::qaSelected(const QVariantMap &item)
{
    const QVariantMap params = selectedOutputParams(item);
    if (!params.isEmpty())
    {
        enqueueServiceJob("QA", "qa", params, true);
    }
}

void JobController::repairSelected(const QVariantMap &item, bool planOnly)
{
    QVariantMap params = selectedOutputParams(item);
    if (params.isEmpty())
    {
        return;
    }
    params["plan_only"] = planOnly;
    params["local_only"] = m_settings->localOnly();
    enqueueServiceJob(planOnly ? "Repair plan" : "Repair", "repair", params, true);
}

void JobController::cloudPrepareSelected(const QVariantMap &item)
{
    QVariantMap params = selectedOutputParams(item);
    if (params.isEmpty())
    {
        return;
    }
    params["chunk_minutes"] = m_settings->cloudChunkMinutes();
    enqueueServiceJob("Cloud prepare", "cloud_prepare", params, true);
}

void JobController::cloudSummarizeSelected(const QVariantMap &item)
{
    QVariantMap params = selectedOutputParams(item);
    if (params.isEmpty())
    {
        return;
    }
    params["call_api"] = true;
    params["mode"] = "chunked";
    params["prompt_file"] = localPromptFile("app-summary.prompt.md", m_settings->summaryPrompt());
    enqueueServiceJob("Cloud summarize", "cloud_summarize", params, true);
}

void JobController::cloudTitleSelected(const QVariantMap &item)
{
    QVariantMap params = selectedOutputParams(item);
    if (params.isEmpty())
    {
        return;
    }
    params["call_api"] = true;
    params["force"] = true;
    params["prompt_file"] = localPromptFile("app-title.prompt.md", m_settings->titlePrompt());
    enqueueServiceJob("Cloud title", "cloud_title", params, true);
}

void JobController::cloudGlossaryReviewSelected(const QVariantMap &item)
{
    QVariantMap params = selectedOutputParams(item);
    if (params.isEmpty())
    {
        return;
    }
    params["call_api"] = true;
    enqueueServiceJob("Glossary review", "cloud_glossary_review", params, true);
}

void JobController::cloudPolishSelected(const QVariantMap &item)
{
    QVariantMap params = selectedOutputParams(item);
    if (params.isEmpty())
    {
        return;
    }
    params["call_api"] = true;
    enqueueServiceJob("Polish", "cloud_polish", params, true);
}

void JobController::exportSrtForFile(const QString &path, bool overwrite)
{
    const QString input = AppPaths::cleanPath(path);
    if (!AppPaths::isExistingNonEmptyFile(input))
    {
        failBeforeStart(QString("SRT input file is missing: %1").arg(input));
        return;
    }
    QVariantMap params;
    params["inputs"] = QVariantList{input};
    params["languages"] = QVariantList{"auto"};
    params["overwrite"] = overwrite;
    enqueueServiceJob("SRT", "srt", params, false);
}

void JobController::exportSrtForSelected(const QVariantMap &item, bool overwrite)
{
    const QString audio = selectedAudioPath(item);
    if (!audio.isEmpty() && AppPaths::isExistingNonEmptyFile(audio))
    {
        exportSrtForFile(audio, overwrite);
        return;
    }
    const QString output = selectedOutputPath(item);
    const QString transcript = QDir(output).filePath("transcript.readable.md");
    if (AppPaths::isExistingNonEmptyFile(transcript))
    {
        exportSrtForFile(transcript, overwrite);
        return;
    }
    failBeforeStart("No audio or readable transcript is available for SRT export.");
}

void JobController::importXiaoyuzhou(const QString &url, const QString &groupName, bool download)
{
    if (url.trimmed().isEmpty())
    {
        failBeforeStart("Enter a Xiaoyuzhou episode URL.");
        return;
    }
    QVariantMap params;
    params["url"] = url.trimmed();
    params["process_dir"] = AppPaths::materialsRoot(m_settings->dataRoot());
    params["group_name"] = groupName.trimmed().isEmpty() ? "Default" : groupName.trimmed();
    params["download"] = download;
    params["data_only"] = true;
    params["transcribe"] = false;
    enqueueServiceJob("Import Xiaoyuzhou", "import_xiaoyuzhou", params, true);
}

void JobController::addSubscription(const QString &url, const QString &groupName, int limit)
{
    if (url.trimmed().isEmpty())
    {
        failBeforeStart("Enter a subscription URL.");
        return;
    }
    QVariantList arguments{"add", url.trimmed(), "--group-name", groupName.trimmed().isEmpty() ? "Default" : groupName.trimmed()};
    if (limit > 0)
    {
        arguments << "--limit" << QString::number(limit);
    }
    QVariantMap params;
    params["arguments"] = arguments;
    enqueueServiceJob("Add subscription", "subscriptions", params, true);
}

void JobController::refreshSubscriptions(bool refreshAll, const QString &subscriptionId, int limit)
{
    QVariantList arguments{"refresh"};
    if (refreshAll)
    {
        arguments << "--all";
    }
    if (!subscriptionId.trimmed().isEmpty())
    {
        arguments << "--id" << subscriptionId.trimmed();
    }
    if (limit > 0)
    {
        arguments << "--limit" << QString::number(limit);
    }
    QVariantMap params;
    params["arguments"] = arguments;
    enqueueServiceJob("Refresh subscriptions", "subscriptions", params, true);
}

void JobController::removeSubscription(const QString &subscriptionId)
{
    if (subscriptionId.trimmed().isEmpty())
    {
        failBeforeStart("Select a subscription to remove.");
        return;
    }
    QVariantMap params;
    params["arguments"] = QVariantList{"remove", subscriptionId.trimmed()};
    enqueueServiceJob("Remove subscription", "subscriptions", params, true);
}

void JobController::listSubscriptions()
{
    QVariantMap params;
    params["arguments"] = QVariantList{"list"};
    enqueueServiceJob("List subscriptions", "subscriptions", params, false);
}

void JobController::configList()
{
    enqueueServiceJob("Config list", "config_list", {}, false);
}

void JobController::configInspect()
{
    enqueueServiceJob("Config inspect", "config_inspect", {}, false);
}

void JobController::configGet(const QString &key)
{
    if (key.trimmed().isEmpty())
    {
        failBeforeStart("Enter a config key.");
        return;
    }
    QVariantMap params;
    params["key"] = key.trimmed();
    enqueueServiceJob("Config get", "config_get", params, false);
}

void JobController::configSet(const QString &key, const QVariant &value)
{
    if (key.trimmed().isEmpty())
    {
        failBeforeStart("Enter a config key.");
        return;
    }
    QVariantMap params;
    params["key"] = key.trimmed();
    params["value"] = value;
    enqueueServiceJob("Config set", "config_set", params, false);
}

void JobController::runBatchTranscribe(const QVariantList &items)
{
    int count = 0;
    for (const QVariant &value : items)
    {
        const QVariantMap params = selectedAudioParams(value.toMap());
        if (!params.isEmpty())
        {
            m_queue.append({"Batch transcribe", "transcribe", params, true});
            ++count;
        }
    }
    if (count == 0)
    {
        failBeforeStart("No runnable audio files are in the current batch.");
        return;
    }
    appendLog(QString("Queued %1 transcribe jobs.\n").arg(count));
    startNextJob();
}

void JobController::enqueueServiceJob(const QString &stage, const QString &method, const QVariantMap &params, bool refreshLibrary)
{
    m_queue.append({stage, method, params, refreshLibrary});
    startNextJob();
}

void JobController::startNextJob()
{
    if (m_running || m_queue.isEmpty())
    {
        emit jobStateChanged();
        return;
    }

    const QString executable = m_settings->resolvedAtotExecutable();
    if (executable.isEmpty())
    {
        failBeforeStart("Missing atot executable. Set it in Settings or add it to PATH.");
        return;
    }

    m_currentJob = m_queue.takeFirst();
    m_currentOutput.clear();
    m_lastError.clear();
    m_lastResult.clear();
    m_stage = m_currentJob.stage;
    m_running = true;

    QDir().mkpath(AppPaths::cacheRoot(m_settings->dataRoot()));
    QStringList arguments = m_settings->atotArgumentPrefix();
    arguments += AtotServiceClient::serviceArguments(m_currentJob.method, m_currentJob.params);
    appendLog("\n$ " + AtotServiceClient::displayCommand(executable, arguments) + "\n");

    QProcess *process = new QProcess(this);
    m_process = process;
    process->setProgram(executable);
    process->setArguments(arguments);
    process->setWorkingDirectory(AppPaths::cacheRoot(m_settings->dataRoot()));
    process->setProcessEnvironment(m_settings->processEnvironment());
    process->setProcessChannelMode(QProcess::SeparateChannels);

    connect(process, &QProcess::readyReadStandardOutput, this, [this, process]() {
        const QString text = QString::fromUtf8(process->readAllStandardOutput());
        m_currentOutput += text;
        appendLog(text);
    });
    connect(process, &QProcess::readyReadStandardError, this, [this, process]() {
        const QString text = QString::fromUtf8(process->readAllStandardError());
        m_currentOutput += text;
        appendLog(text);
    });
    connect(process, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
        if (error == QProcess::FailedToStart)
        {
            m_lastError = "Failed to start atot process.";
            appendLog("\nERROR: " + m_lastError + "\n");
        }
    });
    connect(process, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), this, [this, process](int exitCode, QProcess::ExitStatus exitStatus) {
        const bool success = exitStatus == QProcess::NormalExit && exitCode == 0;
        m_lastResult = m_currentOutput.trimmed();
        if (!success)
        {
            m_lastError = QString("Command failed with exit code %1.").arg(exitCode);
            appendLog("\nERROR: " + m_lastError + "\n");
        }
        else
        {
            appendLog("\nDone.\n");
        }
        if (m_currentJob.refreshLibrary && m_library)
        {
            m_library->refresh();
        }
        process->deleteLater();
        m_process = nullptr;
        m_running = false;
        m_stage = success ? "Completed" : "Failed";
        emit jobStateChanged();
        emit jobFinished(success);
        if (!m_queue.isEmpty())
        {
            startNextJob();
        }
    });

    process->start();
    emit jobStateChanged();
}

void JobController::appendLog(const QString &text)
{
    if (text.isEmpty())
    {
        return;
    }
    m_logText += text;
    emit logTextChanged();
}

void JobController::failBeforeStart(const QString &message)
{
    m_lastError = message;
    m_stage = "Failed";
    m_running = false;
    appendLog("\nERROR: " + message + "\n");
    emit jobStateChanged();
    emit jobFinished(false);
}

QVariantMap JobController::selectedOutputParams(const QVariantMap &item) const
{
    const QString output = selectedOutputPath(item);
    if (output.isEmpty() || !QFileInfo(output).exists())
    {
        const_cast<JobController *>(this)->failBeforeStart(QString("Output directory is missing: %1").arg(output));
        return {};
    }
    QVariantMap params;
    params["output"] = output;
    return params;
}

QVariantMap JobController::selectedAudioParams(const QVariantMap &item) const
{
    const QString audio = selectedAudioPath(item);
    if (audio.isEmpty() || !AppPaths::isExistingNonEmptyFile(audio))
    {
        const_cast<JobController *>(this)->failBeforeStart(QString("Audio file is missing: %1").arg(audio));
        return {};
    }
    QVariantMap params;
    params["input"] = audio;
    params["job_dir"] = selectedOutputPath(item);
    params["local_only"] = m_settings->localOnly();
    params["model"] = m_settings->modelAlias();
    return params;
}

QString JobController::selectedOutputPath(const QVariantMap &item) const
{
    return AppPaths::cleanPath(item.value("outputPath").toString());
}

QString JobController::selectedAudioPath(const QVariantMap &item) const
{
    return AppPaths::cleanPath(item.value("audioPath").toString());
}

QString JobController::localPromptFile(const QString &fileName, const QString &fallbackText) const
{
    const QString directory = QDir(AppPaths::cacheRoot(m_settings->dataRoot())).filePath("qt-prompts");
    QDir().mkpath(directory);
    const QString path = QDir(directory).filePath(fileName);
    const QString existing = AppPaths::readTextFile(path);
    if (!QFileInfo(path).exists() || existing != fallbackText)
    {
        QFile file(path);
        if (file.open(QIODevice::WriteOnly | QIODevice::Text))
        {
            QTextStream stream(&file);
            stream << fallbackText;
        }
    }
    return QDir::toNativeSeparators(path);
}
