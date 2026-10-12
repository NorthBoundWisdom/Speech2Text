#pragma once

#include <QtCore/QJsonObject>
#include <QtCore/QObject>
#include <QtCore/QString>
#include <QtCore/QVariantList>
#include <QtCore/QVariantMap>

class SettingsController;

class LibraryController : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString dataRoot READ dataRoot NOTIFY libraryChanged)
    Q_PROPERTY(QString libraryRoot READ libraryRoot NOTIFY libraryChanged)
    Q_PROPERTY(QVariantList sources READ sources NOTIFY libraryChanged)
    Q_PROPERTY(QVariantList groups READ groups NOTIFY libraryChanged)
    Q_PROPERTY(QVariantList subscriptions READ subscriptions NOTIFY libraryChanged)
    Q_PROPERTY(QVariantList items READ items NOTIFY libraryChanged)
    Q_PROPERTY(QVariantList filteredItems READ filteredItems NOTIFY filteredItemsChanged)
    Q_PROPERTY(QVariantMap selectedItem READ selectedItem NOTIFY selectedItemChanged)
    Q_PROPERTY(QVariantMap selectedSnapshot READ selectedSnapshot NOTIFY selectedItemChanged)
    Q_PROPERTY(QVariantMap selectedSubscription READ selectedSubscription NOTIFY selectedSubscriptionChanged)
    Q_PROPERTY(QVariantList selectedSubscriptionItems READ selectedSubscriptionItems NOTIFY selectedSubscriptionChanged)
    Q_PROPERTY(QString selectedSubscriptionId READ selectedSubscriptionId NOTIFY selectedSubscriptionChanged)
    Q_PROPERTY(QString selectedSource READ selectedSource WRITE setSelectedSource NOTIFY filterChanged)
    Q_PROPERTY(QString selectedSourceTitle READ selectedSourceTitle NOTIFY filterChanged)
    Q_PROPERTY(bool showingSubscriptions READ showingSubscriptions NOTIFY filterChanged)
    Q_PROPERTY(QString searchText READ searchText WRITE setSearchText NOTIFY filterChanged)
    Q_PROPERTY(bool showArchived READ showArchived WRITE setShowArchived NOTIFY filterChanged)
    Q_PROPERTY(QString statusMessage READ statusMessage NOTIFY libraryChanged)
    Q_PROPERTY(int processedCount READ processedCount NOTIFY libraryChanged)
    Q_PROPERTY(int unprocessedCount READ unprocessedCount NOTIFY libraryChanged)

public:
    explicit LibraryController(SettingsController *settings, QObject *parent = nullptr);

    QString dataRoot() const;
    QString libraryRoot() const;
    QVariantList sources() const;
    QVariantList groups() const;
    QVariantList subscriptions() const;
    QVariantList items() const;
    QVariantList filteredItems() const;
    QVariantMap selectedItem() const;
    QVariantMap selectedSnapshot() const;
    QVariantMap selectedSubscription() const;
    QVariantList selectedSubscriptionItems() const;
    QString selectedSubscriptionId() const;
    QString selectedSource() const;
    void setSelectedSource(const QString &value);
    QString selectedSourceTitle() const;
    bool showingSubscriptions() const;
    QString searchText() const;
    void setSearchText(const QString &value);
    bool showArchived() const;
    void setShowArchived(bool value);
    QString statusMessage() const;
    int processedCount() const;
    int unprocessedCount() const;

    Q_INVOKABLE void refresh();
    Q_INVOKABLE void selectItem(const QString &episodeId);
    Q_INVOKABLE void selectSubscription(const QString &subscriptionId);
    Q_INVOKABLE QVariantMap itemById(const QString &episodeId) const;
    Q_INVOKABLE QVariantList subscriptionItems(const QString &subscriptionId) const;
    Q_INVOKABLE void setSelectedRead(bool read);
    Q_INVOKABLE void toggleSelectedStar();
    Q_INVOKABLE void setSelectedQueueStatus(const QString &status);
    Q_INVOKABLE void archiveSelected(bool archived);
    Q_INVOKABLE QString documentForSelectedTab(const QString &tab) const;

signals:
    void libraryChanged();
    void filteredItemsChanged();
    void selectedItemChanged();
    void selectedSubscriptionChanged();
    void filterChanged();
    void errorRaised(const QString &message);

private:
    QVariantMap scanEpisode(const QString &episodeDirectoryPath) const;
    QVariantMap snapshotForItem(const QVariantMap &item, bool full = true) const;
    QString metadataText(const QVariantMap &item) const;
    QString repairMarkdown(const QString &outputPath) const;
    QString latestFile(const QString &directoryPath, const QString &prefix, const QString &suffix) const;
    QString localAudioPath(const QString &episodeId, const QJsonObject &metadata) const;
    QString statusForSnapshot(const QVariantMap &snapshot, bool audioPresent, bool outputExists) const;
    QString detailForSnapshot(const QVariantMap &snapshot, bool audioPresent, bool outputExists) const;
    QString defaultNodeStatus(const QJsonObject &metadata) const;
    QString displayGroupName(const QString &value) const;
    bool updateSelectedJson(const QString &key, const QJsonValue &value);
    void loadGroups();
    void loadSubscriptions();
    void rebuildSources();
    void rebuildFilteredItems();
    void updateSelectionAfterRefresh(const QString &preferredId = {});
    bool itemMatchesSource(const QVariantMap &item) const;
    bool itemMatchesSearch(const QVariantMap &item) const;
    QVariantMap subscriptionById(const QString &subscriptionId) const;

    SettingsController *m_settings = nullptr;
    QString m_dataRoot;
    QString m_libraryRoot;
    QVariantList m_sources;
    QVariantList m_groups;
    QVariantList m_subscriptions;
    QVariantList m_items;
    QVariantList m_filteredItems;
    QVariantMap m_selectedItem;
    QVariantMap m_selectedSnapshot;
    QString m_selectedSubscriptionId;
    QString m_selectedSource = "library";
    QString m_searchText;
    bool m_showArchived = false;
    QString m_statusMessage;
};
