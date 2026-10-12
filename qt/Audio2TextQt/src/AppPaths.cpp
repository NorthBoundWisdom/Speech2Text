#include "AppPaths.h"

#include <QtCore/QCoreApplication>
#include <QtCore/QDir>
#include <QtCore/QDirIterator>
#include <QtCore/QFile>
#include <QtCore/QFileInfo>
#include <QtCore/QJsonDocument>
#include <QtCore/QProcessEnvironment>
#include <QtCore/QRegularExpression>
#include <QtCore/QStandardPaths>
#include <QtCore/QTextStream>
#include <QtCore/QUrl>

namespace
{
bool looksLikeLibraryRoot(const QString &path)
{
    const QDir dir(path);
    return dir.exists("episodes") || dir.exists("manifest.json") || dir.exists("subscriptions");
}

QString withNativeSeparators(const QString &path)
{
    return QDir::toNativeSeparators(QDir::cleanPath(path));
}
}

namespace AppPaths
{
QString defaultDataRoot()
{
    const QString documents = QStandardPaths::writableLocation(QStandardPaths::DocumentsLocation);
    const QString base = documents.isEmpty() ? QDir::homePath() + "/Documents" : documents;
    return withNativeSeparators(base + "/SpeechToTextData");
}

QString cleanPath(QString path)
{
    path = path.trimmed();
    if (path.startsWith("file:", Qt::CaseInsensitive))
    {
        path = QUrl(path).toLocalFile();
    }
    if (path == "~")
    {
        path = QDir::homePath();
    }
    else if (path.startsWith("~/"))
    {
        path = QDir::homePath() + path.mid(1);
    }
    return path.isEmpty() ? path : withNativeSeparators(path);
}

QString normalizeLibraryRoot(const QString &path)
{
    const QString cleaned = cleanPath(path);
    if (cleaned.isEmpty())
    {
        return cleaned;
    }
    const QFileInfo info(cleaned);
    if (info.fileName() == "Audio2TextLibrary")
    {
        return withNativeSeparators(cleaned);
    }
    return withNativeSeparators(QDir(cleaned).filePath("Audio2TextLibrary"));
}

QString resolveLibraryRoot(const QString &dataRoot, const QString &libraryRootOverride)
{
    const QString overridePath = cleanPath(libraryRootOverride);
    if (!overridePath.isEmpty())
    {
        if (looksLikeLibraryRoot(overridePath))
        {
            return withNativeSeparators(overridePath);
        }
        return normalizeLibraryRoot(overridePath);
    }

    const QString root = cleanPath(dataRoot);
    if (looksLikeLibraryRoot(root))
    {
        return withNativeSeparators(root);
    }
    const QString child = QDir(root).filePath("Audio2TextLibrary");
    if (looksLikeLibraryRoot(child))
    {
        return withNativeSeparators(child);
    }
    return withNativeSeparators(child);
}

QString materialsRoot(const QString &dataRoot)
{
    return withNativeSeparators(QDir(cleanPath(dataRoot)).filePath("materials"));
}

QString workRoot(const QString &dataRoot)
{
    return withNativeSeparators(QDir(cleanPath(dataRoot)).filePath("work"));
}

QString cacheRoot(const QString &dataRoot)
{
    return withNativeSeparators(QDir(cleanPath(dataRoot)).filePath("cache"));
}

QString modelRoot(const QString &dataRoot)
{
    return withNativeSeparators(QDir(cleanPath(dataRoot)).filePath("model"));
}

QString defaultAtotPath(const QString &dataRoot)
{
#ifdef Q_OS_WIN
    const QString candidate = QDir(cleanPath(dataRoot)).filePath("env/Scripts/atot.exe");
#else
    const QString candidate = QDir(cleanPath(dataRoot)).filePath("env/bin/atot");
#endif
    return QFileInfo(candidate).isExecutable() ? withNativeSeparators(candidate) : QString();
}

QString applicationDir()
{
    const QString path = QCoreApplication::applicationDirPath();
    return path.isEmpty() ? QString() : withNativeSeparators(path);
}

QString findExecutable(const QString &name, const QStringList &extraDirectories)
{
    const QString configured = cleanPath(name);
    if (QFileInfo(configured).isExecutable())
    {
        return configured;
    }

    const QString foundInExtra = QStandardPaths::findExecutable(name, extraDirectories);
    if (!foundInExtra.isEmpty())
    {
        return withNativeSeparators(foundInExtra);
    }
    const QString found = QStandardPaths::findExecutable(name);
    return found.isEmpty() ? QString() : withNativeSeparators(found);
}

QStringList vcpkgToolDirectories(const QString &vcpkgRoot)
{
    QStringList directories;
    const QString root = cleanPath(vcpkgRoot.isEmpty()
        ? QProcessEnvironment::systemEnvironment().value("VCPKG_ROOT")
        : vcpkgRoot);
    if (root.isEmpty())
    {
        return directories;
    }
    const QDir installedRoot(QDir(root).filePath("installed"));
    const QFileInfoList triplets = installedRoot.entryInfoList(QDir::Dirs | QDir::NoDotAndDotDot);
    for (const QFileInfo &triplet : triplets)
    {
        const QDir dir(triplet.absoluteFilePath());
        directories << withNativeSeparators(dir.filePath("bin"));
        directories << withNativeSeparators(dir.filePath("tools/ffmpeg"));
    }
    directories.removeDuplicates();
    directories.erase(
        std::remove_if(directories.begin(), directories.end(), [](const QString &path) {
            return !QFileInfo(path).isDir();
        }),
        directories.end());
    return directories;
}

QString sanitizedSlug(const QString &value, int maxLength)
{
    QString output;
    output.reserve(value.size());
    for (const QChar ch : value.trimmed())
    {
        if (ch.isLetterOrNumber() || (ch.unicode() >= 0x3400 && ch.unicode() <= 0x9fff))
        {
            output.append(ch);
        }
        else
        {
            output.append('-');
        }
    }
    output.replace(QRegularExpression("-+"), "-");
    output = output.trimmed();
    while (output.startsWith('-') || output.startsWith('.') || output.startsWith(' '))
    {
        output.remove(0, 1);
    }
    while (output.endsWith('-') || output.endsWith('.') || output.endsWith(' '))
    {
        output.chop(1);
    }
    if (output.isEmpty())
    {
        output = "audio";
    }
    return output.left(maxLength);
}

QString audioSuffixFromUrl(const QString &url)
{
    const QString path = QUrl(url).path();
    const QString suffix = QFileInfo(path).suffix().toLower();
    static const QStringList supported = {"m4a", "mp3", "wav", "flac", "aac", "mp4", "m4v", "mov", "mkv", "webm"};
    return supported.contains(suffix) ? "." + suffix : ".mp3";
}

QString firstMediaFile(const QString &directoryPath)
{
    static const QStringList filters = {"*.m4a", "*.mp3", "*.wav", "*.flac", "*.aac", "*.mp4", "*.m4v", "*.mov", "*.mkv", "*.webm"};
    const QDir dir(directoryPath);
    const QFileInfoList files = dir.entryInfoList(filters, QDir::Files, QDir::Name);
    return files.isEmpty() ? QString() : withNativeSeparators(files.first().absoluteFilePath());
}

QString readTextFile(const QString &path)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text))
    {
        return {};
    }
    return QString::fromUtf8(file.readAll());
}

