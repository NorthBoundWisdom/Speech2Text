#include "LibraryController.h"

#include "AppPaths.h"
#include "SettingsController.h"

#include <QtCore/QDateTime>
#include <QtCore/QDir>
#include <QtCore/QFileInfo>
#include <QtCore/QJsonArray>
#include <QtCore/QJsonDocument>
#include <QtCore/QJsonValue>
#include <QtCore/QSet>

namespace
{
QString stringValue(const QJsonObject &object, const QString &key)
{
    const QJsonValue value = object.value(key);
    if (value.isString())
    {
        return value.toString().trimmed();
    }
    if (value.isDouble())
    {
        return QString::number(value.toDouble());
    }
    if (value.isBool())
    {
        return value.toBool() ? "true" : "false";
    }
    return {};
}

bool boolValue(const QJsonValue &value)
{
    if (value.isBool())
    {
        return value.toBool();
    }
    if (value.isDouble())
    {
        return !qFuzzyIsNull(value.toDouble());
    }
    if (value.isString())
    {
        const QString text = value.toString().trimmed().toLower();
        return text == "true" || text == "yes" || text == "1";
    }
    return false;
}

QString dateString(const QFileInfo &info)
{
    return info.exists() ? info.lastModified().toString(Qt::ISODate) : QString();
}

QDateTime parseDate(const QString &value)
{
    if (value.isEmpty())
    {
        return {};
    }
    QDateTime parsed = QDateTime::fromString(value, Qt::ISODateWithMs);
    if (!parsed.isValid())
    {
        parsed = QDateTime::fromString(value, Qt::ISODate);
    }
    return parsed;
}

QVariantMap sourceMap(const QString &id, const QString &title, const QString &kind, int count)
{
    QVariantMap map;
    map["id"] = id;
    map["title"] = title;
    map["kind"] = kind;
    map["count"] = count;
    return map;
}

QString diskSuffix(qint64 bytes)
{
    return AppPaths::formatBytes(bytes);
}
}

LibraryController::LibraryController(SettingsController *settings, QObject *parent)
    : QObject(parent),
      m_settings(settings)
{
    connect(m_settings, &SettingsController::settingsChanged, this, &LibraryController::refresh);
}

QString LibraryController::dataRoot() const
{
    return m_dataRoot;
}

QString LibraryController::libraryRoot() const
{
    return m_libraryRoot;
}

QVariantList LibraryController::sources() const
{
    return m_sources;
}

QVariantList LibraryController::groups() const
{
    return m_groups;
}

QVariantList LibraryController::subscriptions() const
{
    return m_subscriptions;
}

QVariantList LibraryController::items() const
{
    return m_items;
}

QVariantList LibraryController::filteredItems() const
{
    return m_filteredItems;
}

QVariantMap LibraryController::selectedItem() const
{
    return m_selectedItem;
}

QVariantMap LibraryController::selectedSnapshot() const
{
    return m_selectedSnapshot;
}

QVariantMap LibraryController::selectedSubscription() const
{
    return subscriptionById(m_selectedSubscriptionId);
}

QVariantList LibraryController::selectedSubscriptionItems() const
{
    return subscriptionItems(m_selectedSubscriptionId);
}

QString LibraryController::selectedSubscriptionId() const
{
    return m_selectedSubscriptionId;
}

QString LibraryController::selectedSource() const
{
    return m_selectedSource;
}

void LibraryController::setSelectedSource(const QString &value)
{
    const QString normalized = value.trimmed().isEmpty() ? "library" : value.trimmed();
    if (m_selectedSource == normalized)
    {
        return;
    }
    m_selectedSource = normalized;
    if (m_selectedSource.startsWith("subscription:"))
    {
        m_selectedSubscriptionId = m_selectedSource.mid(QString("subscription:").size());
        m_selectedSource = "subscriptions";
    }
    else if (m_selectedSource != "subscriptions")
    {
        m_selectedSubscriptionId.clear();
    }
    rebuildFilteredItems();
    updateSelectionAfterRefresh();
    emit filterChanged();
    emit selectedSubscriptionChanged();
}

QString LibraryController::selectedSourceTitle() const
{
    for (const QVariant &value : m_sources)
    {
        const QVariantMap source = value.toMap();
        if (source.value("id").toString() == m_selectedSource)
        {
            return source.value("title").toString();
        }
    }
    if (m_selectedSource.startsWith("group:"))
    {
        return m_selectedSource.mid(QString("group:").size());
    }
    return "Library";
}

bool LibraryController::showingSubscriptions() const
{
    return m_selectedSource == "subscriptions" || m_selectedSource.startsWith("subscription:");
}

