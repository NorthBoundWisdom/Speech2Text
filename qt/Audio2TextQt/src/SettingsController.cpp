#include "SettingsController.h"

#include "AppPaths.h"

#include <QtCore/QDir>
#include <QtCore/QFile>
#include <QtCore/QFileInfo>
#include <QtCore/QProcessEnvironment>
#include <QtCore/QRegularExpression>
#include <QtCore/QStandardPaths>

namespace
{
QString defaultSummaryPrompt()
{
    return QStringLiteral(
        "请只基于输入的中文播客转写稿生成结构化 Markdown 总结，不要补充外部事实。\n"
        "第一行必须是“# <具体中文总结标题>”，标题要基于本期内容生成；不要写成“播客结构化总结”、“中文播客摘要”、“Summary”或目录名如 work。\n"
        "请覆盖：主要内容、核心观点、关键要点、重要名词（较生僻的请给出解释）、结论、金句提炼。\n"
        "直接输出最终 Markdown，不要输出思考过程。");
}

QString defaultTitlePrompt()
{
    return QStringLiteral(
        "请只基于输入的中文播客摘要生成一个适合列表显示的中文短标题，不要补充外部事实。\n"
        "必须输出成“主要嘉宾：一句话观点”格式；如果没有明确单一嘉宾，才允许输出成“主题：一句话观点”格式。\n"
        "风格要像播客标题，而不是章节名、关键词列表或抽象名词堆砌。\n"
        "正例：罗永浩：情绪稳定很重要\n"
        "正例：郑植：创作要走现实路\n"
        "反例：情绪稳定与表达\n"
        "反例：郑植创作现实路\n"
        "反例：AI 时代的表达\n"
        "要求：\n"
        "1. 标题里必须有一个明确的人名或主题短语放在冒号前。\n"
        "2. 冒号后必须是一个完整观点、判断、态度或冲突，不要只写名词。\n"
        "3. 尽量点明本期最有记忆点的一句话观点，而不是泛泛概括。\n"
        "4. 控制在10到20个汉字。\n"
        "5. 使用中文冒号“：”。\n"
        "6. 不要使用书名号、引号、括号、序号、解释文字。\n"
        "直接只输出标题本身。");
}

QString tomlQuotedString(const QString &value)
{
    QString escaped;
    escaped.reserve(value.size() + 8);
    for (const QChar ch : value)
    {
        switch (ch.unicode())
        {
        case '\\':
            escaped += QStringLiteral("\\\\");
            break;
        case '"':
            escaped += QStringLiteral("\\\"");
            break;
        case '\n':
            escaped += QStringLiteral("\\n");
            break;
        case '\t':
            escaped += QStringLiteral("\\t");
            break;
        case '\r':
            break;
        default:
            escaped += ch;
            break;
        }
    }
    return QStringLiteral("\"") + escaped + QStringLiteral("\"");
}

QString parseTomlString(const QString &value)
{
    QString trimmed = value.trimmed();
    const int comment = trimmed.indexOf(QStringLiteral(" #"));
    if (comment >= 0)
    {
        trimmed = trimmed.left(comment).trimmed();
    }
    if (trimmed.size() < 2 || trimmed.front() != '"' || trimmed.back() != '"')
    {
        return trimmed;
    }

    QString output;
    bool escaping = false;
    const QString body = trimmed.mid(1, trimmed.size() - 2);
    for (const QChar ch : body)
    {
        if (escaping)
        {
            switch (ch.unicode())
            {
            case 'n':
                output += '\n';
                break;
            case 't':
                output += '\t';
                break;
            case '"':
                output += '"';
                break;
            case '\\':
                output += '\\';
                break;
            default:
                output += ch;
                break;
            }
            escaping = false;
            continue;
        }
        if (ch == '\\')
        {
            escaping = true;
        }
        else
        {
            output += ch;
        }
    }
    if (escaping)
    {
        output += '\\';
    }
    return output;
}

QString parseTomlArrayAsText(const QString &value)
{
    QString trimmed = value.trimmed();
    if (!trimmed.startsWith('[') || !trimmed.endsWith(']'))
    {
        return parseTomlString(trimmed);
    }
    trimmed = trimmed.mid(1, trimmed.size() - 2).trimmed();
    if (trimmed.isEmpty())
    {
        return {};
    }

    QStringList items;
    QString current;
    bool inString = false;
    bool escaping = false;
    for (const QChar ch : trimmed)
    {
        if (escaping)
        {
            current += '\\';
            current += ch;
            escaping = false;
            continue;
        }
        if (ch == '\\')
        {
            escaping = true;
            continue;
        }
        if (ch == '"')
        {
            inString = !inString;
            current += ch;
            continue;
        }
        if (ch == ',' && !inString)
        {
            const QString item = parseTomlString(current.trimmed()).trimmed();
            if (!item.isEmpty())
            {
                items << item;
            }
            current.clear();
            continue;
        }
        current += ch;
    }
    const QString last = parseTomlString(current.trimmed()).trimmed();
    if (!last.isEmpty())
    {
        items << last;
    }
    return items.join(QStringLiteral(", "));
}

QStringList modelOptionList(const QString &text)
{
    QStringList options;
    const QStringList parts = text.split(QRegularExpression(QStringLiteral("[,\\n]")), Qt::SkipEmptyParts);
    for (const QString &part : parts)
    {
        const QString trimmed = part.trimmed();
        if (!trimmed.isEmpty())
        {
            options << trimmed;
        }
    }
    if (options.isEmpty())
    {
        options << QStringLiteral("gpt-5.4-mini") << QStringLiteral("gpt-5.4")
                << QStringLiteral("gpt-5.5") << QStringLiteral("gpt-5.6-sol")
                << QStringLiteral("gpt-5.6-terra") << QStringLiteral("gpt-5.6-luna");
    }
    options.removeDuplicates();
    return options;
}

QString tomlStringArray(const QString &text)
{
    QStringList encoded;
    for (const QString &option : modelOptionList(text))
    {
        encoded << tomlQuotedString(option);
    }
    return QStringLiteral("[") + encoded.join(QStringLiteral(", ")) + QStringLiteral("]");
}

QString sectionPattern(const QString &section)
{
    return QStringLiteral("^\\s*\\[\\s*%1\\s*\\]\\s*(?:#.*)?$").arg(QRegularExpression::escape(section));
}

QString keyPattern(const QString &key)
{
    return QStringLiteral("^\\s*%1\\s*=").arg(QRegularExpression::escape(key));
}

void setTomlValue(QString &text, const QString &section, const QString &key, const QString &value)
{
    text.replace(QStringLiteral("\r\n"), QStringLiteral("\n"));
    text.replace('\r', '\n');
    QStringList lines = text.split('\n', Qt::KeepEmptyParts);
    if (!lines.isEmpty() && lines.last().isEmpty())
    {
        lines.removeLast();
    }

    const QRegularExpression sectionRe(sectionPattern(section));
    const QRegularExpression anySectionRe(QStringLiteral("^\\s*\\[[^\\]]+\\]\\s*(?:#.*)?$"));
    int sectionStart = -1;
    for (int index = 0; index < lines.size(); ++index)
    {
        if (sectionRe.match(lines.at(index)).hasMatch())
        {
            sectionStart = index;
            break;
        }
    }

    if (sectionStart < 0)
    {
        if (!lines.isEmpty() && !lines.last().trimmed().isEmpty())
        {
            lines << QString();
        }
        lines << QStringLiteral("[%1]").arg(section);
        lines << QStringLiteral("%1 = %2").arg(key, value);
        text = lines.join('\n') + '\n';
        return;
    }

    int sectionEnd = lines.size();
    for (int index = sectionStart + 1; index < lines.size(); ++index)
    {
        if (anySectionRe.match(lines.at(index)).hasMatch())
        {
            sectionEnd = index;
            break;
        }
    }

    const QRegularExpression keyRe(keyPattern(key));
    for (int index = sectionStart + 1; index < sectionEnd; ++index)
    {
        if (keyRe.match(lines.at(index)).hasMatch())
        {
            lines[index] = QStringLiteral("%1 = %2").arg(key, value);
            text = lines.join('\n') + '\n';
            return;
        }
    }

    lines.insert(sectionEnd, QStringLiteral("%1 = %2").arg(key, value));
    text = lines.join('\n') + '\n';
}

QString readTomlValue(const QString &text, const QString &section, const QString &key)
{
    QString activeSection;
    const QStringList lines = text.split(QRegularExpression(QStringLiteral("\\r?\\n")));
    const QRegularExpression sectionRe(QStringLiteral("^\\s*\\[\\s*([^\\]]+)\\s*\\]\\s*(?:#.*)?$"));
    const QRegularExpression keyRe(QStringLiteral("^\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*(.*)$"));
    for (const QString &line : lines)
    {
        const QString trimmed = line.trimmed();
        if (trimmed.isEmpty() || trimmed.startsWith('#'))
        {
            continue;
        }
        const QRegularExpressionMatch sectionMatch = sectionRe.match(line);
        if (sectionMatch.hasMatch())
        {
            activeSection = sectionMatch.captured(1).trimmed();
            continue;
        }
        if (activeSection != section)
        {
            continue;
        }
        const QRegularExpressionMatch keyMatch = keyRe.match(line);
        if (keyMatch.hasMatch() && keyMatch.captured(1) == key)
        {
            return keyMatch.captured(2).trimmed();
        }
    }
    return {};
}
}