QJsonObject readJsonObject(const QString &path)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly))
    {
        return {};
    }
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll());
    return document.isObject() ? document.object() : QJsonObject();
}

QString prettyJson(const QJsonObject &object)
{
    if (object.isEmpty())
    {
        return {};
    }
    return QString::fromUtf8(QJsonDocument(object).toJson(QJsonDocument::Indented));
}

bool writeJsonObject(const QString &path, const QJsonObject &object, QString *errorMessage)
{
    QFileInfo info(path);
    QDir().mkpath(info.absolutePath());
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate))
    {
        if (errorMessage)
        {
            *errorMessage = file.errorString();
        }
        return false;
    }
    file.write(QJsonDocument(object).toJson(QJsonDocument::Indented));
    return true;
}

bool isExistingNonEmptyFile(const QString &path)
{
    const QFileInfo info(path);
    return info.isFile() && info.size() > 0;
}

qint64 directorySize(const QString &path)
{
    if (path.trimmed().isEmpty() || !QFileInfo(path).isDir())
    {
        return 0;
    }
    qint64 total = 0;
    QDirIterator iterator(path, QDir::Files, QDirIterator::Subdirectories);
    while (iterator.hasNext())
    {
        iterator.next();
        total += iterator.fileInfo().size();
    }
    return total;
}

QString formatBytes(qint64 bytes)
{
    if (bytes <= 0)
    {
        return {};
    }
    const double mb = static_cast<double>(bytes) / 1048576.0;
    if (mb >= 1.0)
    {
        return QString(" · %1 MB").arg(mb, 0, 'f', 1);
    }
    return QString(" · %1 B").arg(bytes);
}
}