QString LibraryController::searchText() const
{
    return m_searchText;
}

void LibraryController::setSearchText(const QString &value)
{
    if (m_searchText == value)
    {
        return;
    }
    m_searchText = value;
    rebuildFilteredItems();
    updateSelectionAfterRefresh(m_selectedItem.value("id").toString());
    emit filterChanged();
}

bool LibraryController::showArchived() const
{
    return m_showArchived;
}

void LibraryController::setShowArchived(bool value)
{
    if (m_showArchived == value)
    {
        return;
    }
    m_showArchived = value;
    rebuildFilteredItems();
    updateSelectionAfterRefresh(m_selectedItem.value("id").toString());
    emit filterChanged();
}

QString LibraryController::statusMessage() const
{
    return m_statusMessage;
}

int LibraryController::processedCount() const
{
    int count = 0;
    for (const QVariant &value : m_items)
    {
        const QVariantMap item = value.toMap();
        if (!item.value("isArchived").toBool() && item.value("hasProcessed").toBool())
        {
            ++count;
        }
    }
    return count;
}

int LibraryController::unprocessedCount() const
{
    int count = 0;
    for (const QVariant &value : m_items)
    {
        const QVariantMap item = value.toMap();
        if (!item.value("isArchived").toBool() && !item.value("hasProcessed").toBool())
        {
            ++count;
        }
    }
    return count;
}

void LibraryController::refresh()
{
    const QString preferredId = m_selectedItem.value("id").toString();
    m_dataRoot = m_settings->dataRoot();
    m_libraryRoot = m_settings->resolvedLibraryRoot();
    m_items.clear();
    m_groups.clear();
    m_subscriptions.clear();
    m_statusMessage.clear();

    const QDir episodeRoot(QDir(m_libraryRoot).filePath("episodes"));
    if (!episodeRoot.exists())
    {
        m_statusMessage = QString("Library episodes directory not found: %1").arg(episodeRoot.absolutePath());
        rebuildSources();
        rebuildFilteredItems();
        updateSelectionAfterRefresh();
        emit libraryChanged();
        return;
    }

    const QFileInfoList episodeDirectories = episodeRoot.entryInfoList(QDir::Dirs | QDir::NoDotAndDotDot, QDir::Name);
    for (const QFileInfo &episodeDirectory : episodeDirectories)
    {
        QVariantMap item = scanEpisode(episodeDirectory.absoluteFilePath());
        if (!item.isEmpty())
        {
            m_items.append(item);
        }
    }

    std::sort(m_items.begin(), m_items.end(), [](const QVariant &lhs, const QVariant &rhs) {
        const QVariantMap left = lhs.toMap();
        const QVariantMap right = rhs.toMap();
        const QString leftModified = left.value("modifiedAt").toString();
        const QString rightModified = right.value("modifiedAt").toString();
        if (leftModified != rightModified)
        {
            return leftModified > rightModified;
        }
        return QString::localeAwareCompare(left.value("title").toString(), right.value("title").toString()) < 0;
    });

    loadGroups();
    loadSubscriptions();
    rebuildSources();
    rebuildFilteredItems();
    updateSelectionAfterRefresh(preferredId);
    m_statusMessage = QString("%1 episodes · %2 groups · %3 subscriptions")
        .arg(m_items.size())
        .arg(m_groups.size())
        .arg(m_subscriptions.size());
    emit libraryChanged();
}

void LibraryController::selectItem(const QString &episodeId)
{
    const QVariantMap item = itemById(episodeId);
    if (item.isEmpty())
    {
        return;
    }
    m_selectedItem = item;
    m_selectedSnapshot = snapshotForItem(item, true);
    emit selectedItemChanged();
}

void LibraryController::selectSubscription(const QString &subscriptionId)
{
    const QString normalized = subscriptionId.trimmed();
    if (m_selectedSubscriptionId == normalized)
    {
        return;
    }
    m_selectedSubscriptionId = normalized;
    if (showingSubscriptions())
    {
        m_selectedItem.clear();
        m_selectedSnapshot.clear();
        emit selectedItemChanged();
    }
    emit selectedSubscriptionChanged();
}

QVariantMap LibraryController::itemById(const QString &episodeId) const
{
    for (const QVariant &value : m_items)
    {
        const QVariantMap item = value.toMap();
        if (item.value("id").toString() == episodeId)
        {
            return item;
        }
    }
    return {};
}

