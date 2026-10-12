#pragma once

#include <QtCore/QJsonObject>
#include <QtCore/QString>
#include <QtCore/QStringList>

namespace AppPaths
{
QString defaultDataRoot();
QString cleanPath(QString path);
QString normalizeLibraryRoot(const QString &path);
QString resolveLibraryRoot(const QString &dataRoot, const QString &libraryRootOverride = {});
QString materialsRoot(const QString &dataRoot);
QString workRoot(const QString &dataRoot);
QString cacheRoot(const QString &dataRoot);
QString modelRoot(const QString &dataRoot);
QString defaultAtotPath(const QString &dataRoot);
QString applicationDir();
QString findExecutable(const QString &name, const QStringList &extraDirectories = {});
QStringList vcpkgToolDirectories(const QString &vcpkgRoot);
QString sanitizedSlug(const QString &value, int maxLength = 80);
QString audioSuffixFromUrl(const QString &url);
QString firstMediaFile(const QString &directoryPath);
QString readTextFile(const QString &path);
QJsonObject readJsonObject(const QString &path);
QString prettyJson(const QJsonObject &object);
bool writeJsonObject(const QString &path, const QJsonObject &object, QString *errorMessage = nullptr);
bool isExistingNonEmptyFile(const QString &path);
qint64 directorySize(const QString &path);
QString formatBytes(qint64 bytes);
}