SettingsController::SettingsController(QObject *parent)
    : QObject(parent),
      m_settings("Audio2Text", "Audio2TextQt")
{
    load();
}

QString SettingsController::dataRoot() const
{
    return m_dataRoot;
}

void SettingsController::setDataRoot(const QString &value)
{
    const QString normalized = AppPaths::cleanPath(value);
    if (m_dataRoot == normalized)
    {
        return;
    }
    m_dataRoot = normalized;
    loadCloudConfig();
    save();
    emit settingsChanged();
}

QString SettingsController::libraryRootOverride() const
{
    return m_libraryRootOverride;
}

void SettingsController::setLibraryRootOverride(const QString &value)
{
    updateValue(m_libraryRootOverride, AppPaths::cleanPath(value));
}

QString SettingsController::resolvedLibraryRoot() const
{
    return AppPaths::resolveLibraryRoot(m_dataRoot, m_libraryRootOverride);
}

QString SettingsController::atotPath() const
{
    return m_atotPath;
}

void SettingsController::setAtotPath(const QString &value)
{
    updateValue(m_atotPath, AppPaths::cleanPath(value));
}

QString SettingsController::vcpkgRoot() const
{
    return m_vcpkgRoot;
}

void SettingsController::setVcpkgRoot(const QString &value)
{
    updateValue(m_vcpkgRoot, AppPaths::cleanPath(value));
}