QVariantList LibraryController::subscriptionItems(const QString &subscriptionId) const
{
    QVariantList matches;
    const QString normalized = subscriptionId.trimmed();
    if (normalized.isEmpty())
    {
        return matches;
    }
    for (const QVariant &value : m_items)
    {
        const QVariantMap item = value.toMap();
        if (!item.value("isArchived").toBool() && item.value("subscriptionID").toString() == normalized)
        {
            matches.append(item);
        }
    }
    std::sort(matches.begin(), matches.end(), [](const QVariant &lhs, const QVariant &rhs) {
        const QVariantMap left = lhs.toMap();
        const QVariantMap right = rhs.toMap();
        const QString leftPublished = left.value("publishedAt").toString();
        const QString rightPublished = right.value("publishedAt").toString();
        if (leftPublished != rightPublished)
        {
            return leftPublished > rightPublished;
        }
        return left.value("modifiedAt").toString() > right.value("modifiedAt").toString();
    });
    return matches;
}

void LibraryController::setSelectedRead(bool read)
{
    if (updateSelectedJson("app_read", QJsonValue(read)))
    {
        refresh();
    }
}

void LibraryController::toggleSelectedStar()
{
    const bool starred = m_selectedItem.value("isStarred").toBool();
    if (updateSelectedJson("app_star", QJsonValue(!starred)))
    {
        refresh();
    }
}

void LibraryController::setSelectedQueueStatus(const QString &status)
{
    const QString normalized = status.trimmed().isEmpty() ? "unread" : status.trimmed();
    if (updateSelectedJson("app_queue_status", QJsonValue(normalized)))
    {
        refresh();
    }
}

void LibraryController::archiveSelected(bool archived)
{
    const QString episodePath = m_selectedItem.value("episodeJsonPath").toString();
    QJsonObject metadata = AppPaths::readJsonObject(episodePath);
    if (metadata.isEmpty())
    {
        emit errorRaised(QString("Could not read episode metadata: %1").arg(episodePath));
        return;
    }
    metadata["app_status"] = archived ? "archived" : defaultNodeStatus(metadata);
    metadata["app_status_updated_at"] = QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs);
    QString error;
    if (!AppPaths::writeJsonObject(episodePath, metadata, &error))
    {
        emit errorRaised(QString("Could not update episode metadata: %1").arg(error));
        return;
    }
    refresh();
}

QString LibraryController::documentForSelectedTab(const QString &tab) const
{
    if (tab == "metadata")
    {
        return m_selectedSnapshot.value("metadataText").toString();
    }
    if (tab == "summary")
    {
        return m_selectedSnapshot.value("summaryText").toString();
    }
    if (tab == "transcript")
    {
        return m_selectedSnapshot.value("transcriptText").toString();
    }
    if (tab == "repair")
    {
        return m_selectedSnapshot.value("repairText").toString();
    }
    if (tab == "glossary")
    {
        return m_selectedSnapshot.value("glossaryText").toString();
    }
    if (tab == "log")
    {
        return m_selectedSnapshot.value("logText").toString();
    }
    return {};
}

