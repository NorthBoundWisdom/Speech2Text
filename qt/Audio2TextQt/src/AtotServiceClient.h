#pragma once

#include <QtCore/QJsonObject>
#include <QtCore/QString>
#include <QtCore/QStringList>
#include <QtCore/QVariantMap>

class AtotServiceClient
{
public:
    static QString requestJson(const QString &method, const QVariantMap &params);
    static QStringList serviceArguments(const QString &method, const QVariantMap &params);
    static QString displayCommand(const QString &executable, const QStringList &arguments);
};