bool SettingsController::localOnly() const
{
    return m_localOnly;
}

void SettingsController::setLocalOnly(bool value)
{
    if (m_localOnly == value)
    {
        return;
    }
    m_localOnly = value;
    save();
    saveConfigFile();
    emit settingsChanged();
}

double SettingsController::cloudChunkMinutes() const
{
    return m_cloudChunkMinutes;
}

void SettingsController::setCloudChunkMinutes(double value)
{
    const double normalized = value > 0.0 ? value : 20.0;
    if (qFuzzyCompare(m_cloudChunkMinutes, normalized))
    {
        return;
    }
    m_cloudChunkMinutes = normalized;
    save();
    emit settingsChanged();
}

QString SettingsController::modelAlias() const
{
    return m_modelAlias;
}

void SettingsController::setModelAlias(const QString &value)
{
    const QString normalized = value.trimmed().isEmpty() ? "large-v3-turbo" : value.trimmed();
    if (m_modelAlias == normalized)
    {
        return;
    }
    m_modelAlias = normalized;
    save();
    saveConfigFile();
    emit settingsChanged();
}

QString SettingsController::configPath() const
{
    return QDir(AppPaths::cleanPath(m_dataRoot)).filePath("config.toml");
}

QString SettingsController::cloudApiBase() const
{
    return m_cloudApiBase;
}

void SettingsController::setCloudApiBase(const QString &value)
{
    const QString normalized = value.trimmed();
    if (m_cloudApiBase == normalized)
    {
        return;
    }
    m_cloudApiBase = normalized;
    saveConfigFile();
    emit settingsChanged();
}

QString SettingsController::cloudApiKey() const
{
    return m_cloudApiKey;
}

void SettingsController::setCloudApiKey(const QString &value)
{
    const QString normalized = value.trimmed();
    if (m_cloudApiKey == normalized)
    {
        return;
    }
    m_cloudApiKey = normalized;
    saveConfigFile();
    emit settingsChanged();
}