QVariantMap LibraryController::scanEpisode(const QString &episodeDirectoryPath) const
{
    const QFileInfo episodeDirectory(episodeDirectoryPath);
    const QString episodeJsonPath = QDir(episodeDirectoryPath).filePath("episode.json");
    const QJsonObject metadata = AppPaths::readJsonObject(episodeJsonPath);
    if (metadata.isEmpty())
    {
        return {};
    }

    const QString episodeId = stringValue(metadata, "episode_id").isEmpty()
        ? episodeDirectory.fileName()
        : stringValue(metadata, "episode_id");
    const QString title = stringValue(metadata, "title").isEmpty() ? episodeId : stringValue(metadata, "title");
    const QString group = displayGroupName(stringValue(metadata, "app_group"));
    const QString audioPath = localAudioPath(episodeId, metadata);
    const QString outputPath = QDir(AppPaths::workRoot(m_dataRoot)).filePath(episodeId);
    const QString documentsPath = QDir(episodeDirectoryPath).filePath("documents");
    QVariantMap snapshotInput;
    snapshotInput["outputPath"] = QDir::toNativeSeparators(outputPath);
    snapshotInput["documentsPath"] = QDir::toNativeSeparators(documentsPath);
    const QVariantMap snapshot = snapshotForItem(snapshotInput, false);

    const bool hasFile = AppPaths::isExistingNonEmptyFile(audioPath);
    const bool hasDocuments = AppPaths::isExistingNonEmptyFile(QDir(documentsPath).filePath("summary.md"))
        || AppPaths::isExistingNonEmptyFile(QDir(documentsPath).filePath("transcript.md"));
    const bool outputExists = QFileInfo(outputPath).exists() || hasDocuments;
    const bool hasTranscript = snapshot.value("hasTranscript").toBool();
    const bool hasProcessed = hasDocuments || (snapshot.value("runStatus").toString() == "done" && hasTranscript);
    const qint64 diskBytes = snapshot.value("diskUsageBytes").toLongLong();

    const QString sourceUrl = stringValue(metadata, "source_url").isEmpty()
        ? stringValue(metadata, "canonical_url")
        : stringValue(metadata, "source_url");
    const QString publishedAt = stringValue(metadata, "local_published_at").isEmpty()
        ? stringValue(metadata, "published_at")
        : stringValue(metadata, "local_published_at");

    QFileInfo modifiedInfo(documentsPath);
    if (!modifiedInfo.exists())
    {
        modifiedInfo = QFileInfo(outputPath);
    }
    if (!modifiedInfo.exists())
    {
        modifiedInfo = QFileInfo(audioPath);
    }
    if (!modifiedInfo.exists())
    {
        modifiedInfo = QFileInfo(episodeJsonPath);
    }

    QVariantMap item;
    item["id"] = episodeId;
    item["title"] = title;
    item["groupName"] = group;
    item["nodeStatus"] = stringValue(metadata, "app_status").isEmpty() ? defaultNodeStatus(metadata) : stringValue(metadata, "app_status");
    item["audioPath"] = QDir::toNativeSeparators(audioPath);
    item["outputPath"] = QDir::toNativeSeparators(outputPath);
    item["documentsPath"] = QDir::toNativeSeparators(documentsPath);
    item["episodeJsonPath"] = QDir::toNativeSeparators(episodeJsonPath);
    item["episodeDirectory"] = QDir::toNativeSeparators(episodeDirectoryPath);
    item["status"] = statusForSnapshot(snapshot, hasFile, outputExists);
    item["detail"] = detailForSnapshot(snapshot, hasFile, outputExists);
    item["hasFile"] = hasFile;
    item["hasProcessed"] = hasProcessed;
    item["hasTranscript"] = hasTranscript;
    item["hasOutput"] = outputExists;
    item["runStatus"] = snapshot.value("runStatus").toString();
    item["qaStatus"] = snapshot.value("qaStatus").toString();
    item["source"] = stringValue(metadata, "source");
    item["sourceURL"] = sourceUrl;
    item["subscriptionID"] = stringValue(metadata, "subscription_id");
    item["seriesURL"] = stringValue(metadata, "series_url");
    item["mediaURL"] = stringValue(metadata, "audio_url");
    item["seriesName"] = stringValue(metadata, "series_name");
    item["publishedAt"] = publishedAt;
    item["duration"] = stringValue(metadata, "duration");
    item["description"] = stringValue(metadata, "description");
    item["imageURL"] = stringValue(metadata, "image_url");
    item["isRead"] = boolValue(metadata.value("app_read"));
    item["isStarred"] = boolValue(metadata.value("app_star"));
    item["queueStatus"] = stringValue(metadata, "app_queue_status").isEmpty() ? "unread" : stringValue(metadata, "app_queue_status");
    item["isArchived"] = stringValue(metadata, "app_status") == "archived";
    item["modifiedAt"] = dateString(modifiedInfo);
    item["processedAt"] = stringValue(metadata, "processed_at");
    item["diskUsage"] = diskSuffix(diskBytes);
    item["metadataJson"] = AppPaths::prettyJson(metadata);
    return item;
}

