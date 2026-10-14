import QtQuick

Canvas {
    id: root
    property string symbol: "folder"
    property color color: "gray"
    implicitWidth: 24
    implicitHeight: 24
    Accessible.ignored: true
    onSymbolChanged: requestPaint()
    onColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()

    onPaint: {
        let ctx = getContext("2d");
        ctx.reset();
        ctx.scale(width / 24, height / 24);
        ctx.strokeStyle = color;
        ctx.fillStyle = color;
        ctx.lineWidth = 1.7;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        function path(points, close) {
            ctx.beginPath();
            ctx.moveTo(points[0][0], points[0][1]);
            for (let i = 1; i < points.length; ++i) ctx.lineTo(points[i][0], points[i][1]);
            if (close) ctx.closePath();
            ctx.stroke();
        }
        function circle(x, y, radius) {
            ctx.beginPath();
            ctx.arc(x, y, radius, 0, Math.PI * 2);
            ctx.stroke();
        }
        if (symbol === "subscriptions") {
            ctx.beginPath();
            ctx.arc(12, 12, 2, 0, Math.PI * 2);
            ctx.fill();
            for (let radius of [6, 10]) {
                for (let angle of [0, Math.PI]) {
                    ctx.beginPath();
                    ctx.arc(12, 12, radius, angle - 0.8, angle + 0.8);
                    ctx.stroke();
                }
            }
        } else if (symbol === "today") {
            circle(12, 12, 4);
            for (let i = 0; i < 8; ++i) {
                let angle = i * Math.PI / 4;
                path([[12 + 7.5 * Math.cos(angle), 12 + 7.5 * Math.sin(angle)],
                      [12 + 10.5 * Math.cos(angle), 12 + 10.5 * Math.sin(angle)]], false);
            }
        } else if (symbol === "unprocessed") {
            path([[2, 10], [6, 4], [18, 4], [22, 10], [22, 20], [2, 20]], true);
            path([[2, 12], [8, 12], [10, 15], [14, 15], [16, 12], [22, 12]], false);
        } else if (symbol === "processed") {
            circle(12, 12, 9);
            path([[7, 12], [10.5, 15.5], [17, 8.5]], false);
        } else if (symbol === "starred") {
            ctx.beginPath();
            for (let i = 0; i < 10; ++i) {
                let angle = -Math.PI / 2 + i * Math.PI / 5;
                let radius = i % 2 === 0 ? 11 : 4.8;
                let x = 12 + Math.cos(angle) * radius;
                let y = 12 + Math.sin(angle) * radius;
                if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            }
            ctx.closePath();
            ctx.fill();
        } else if (symbol === "archive") {
            ctx.strokeRect(3, 3, 18, 4);
            path([[5, 7], [5, 21], [19, 21], [19, 7]], false);
            path([[10, 11], [14, 11]], false);
        } else if (symbol === "library") {
            ctx.strokeRect(2, 5, 5, 16);
            ctx.strokeRect(9, 3, 5, 18);
            path([[16, 6], [20, 5], [23, 20], [19, 21]], true);
            path([[4, 17], [5, 17]], false);
        } else {
            path([[2, 7], [2, 4], [9, 4], [12, 7], [22, 7], [22, 21], [2, 21]], true);
            path([[2, 9], [22, 9]], false);
        }
    }
}
