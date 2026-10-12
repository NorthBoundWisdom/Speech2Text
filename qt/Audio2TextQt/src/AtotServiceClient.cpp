#include "AtotServiceClient.h"

#include <QtCore/QJsonDocument>
#include <QtCore/QJsonObject>

QString AtotServiceClient::requestJson(const QString &method, const QVariantMap &params)
{
    QJsonObject request;
    request["method"] = method;
    request["params"] = QJsonObject::fromVariantMap(params);
    return QString::fromUtf8(QJsonDocument(request).toJson(QJsonDocument::Compact));
}

QStringList AtotServiceClient::serviceArguments(const QString &method, const QVariantMap &params)
{
    return {
        "serve",
        "--stdio",
        "--request-json",
        requestJson(method, params),
        "--unwrap-result"
    };
}

QString AtotServiceClient::displayCommand(const QString &executable, const QStringList &arguments)
{
    QStringList parts;
    parts << executable;
    for (const QString &argument : arguments)
    {
        if (argument.contains(' ') || argument.contains('"'))
        {
            parts << '"' + QString(argument).replace('"', "\\\"") + '"';
        }
        else
        {
            parts << argument;
        }
    }
    return parts.join(' ');
}