QVariantMap LibraryController::snapshotForItem(const QVariantMap &item, bool full) const
{
    const QString outputPath = item.value("outputPath").toString();
    const QString documentsPath = item.value("documentsPath").toString();
    const QDir output(outputPath);
    const QDir documents(documentsPath);

    const QString transcriptFromDocuments = documents.filePath("transcript.md");
    const QString transcriptFromOutput = output.filePath("transcript.readable.md");
    const QString summaryFromDocuments = documents.filePath("summary.md");
    const QString summaryFromCloud = output.filePath("cloud/summary.md");

    const QString transcriptText = AppPaths::readTextFile(transcriptFromDocuments).isEmpty()
        ? AppPaths::readTextFile(transcriptFromOutput)
        : AppPaths::readTextFile(transcriptFromDocuments);
    QString summaryText = AppPaths::readTextFile(summaryFromDocuments);
    if (summaryText.isEmpty())
    {
        summaryText = AppPaths::readTextFile(summaryFromCloud);
    }

    QJsonObject run = AppPaths::readJsonObject(output.filePath("run.json"));
    QString runStatus = "missing";
    if (!run.isEmpty())
    {
        runStatus = run.value("success").isBool() ? (run.value("success").toBool() ? "done" : "failed") : "running";
    }
    else if (QFileInfo(output.filePath("chunks_manifest.json")).exists())
    {
        runStatus = "running";
    }

    int completedChunks = 0;
    int totalChunks = 0;
    const QJsonArray chunks = run.value("chunks").toArray();
    totalChunks = chunks.size();
    const QJsonObject counts = run.value("chunk_status_counts").toObject();
    completedChunks += counts.value("transcribed").toInt();
    completedChunks += counts.value("transcribed_after_cache_mismatch").toInt();
    completedChunks += counts.value("skipped_existing").toInt();

    const QJsonObject qa = AppPaths::readJsonObject(output.filePath("qa.json"));
    QString qaStatus = "missing";
    if (qa.value("success").isBool())
    {
        qaStatus = qa.value("success").toBool() ? "pass" : "fail";
    }

    const qint64 diskUsageBytes = AppPaths::directorySize(outputPath) + AppPaths::directorySize(documentsPath);

    QVariantMap snapshot;
    snapshot["summaryText"] = full ? summaryText : (summaryText.isEmpty() ? QString() : QString("available"));
    snapshot["transcriptText"] = full ? transcriptText : (transcriptText.isEmpty() ? QString() : QString("available"));
    snapshot["hasTranscript"] = !transcriptText.trimmed().isEmpty();
    snapshot["qaText"] = full ? AppPaths::readTextFile(output.filePath("qa.md")) : QString();
    snapshot["reviewText"] = full ? AppPaths::readTextFile(output.filePath("review.md")) : QString();
    snapshot["repairText"] = full ? repairMarkdown(outputPath) : QString();
    snapshot["glossaryText"] = full
        ? AppPaths::readTextFile(output.filePath("cloud/glossary_editor_items.md"))
        : QString();
    if (full && snapshot.value("glossaryText").toString().isEmpty())
    {
        snapshot["glossaryText"] = AppPaths::readTextFile(output.filePath("cloud/glossary_suggestions.md"));
    }
    if (full && snapshot.value("glossaryText").toString().isEmpty())
    {
        snapshot["glossaryText"] = AppPaths::readTextFile(output.filePath("glossary.effective.json"));
    }
    snapshot["runText"] = full ? AppPaths::prettyJson(run) : QString();
    const QString events = full ? AppPaths::readTextFile(output.filePath("events.jsonl")) : QString();
    snapshot["logText"] = QStringList({snapshot.value("runText").toString(), events}).join("\n").trimmed();
    snapshot["runStatus"] = runStatus;
    snapshot["qaStatus"] = qaStatus;
    snapshot["completedChunks"] = completedChunks;
    snapshot["totalChunks"] = totalChunks;
    snapshot["chunkProgress"] = totalChunks > 0 ? QString("%1/%2").arg(completedChunks).arg(totalChunks) : "0/0";
    snapshot["diskUsageBytes"] = diskUsageBytes;
    snapshot["cloudStatus"] = QFileInfo(output.filePath("cloud/summary.md")).exists() ? "complete" : "missing";
    if (full)
    {
        snapshot["metadataText"] = metadataText(item);
    }
    return snapshot;
}

QString LibraryController::metadataText(const QVariantMap &item) const
{
    QStringList lines;
    lines << "# " + item.value("title").toString() << "";
    auto append = [&lines](const QString &label, const QString &value) {
        if (!value.trimmed().isEmpty())
        {
            lines << QString("- %1: %2").arg(label, value.trimmed());
        }
    };
    append("Podcast", item.value("seriesName").toString());
    append("Source", item.value("source").toString());
    append("Group", item.value("groupName").toString());
    append("Original link", item.value("sourceURL").toString());
    append("Podcast link", item.value("seriesURL").toString());
    append("Published at", item.value("publishedAt").toString());
    append("Duration", item.value("duration").toString());
    append("Audio link", item.value("mediaURL").toString());
    append("Local audio", item.value("audioPath").toString());
    append("Output directory", item.value("outputPath").toString());
    append("Status", item.value("status").toString());
    append("Queue", item.value("queueStatus").toString());
    const QString description = item.value("description").toString().trimmed();
    if (!description.isEmpty())
    {
        lines << "" << "## Overview" << "" << description;
    }
    const QString metadataJson = item.value("metadataJson").toString();
    if (!metadataJson.isEmpty())
    {
        lines << "" << "## Raw Metadata" << "" << "```json" << metadataJson << "```";
    }
    return lines.join("\n");
}