QString SettingsController::cloudModel() const
{
    return m_cloudModel;
}

void SettingsController::setCloudModel(const QString &value)
{
    const QString normalized = value.trimmed().isEmpty() ? QStringLiteral("gpt-5.4-mini") : value.trimmed();
    if (m_cloudModel == normalized)
    {
        return;
    }
    m_cloudModel = normalized;
    saveConfigFile();
    emit settingsChanged();
}

QString SettingsController::cloudTimeout() const
{
    return m_cloudTimeout;
}

void SettingsController::setCloudTimeout(const QString &value)
{
    const QString normalized = value.trimmed().isEmpty() ? QStringLiteral("360") : value.trimmed();
    if (m_cloudTimeout == normalized)
    {
        return;
    }
    m_cloudTimeout = normalized;
    saveConfigFile();
    emit settingsChanged();
}

QString SettingsController::cloudTemperature() const
{
    return m_cloudTemperature;
}

void SettingsController::setCloudTemperature(const QString &value)
{
    const QString normalized = value.trimmed().isEmpty() ? QStringLiteral("1") : value.trimmed();
    if (m_cloudTemperature == normalized)
    {
        return;
    }
    m_cloudTemperature = normalized;
    saveConfigFile();
    emit settingsChanged();
}

QString SettingsController::cloudMaxTokens() const
{
    return m_cloudMaxTokens;
}

void SettingsController::setCloudMaxTokens(const QString &value)
{
    const QString normalized = value.trimmed().isEmpty() ? QStringLiteral("8192") : value.trimmed();
    if (m_cloudMaxTokens == normalized)
    {
        return;
    }
    m_cloudMaxTokens = normalized;
    saveConfigFile();
    emit settingsChanged();
}

QString SettingsController::cloudModelOptions() const
{
    return m_cloudModelOptions;
}

void SettingsController::setCloudModelOptions(const QString &value)
{
    const QString normalized = modelOptionList(value).join(QStringLiteral(", "));
    if (m_cloudModelOptions == normalized)
    {
        return;
    }
    m_cloudModelOptions = normalized;
    saveConfigFile();
    emit settingsChanged();
}

QString SettingsController::summaryPrompt() const
{
    return m_summaryPrompt;
}

void SettingsController::setSummaryPrompt(const QString &value)
{
    const QString normalized = value.trimmed().isEmpty() ? defaultSummaryPrompt() : value.trimmed();
    if (m_summaryPrompt == normalized)
    {
        return;
    }
    m_summaryPrompt = normalized;
    saveConfigFile();
    emit settingsChanged();
}

QString SettingsController::titlePrompt() const
{
    return m_titlePrompt;
}

void SettingsController::setTitlePrompt(const QString &value)
{
    const QString normalized = value.trimmed().isEmpty() ? defaultTitlePrompt() : value.trimmed();
    if (m_titlePrompt == normalized)
    {
        return;
    }
    m_titlePrompt = normalized;
    saveConfigFile();
    emit settingsChanged();
}

bool SettingsController::cloudConfigured() const
{
    return !m_cloudApiBase.trimmed().isEmpty() && !m_cloudApiKey.trimmed().isEmpty();
}

void SettingsController::setDataRootUrl(const QUrl &url)
{
    setDataRoot(url.toLocalFile());
}

void SettingsController::setLibraryRootUrl(const QUrl &url)
{
    setLibraryRootOverride(url.toLocalFile());
}

void SettingsController::setAtotPathUrl(const QUrl &url)
{
    setAtotPath(url.toLocalFile());
}

void SettingsController::resetDefaults()
{
    m_dataRoot = AppPaths::defaultDataRoot();
    m_libraryRootOverride.clear();
    m_atotPath.clear();
    m_vcpkgRoot = QProcessEnvironment::systemEnvironment().value("VCPKG_ROOT");
    m_localOnly = true;
    m_cloudChunkMinutes = 20.0;
    m_modelAlias = "large-v3-turbo";
    m_cloudApiBase.clear();
    m_cloudApiKey.clear();
    m_cloudModel = "gpt-5.4-mini";
    m_cloudTimeout = "360";
    m_cloudTemperature = "1";
    m_cloudMaxTokens = "8192";
    m_cloudModelOptions = "gpt-5.4-mini, gpt-5.4, gpt-5.5, gpt-5.6-sol, gpt-5.6-terra, gpt-5.6-luna";
    m_summaryPrompt = defaultSummaryPrompt();
    m_titlePrompt = defaultTitlePrompt();
    save();
    saveConfigFile();
    emit settingsChanged();
}

