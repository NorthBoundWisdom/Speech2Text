#pragma once

#include <QtCore/QObject>
#include <QtGui/QColor>

class ThemeController : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QColor window READ window CONSTANT)
    Q_PROPERTY(QColor panel READ panel CONSTANT)
    Q_PROPERTY(QColor panelAlt READ panelAlt CONSTANT)
    Q_PROPERTY(QColor border READ border CONSTANT)
    Q_PROPERTY(QColor text READ text CONSTANT)
    Q_PROPERTY(QColor muted READ muted CONSTANT)
    Q_PROPERTY(QColor accent READ accent CONSTANT)
    Q_PROPERTY(QColor success READ success CONSTANT)
    Q_PROPERTY(QColor warning READ warning CONSTANT)
    Q_PROPERTY(QColor danger READ danger CONSTANT)

public:
    explicit ThemeController(QObject *parent = nullptr);

    QColor window() const;
    QColor panel() const;
    QColor panelAlt() const;
    QColor border() const;
    QColor text() const;
    QColor muted() const;
    QColor accent() const;
    QColor success() const;
    QColor warning() const;
    QColor danger() const;
};