QString LibraryController::repairMarkdown(const QString &outputPath) const
{
    QStringList sections;
    sections << "# Repair";
    const QDir repairDir(QDir(outputPath).filePath("repair"));
    const QString plan = AppPaths::prettyJson(AppPaths::readJsonObject(repairDir.filePath("repair_plan.json")));
    if (!plan.isEmpty())
    {
        sections << "## Plan\n\n```json\n" + plan + "\n```";
    }
    const QString runPath = latestFile(repairDir.absolutePath(), "repair_run_", ".json");
    if (!runPath.isEmpty())
    {
        const QString runText = AppPaths::prettyJson(AppPaths::readJsonObject(runPath));
        if (!runText.isEmpty())
        {
            sections << "## Latest Run\n\n```json\n" + runText + "\n```";
        }
    }
    const QString diffPath = latestFile(repairDir.absolutePath(), "diff_", ".md");
    if (!diffPath.isEmpty())
    {
        const QString diff = AppPaths::readTextFile(diffPath);
        if (!diff.isEmpty())
        {
            sections << "## Latest Diff\n\n" + diff;
        }
    }
    if (sections.size() == 1)
    {
        sections << "No repair artifacts are available.";
    }
    return sections.join("\n\n");
}

QString LibraryController::latestFile(const QString &directoryPath, const QString &prefix, const QString &suffix) const
{
    const QDir dir(directoryPath);
    const QFileInfoList files = dir.entryInfoList(QDir::Files, QDir::Name | QDir::Reversed);
    for (const QFileInfo &file : files)
    {
        if (file.fileName().startsWith(prefix) && file.fileName().endsWith(suffix))
        {
            return file.absoluteFilePath();
        }
    }
    return {};
}

QString LibraryController::localAudioPath(const QString &episodeId, const QJsonObject &metadata) const
{
    const QDir materialDir(QDir(AppPaths::materialsRoot(m_dataRoot)).filePath(episodeId));
    const QString existing = AppPaths::firstMediaFile(materialDir.absolutePath());
    if (!existing.isEmpty())
    {
        return existing;
    }
    const QString mediaFilename = stringValue(metadata, "media_filename");
    if (!mediaFilename.isEmpty())
    {
        return QDir::toNativeSeparators(materialDir.filePath(mediaFilename));
    }
    const QString title = stringValue(metadata, "title").isEmpty() ? episodeId : stringValue(metadata, "title");
    return QDir::toNativeSeparators(materialDir.filePath(AppPaths::sanitizedSlug(title) + AppPaths::audioSuffixFromUrl(stringValue(metadata, "audio_url"))));
}

QString LibraryController::statusForSnapshot(const QVariantMap &snapshot, bool audioPresent, bool outputExists) const
{
    if (!audioPresent)
    {
        return "Audio pending";
    }
    const QString runStatus = snapshot.value("runStatus").toString();
    if (runStatus == "running")
    {
        return "Incomplete";
    }
    if (runStatus == "failed")
    {
        return "Failed";
    }
    const QString qaStatus = snapshot.value("qaStatus").toString();
    if (qaStatus == "pass")
    {
        return "QA pass";
    }
    if (qaStatus == "fail")
    {
        return "QA fail";
    }
    if (runStatus == "done")
    {
        return "Processed";
    }
    return outputExists ? "Incomplete" : "Not processed";
}

QString LibraryController::detailForSnapshot(const QVariantMap &snapshot, bool audioPresent, bool outputExists) const
{
    if (!audioPresent)
    {
        return "Metadata exists";
    }
    const int totalChunks = snapshot.value("totalChunks").toInt();
    if (totalChunks > 0)
    {
        return QString("Chunks %1%2")
            .arg(snapshot.value("chunkProgress").toString(), diskSuffix(snapshot.value("diskUsageBytes").toLongLong()));
    }
    if (snapshot.value("hasTranscript").toBool())
    {
        return QString("Transcript available%1").arg(diskSuffix(snapshot.value("diskUsageBytes").toLongLong()));
    }
    return outputExists ? QString("Output exists%1").arg(diskSuffix(snapshot.value("diskUsageBytes").toLongLong())) : QString();
}

QString LibraryController::defaultNodeStatus(const QJsonObject &metadata) const
{
    if (stringValue(metadata, "source") == "local")
    {
        return "import";
    }
    if (!stringValue(metadata, "source_url").isEmpty()
        || !stringValue(metadata, "canonical_url").isEmpty()
        || !stringValue(metadata, "audio_url").isEmpty())
    {
        return "link";
    }
    return "outside";
}

QString LibraryController::displayGroupName(const QString &value) const
{
    const QString trimmed = value.trimmed();
    return trimmed.isEmpty() ? "Default" : trimmed;
}