void SettingsController::reloadCloudConfig()
{
    loadCloudConfig();
    emit settingsChanged();
}

bool SettingsController::saveCloudConfig()
{
    const bool ok = saveConfigFile();
    emit settingsChanged();
    return ok;
}

QVariantMap SettingsController::detectTools() const
{
    const QStringList extraDirectories = extraToolDirectories();
    const QString atot = resolvedAtotExecutable();
    const QString ffmpeg = AppPaths::findExecutable("ffmpeg", extraDirectories);
    const QString ffprobe = AppPaths::findExecutable("ffprobe", extraDirectories);
    QVariantMap payload;
    payload["dataRoot"] = m_dataRoot;
    payload["libraryRoot"] = resolvedLibraryRoot();
    payload["modelRoot"] = AppPaths::modelRoot(m_dataRoot);
    payload["atot"] = atot;
    payload["ffmpeg"] = ffmpeg;
    payload["ffprobe"] = ffprobe;
    payload["atotReady"] = !atot.isEmpty();
    payload["ffmpegReady"] = !ffmpeg.isEmpty();
    payload["ffprobeReady"] = !ffprobe.isEmpty();
    payload["vcpkgRoot"] = m_vcpkgRoot;
    payload["configPath"] = configPath();
    payload["cloudConfigured"] = cloudConfigured();
    return payload;
}

QString SettingsController::resolvedAtotExecutable() const
{
    if (!m_atotPath.isEmpty() && QFileInfo(m_atotPath).isExecutable())
    {
        return m_atotPath;
    }
    const QString local = AppPaths::defaultAtotPath(m_dataRoot);
    if (!local.isEmpty())
    {
        return local;
    }

    const QStringList extraDirectories = extraToolDirectories();
    const QString bundledAtot = QStandardPaths::findExecutable("atot", extraDirectories);
    if (!bundledAtot.isEmpty())
    {
        return QDir::toNativeSeparators(bundledAtot);
    }
    const QString bundledAppCli = QStandardPaths::findExecutable("Audio2TextCli", extraDirectories);
    if (!bundledAppCli.isEmpty())
    {
        return QDir::toNativeSeparators(bundledAppCli);
    }
    const QString bundledPython = QDir(AppPaths::applicationDir()).filePath("python/python.exe");
    if (QFileInfo(bundledPython).isExecutable())
    {
        return QDir::toNativeSeparators(bundledPython);
    }

    const QString found = AppPaths::findExecutable("atot");
    if (!found.isEmpty())
    {
        return found;
    }
    return AppPaths::findExecutable("Audio2TextCli");
}

QStringList SettingsController::atotArgumentPrefix() const
{
    const QString bundledPython = QDir::toNativeSeparators(QDir(AppPaths::applicationDir()).filePath("python/python.exe"));
    if (!bundledPython.isEmpty() && resolvedAtotExecutable().compare(bundledPython, Qt::CaseInsensitive) == 0)
    {
        return {"-m", "atot.cli"};
    }
    return {};
}

QProcessEnvironment SettingsController::processEnvironment() const
{
    QProcessEnvironment environment = QProcessEnvironment::systemEnvironment();
    environment.insert("ATOT_DATA_ROOT", m_dataRoot);
    environment.insert("PYTHONUTF8", "1");
    if (!m_vcpkgRoot.isEmpty())
    {
        environment.insert("VCPKG_ROOT", m_vcpkgRoot);
    }

    QStringList pathEntries = extraToolDirectories();
    const QString currentPath = environment.value("PATH");
    if (!currentPath.isEmpty())
    {
        pathEntries << currentPath.split(QDir::listSeparator(), Qt::SkipEmptyParts);
    }
    environment.insert("PATH", pathEntries.join(QDir::listSeparator()));
    return environment;
}

