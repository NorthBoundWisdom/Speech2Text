#include "ThemeController.h"

ThemeController::ThemeController(QObject *parent)
    : QObject(parent)
{
}

QColor ThemeController::window() const
{
    return QColor("#f5f6f8");
}

QColor ThemeController::panel() const
{
    return QColor("#ffffff");
}

QColor ThemeController::panelAlt() const
{
    return QColor("#eef2f6");
}

QColor ThemeController::border() const
{
    return QColor("#d6dce4");
}

QColor ThemeController::text() const
{
    return QColor("#17202a");
}

QColor ThemeController::muted() const
{
    return QColor("#657281");
}

QColor ThemeController::accent() const
{
    return QColor("#1f6feb");
}

QColor ThemeController::success() const
{
    return QColor("#168a4a");
}

QColor ThemeController::warning() const
{
    return QColor("#ad6b00");
}

QColor ThemeController::danger() const
{
    return QColor("#c73e3a");
}