bool LibraryController::updateSelectedJson(const QString &key, const QJsonValue &value)
{
    const QString episodePath = m_selectedItem.value("episodeJsonPath").toString();
    if (episodePath.isEmpty())
    {
        return false;
    }
    QJsonObject metadata = AppPaths::readJsonObject(episodePath);
    if (metadata.isEmpty())
    {
        emit errorRaised(QString("Could not read episode metadata: %1").arg(episodePath));
        return false;
    }
    metadata[key] = value;
    metadata["app_status_updated_at"] = QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs);
    QString error;
    if (!AppPaths::writeJsonObject(episodePath, metadata, &error))
    {
        emit errorRaised(QString("Could not update episode metadata: %1").arg(error));
        return false;
    }
    return true;
}

void LibraryController::loadGroups()
{
    QSet<QString> names;
    for (const QVariant &value : m_items)
    {
        names.insert(value.toMap().value("groupName").toString());
    }
    const QDir groupsDir(QDir(m_libraryRoot).filePath("groups"));
    const QFileInfoList files = groupsDir.entryInfoList({"*.json"}, QDir::Files, QDir::Name);
    for (const QFileInfo &file : files)
    {
        const QJsonObject group = AppPaths::readJsonObject(file.absoluteFilePath());
        const QString title = displayGroupName(stringValue(group, "title").isEmpty() ? file.baseName() : stringValue(group, "title"));
        names.insert(title);
    }
    names.insert("Default");

    QStringList sorted = names.values();
    sorted.sort(Qt::CaseInsensitive);
    for (const QString &name : sorted)
    {
        int count = 0;
        for (const QVariant &value : m_items)
        {
            const QVariantMap item = value.toMap();
            if (!item.value("isArchived").toBool() && item.value("groupName").toString() == name)
            {
                ++count;
            }
        }
        QVariantMap group;
        group["id"] = name;
        group["title"] = name;
        group["count"] = count;
        m_groups.append(group);
    }
}

void LibraryController::loadSubscriptions()
{
    const QDir subscriptionsDir(QDir(m_libraryRoot).filePath("subscriptions"));
    const QFileInfoList files = subscriptionsDir.entryInfoList({"*.json"}, QDir::Files, QDir::Name);
    for (const QFileInfo &file : files)
    {
        const QJsonObject subscription = AppPaths::readJsonObject(file.absoluteFilePath());
        const QString id = stringValue(subscription, "id").isEmpty() ? file.baseName() : stringValue(subscription, "id");
        int count = 0;
        int processed = 0;
        int unprocessed = 0;
        for (const QVariant &value : m_items)
        {
            const QVariantMap item = value.toMap();
            if (!item.value("isArchived").toBool() && item.value("subscriptionID").toString() == id)
            {
                ++count;
                if (item.value("hasProcessed").toBool())
                {
                    ++processed;
                }
                else
                {
                    ++unprocessed;
                }
            }
        }
        QVariantMap map;
        map["id"] = id;
        map["title"] = stringValue(subscription, "title").isEmpty() ? id : stringValue(subscription, "title");
        map["source"] = stringValue(subscription, "source");
        map["url"] = stringValue(subscription, "url");
        map["feedURL"] = stringValue(subscription, "feed_url");
        map["groupName"] = displayGroupName(stringValue(subscription, "group_name"));
        map["createdAt"] = stringValue(subscription, "created_at");
        map["lastCheckedAt"] = stringValue(subscription, "last_checked_at");
        map["count"] = count;
        map["processedCount"] = processed;
        map["unprocessedCount"] = unprocessed;
        map["metadataJson"] = AppPaths::prettyJson(subscription);
        m_subscriptions.append(map);
    }

    std::sort(m_subscriptions.begin(), m_subscriptions.end(), [](const QVariant &lhs, const QVariant &rhs) {
        return QString::localeAwareCompare(lhs.toMap().value("title").toString(), rhs.toMap().value("title").toString()) < 0;
    });
}