QStringList SettingsController::extraToolDirectories() const
{
    QStringList directories = AppPaths::vcpkgToolDirectories(m_vcpkgRoot);
    const QString appDir = AppPaths::applicationDir();
    const QString bundledScripts = QDir(appDir).filePath("env/Scripts");
    const QString bundledBin = QDir(appDir).filePath("env/bin");
    const QString bundledPython = QDir(appDir).filePath("python");
    const QString bundledPythonScripts = QDir(appDir).filePath("python/Scripts");
    const QString scripts = QDir(m_dataRoot).filePath("env/Scripts");
    const QString bin = QDir(m_dataRoot).filePath("env/bin");
    if (QFileInfo(scripts).isDir())
    {
        directories.prepend(QDir::toNativeSeparators(scripts));
    }
    if (QFileInfo(bin).isDir())
    {
        directories.prepend(QDir::toNativeSeparators(bin));
    }
    if (QFileInfo(bundledScripts).isDir())
    {
        directories.prepend(QDir::toNativeSeparators(bundledScripts));
    }
    if (QFileInfo(bundledBin).isDir())
    {
        directories.prepend(QDir::toNativeSeparators(bundledBin));
    }
    if (QFileInfo(bundledPythonScripts).isDir())
    {
        directories.prepend(QDir::toNativeSeparators(bundledPythonScripts));
    }
    if (QFileInfo(bundledPython).isDir())
    {
        directories.prepend(QDir::toNativeSeparators(bundledPython));
    }
    if (QFileInfo(appDir).isDir())
    {
        directories.prepend(appDir);
    }
    directories.removeDuplicates();
    return directories;
}

void SettingsController::load()
{
    m_dataRoot = AppPaths::cleanPath(m_settings.value("dataRoot", AppPaths::defaultDataRoot()).toString());
    m_libraryRootOverride = AppPaths::cleanPath(m_settings.value("libraryRootOverride").toString());
    m_atotPath = AppPaths::cleanPath(m_settings.value("atotPath").toString());
    m_vcpkgRoot = AppPaths::cleanPath(m_settings.value("vcpkgRoot", QProcessEnvironment::systemEnvironment().value("VCPKG_ROOT")).toString());
    m_localOnly = m_settings.value("localOnly", true).toBool();
    m_cloudChunkMinutes = m_settings.value("cloudChunkMinutes", 20.0).toDouble();
    m_modelAlias = m_settings.value("modelAlias", "large-v3-turbo").toString();
    m_summaryPrompt = defaultSummaryPrompt();
    m_titlePrompt = defaultTitlePrompt();
    loadCloudConfig();
}

void SettingsController::save()
{
    m_settings.setValue("dataRoot", m_dataRoot);
    m_settings.setValue("libraryRootOverride", m_libraryRootOverride);
    m_settings.setValue("atotPath", m_atotPath);
    m_settings.setValue("vcpkgRoot", m_vcpkgRoot);
    m_settings.setValue("localOnly", m_localOnly);
    m_settings.setValue("cloudChunkMinutes", m_cloudChunkMinutes);
    m_settings.setValue("modelAlias", m_modelAlias);
}

void SettingsController::updateValue(QString &field, const QString &value)
{
    if (field == value)
    {
        return;
    }
    field = value;
    save();
    emit settingsChanged();
}