void LibraryController::rebuildSources()
{
    int active = 0;
    int today = 0;
    int unprocessed = 0;
    int processed = 0;
    int starred = 0;
    int archived = 0;
    const QDate todayDate = QDate::currentDate();
    for (const QVariant &value : m_items)
    {
        const QVariantMap item = value.toMap();
        const bool isArchived = item.value("isArchived").toBool();
        if (isArchived)
        {
            ++archived;
            continue;
        }
        ++active;
        if (!item.value("hasProcessed").toBool())
        {
            ++unprocessed;
        }
        else
        {
            ++processed;
        }
        if (item.value("isStarred").toBool())
        {
            ++starred;
        }
        if (parseDate(item.value("modifiedAt").toString()).date() == todayDate)
        {
            ++today;
        }
    }

    QVariantList sources;
    sources << sourceMap("library", "Library", "root", active)
            << sourceMap("smart:today", "Today", "smart", today)
            << sourceMap("smart:unprocessed", "Unprocessed", "smart", unprocessed)
            << sourceMap("smart:processed", "Processed", "smart", processed)
            << sourceMap("smart:starred", "Starred", "smart", starred)
            << sourceMap("smart:archive", "Archive", "smart", archived)
            << sourceMap("subscriptions", "Subscriptions", "root", m_subscriptions.size());
    for (const QVariant &value : m_groups)
    {
        const QVariantMap group = value.toMap();
        sources << sourceMap("group:" + group.value("id").toString(), group.value("title").toString(), "group", group.value("count").toInt());
    }
    m_sources = sources;
}

void LibraryController::rebuildFilteredItems()
{
    QVariantList filtered;
    for (const QVariant &value : m_items)
    {
        const QVariantMap item = value.toMap();
        if (itemMatchesSource(item) && itemMatchesSearch(item))
        {
            filtered.append(item);
        }
    }
    m_filteredItems = filtered;
    emit filteredItemsChanged();
}

void LibraryController::updateSelectionAfterRefresh(const QString &preferredId)
{
    if (showingSubscriptions())
    {
        if (!m_selectedSubscriptionId.isEmpty() && subscriptionById(m_selectedSubscriptionId).isEmpty())
        {
            m_selectedSubscriptionId.clear();
        }
        m_selectedItem.clear();
        m_selectedSnapshot.clear();
        emit selectedSubscriptionChanged();
        emit selectedItemChanged();
        return;
    }

    const QString current = preferredId.isEmpty() ? m_selectedItem.value("id").toString() : preferredId;
    if (!current.isEmpty())
    {
        for (const QVariant &value : m_filteredItems)
        {
            const QVariantMap item = value.toMap();
            if (item.value("id").toString() == current)
            {
                m_selectedItem = item;
                m_selectedSnapshot = snapshotForItem(item, true);
                emit selectedItemChanged();
                return;
            }
        }
    }
    if (!m_filteredItems.isEmpty())
    {
        m_selectedItem = m_filteredItems.first().toMap();
        m_selectedSnapshot = snapshotForItem(m_selectedItem, true);
    }
    else
    {
        m_selectedItem.clear();
        m_selectedSnapshot.clear();
    }
    emit selectedItemChanged();
}

bool LibraryController::itemMatchesSource(const QVariantMap &item) const
{
    const bool archived = item.value("isArchived").toBool();
    if (m_selectedSource == "smart:archive")
    {
        return archived;
    }
    if (!m_showArchived && archived)
    {
        return false;
    }
    if (m_selectedSource == "library")
    {
        return true;
    }
    if (m_selectedSource == "smart:today")
    {
        return parseDate(item.value("modifiedAt").toString()).date() == QDate::currentDate();
    }
    if (m_selectedSource == "smart:unprocessed")
    {
        return !item.value("hasProcessed").toBool();
    }
    if (m_selectedSource == "smart:processed")
    {
        return item.value("hasProcessed").toBool();
    }
    if (m_selectedSource == "smart:starred")
    {
        return item.value("isStarred").toBool();
    }
    if (m_selectedSource == "subscriptions")
    {
        return !item.value("subscriptionID").toString().isEmpty();
    }
    if (m_selectedSource.startsWith("group:"))
    {
        return item.value("groupName").toString() == m_selectedSource.mid(QString("group:").size());
    }
    if (m_selectedSource.startsWith("subscription:"))
    {
        return item.value("subscriptionID").toString() == m_selectedSource.mid(QString("subscription:").size());
    }
    return true;
}

bool LibraryController::itemMatchesSearch(const QVariantMap &item) const
{
    const QString query = m_searchText.trimmed();
    if (query.isEmpty())
    {
        return true;
    }
    const QString haystack = QStringList({
        item.value("title").toString(),
        item.value("seriesName").toString(),
        item.value("description").toString(),
        item.value("sourceURL").toString(),
        item.value("groupName").toString()
    }).join("\n");
    return haystack.contains(query, Qt::CaseInsensitive);
}

QVariantMap LibraryController::subscriptionById(const QString &subscriptionId) const
{
    for (const QVariant &value : m_subscriptions)
    {
        const QVariantMap subscription = value.toMap();
        if (subscription.value("id").toString() == subscriptionId)
        {
            return subscription;
        }
    }
    return {};
}