void SettingsController::loadCloudConfig()
{
    m_cloudApiBase.clear();
    m_cloudApiKey.clear();
    m_cloudModel = "gpt-5.4-mini";
    m_cloudTimeout = "360";
    m_cloudTemperature = "1";
    m_cloudMaxTokens = "8192";
    m_cloudModelOptions = "gpt-5.4-mini, gpt-5.4, gpt-5.5, gpt-5.6-sol, gpt-5.6-terra, gpt-5.6-luna";
    if (m_summaryPrompt.trimmed().isEmpty())
    {
        m_summaryPrompt = defaultSummaryPrompt();
    }
    if (m_titlePrompt.trimmed().isEmpty())
    {
        m_titlePrompt = defaultTitlePrompt();
    }

    QFile file(configPath());
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text))
    {
        return;
    }
    const QString text = QString::fromUtf8(file.readAll());

    const QString localModel = parseTomlString(readTomlValue(text, "local", "asr_model")).trimmed();
    if (!localModel.isEmpty())
    {
        m_modelAlias = localModel;
    }

    const QString workflowLocalOnly = readTomlValue(text, "workflow", "local_only").trimmed().toLower();
    if (workflowLocalOnly == "true")
    {
        m_localOnly = true;
    }
    else if (workflowLocalOnly == "false")
    {
        m_localOnly = false;
    }

    const QString apiBase = parseTomlString(readTomlValue(text, "cloud", "api_base")).trimmed();
    const QString apiKey = parseTomlString(readTomlValue(text, "cloud", "api_key")).trimmed();
    const QString model = parseTomlString(readTomlValue(text, "cloud", "model")).trimmed();
    const QString timeout = parseTomlString(readTomlValue(text, "cloud", "timeout")).trimmed();
    const QString temperature = parseTomlString(readTomlValue(text, "cloud", "temperature")).trimmed();
    const QString maxTokens = parseTomlString(readTomlValue(text, "cloud", "max_tokens")).trimmed();
    const QString modelOptions = parseTomlArrayAsText(readTomlValue(text, "cloud", "model_options")).trimmed();
    const QString summary = parseTomlString(readTomlValue(text, "cloud", "summary_prompt")).trimmed();
    const QString title = parseTomlString(readTomlValue(text, "cloud", "title_prompt")).trimmed();

    m_cloudApiBase = apiBase;
    m_cloudApiKey = apiKey;
    if (!model.isEmpty())
    {
        m_cloudModel = model;
    }
    if (!timeout.isEmpty())
    {
        m_cloudTimeout = timeout;
    }
    if (!temperature.isEmpty())
    {
        m_cloudTemperature = temperature;
    }
    if (!maxTokens.isEmpty())
    {
        m_cloudMaxTokens = maxTokens;
    }
    if (!modelOptions.isEmpty())
    {
        m_cloudModelOptions = modelOptions;
    }
    if (!summary.isEmpty())
    {
        m_summaryPrompt = summary;
    }
    if (!title.isEmpty())
    {
        m_titlePrompt = title;
    }
}

bool SettingsController::saveConfigFile() const
{
    const QString path = configPath();
    QFileInfo info(path);
    if (!QDir().mkpath(info.absolutePath()))
    {
        return false;
    }

    QString text;
    QFile input(path);
    if (input.open(QIODevice::ReadOnly | QIODevice::Text))
    {
        text = QString::fromUtf8(input.readAll());
    }

    setTomlValue(text, "local", "asr_model", tomlQuotedString(m_modelAlias.trimmed().isEmpty() ? QStringLiteral("large-v3-turbo") : m_modelAlias.trimmed()));
    setTomlValue(text, "cloud", "api_base", tomlQuotedString(m_cloudApiBase.trimmed()));
    setTomlValue(text, "cloud", "api_key", tomlQuotedString(m_cloudApiKey.trimmed()));
    setTomlValue(text, "cloud", "model", tomlQuotedString(m_cloudModel.trimmed().isEmpty() ? QStringLiteral("gpt-5.4-mini") : m_cloudModel.trimmed()));
    setTomlValue(text, "cloud", "timeout", tomlQuotedString(m_cloudTimeout.trimmed().isEmpty() ? QStringLiteral("360") : m_cloudTimeout.trimmed()));
    setTomlValue(text, "cloud", "temperature", tomlQuotedString(m_cloudTemperature.trimmed().isEmpty() ? QStringLiteral("1") : m_cloudTemperature.trimmed()));
    setTomlValue(text, "cloud", "max_tokens", tomlQuotedString(m_cloudMaxTokens.trimmed().isEmpty() ? QStringLiteral("8192") : m_cloudMaxTokens.trimmed()));
    setTomlValue(text, "cloud", "model_options", tomlStringArray(m_cloudModelOptions));
    setTomlValue(text, "cloud", "summary_prompt", tomlQuotedString(m_summaryPrompt.trimmed().isEmpty() ? defaultSummaryPrompt() : m_summaryPrompt.trimmed()));
    setTomlValue(text, "cloud", "title_prompt", tomlQuotedString(m_titlePrompt.trimmed().isEmpty() ? defaultTitlePrompt() : m_titlePrompt.trimmed()));
    setTomlValue(text, "workflow", "local_only", m_localOnly ? QStringLiteral("true") : QStringLiteral("false"));

    QFile output(path);
    if (!output.open(QIODevice::WriteOnly | QIODevice::Truncate | QIODevice::Text))
    {
        return false;
    }
    output.write(text.toUtf8());
    return true;
}
