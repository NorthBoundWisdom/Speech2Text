import QtQuick
import QtQuick.Controls

ScrollView {
    id: root
    clip: true

    property string markdown: ""
    property int contentMaxWidth: 900
    property int bodySize: 15
    property string codeFontFamily: Qt.platform.os === "osx" ? "Menlo" : (Qt.platform.os === "windows" ? "Consolas" : "DejaVu Sans Mono")

    onMarkdownChanged: Qt.callLater(function() {
        if (root.contentItem)
            root.contentItem.contentY = 0
    })

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
    }

    function inlineMarkdown(value) {
        var text = escapeHtml(value)
        text = text.replace(/`([^`]+)`/g, "<span style=\"font-family: '" + codeFontFamily + "'; background-color: #eef2f6; color: #17202a;\">$1</span>")
        text = text.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
        text = text.replace(/\*([^*]+)\*/g, "<i>$1</i>")
        text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, "<a href=\"$2\" style=\"color: #1f6feb; text-decoration: none;\">$1</a>")
        return text
    }

    function closeList(state, parts) {
        if (state.list === "ul") {
            parts.push("</ul>")
        } else if (state.list === "ol") {
            parts.push("</ol>")
        }
        state.list = ""
    }

    function paragraphStyle() {
        return "margin-top: 0; margin-bottom: 12px; line-height: 1.58;"
    }

    function headingStyle(level) {
        if (level === 1)
            return "font-size: 26px; font-weight: 700; margin-top: 6px; margin-bottom: 18px; line-height: 1.25;"
        if (level === 2)
            return "font-size: 22px; font-weight: 700; margin-top: 26px; margin-bottom: 12px; line-height: 1.3;"
        if (level === 3)
            return "font-size: 18px; font-weight: 700; margin-top: 18px; margin-bottom: 8px; line-height: 1.35;"
        return "font-size: 16px; font-weight: 700; margin-top: 14px; margin-bottom: 6px; line-height: 1.4;"
    }

    function toHtml(markdownText) {
        var lines = String(markdownText || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n")
        var parts = []
        var state = { list: "", code: false, codeLines: [] }

        parts.push("<html><body style=\"margin: 0; color: #17202a; font-size: " + bodySize + "px;\">")

        for (var i = 0; i < lines.length; ++i) {
            var raw = lines[i]
            var line = raw.trim()

            if (line.indexOf("```") === 0) {
                if (state.code) {
                    parts.push("<pre style=\"margin-top: 8px; margin-bottom: 14px; padding: 12px; background-color: #f4f6f8; border: 1px solid #d6dce4; color: #17202a; font-family: '" + codeFontFamily + "'; font-size: 13px; white-space: pre-wrap;\">" + escapeHtml(state.codeLines.join("\n")) + "</pre>")
                    state.code = false
                    state.codeLines = []
                } else {
                    closeList(state, parts)
                    state.code = true
                    state.codeLines = []
                }
                continue
            }

            if (state.code) {
                state.codeLines.push(raw)
                continue
            }

            if (line.length === 0) {
                closeList(state, parts)
                continue
            }

            if (/^[-*_]{3,}$/.test(line)) {
                closeList(state, parts)
                parts.push("<hr style=\"border: 0; border-top: 1px solid #d6dce4; margin-top: 20px; margin-bottom: 20px;\" />")
                continue
            }

            var heading = line.match(/^(#{1,6})\s+(.+)$/)
            if (heading) {
                closeList(state, parts)
                var level = heading[1].length
                parts.push("<h" + level + " style=\"" + headingStyle(level) + "\">" + inlineMarkdown(heading[2]) + "</h" + level + ">")
                continue
            }

            var unordered = line.match(/^[-*+]\s+(.+)$/)
            if (unordered) {
                if (state.list !== "ul") {
                    closeList(state, parts)
                    parts.push("<ul style=\"margin-top: 4px; margin-bottom: 14px; padding-left: 24px; line-height: 1.55;\">")
                    state.list = "ul"
                }
                parts.push("<li style=\"margin-bottom: 6px;\">" + inlineMarkdown(unordered[1]) + "</li>")
                continue
            }

            var ordered = line.match(/^\d+[.)]\s+(.+)$/)
            if (ordered) {
                if (state.list !== "ol") {
                    closeList(state, parts)
                    parts.push("<ol style=\"margin-top: 4px; margin-bottom: 14px; padding-left: 26px; line-height: 1.55;\">")
                    state.list = "ol"
                }
                parts.push("<li style=\"margin-bottom: 6px;\">" + inlineMarkdown(ordered[1]) + "</li>")
                continue
            }

            if (line.indexOf(">") === 0) {
                closeList(state, parts)
                parts.push("<blockquote style=\"margin: 8px 0 14px 0; padding-left: 14px; border-left: 3px solid #b9d3ff; color: #4c5968; line-height: 1.58;\">" + inlineMarkdown(line.replace(/^>\s?/, "")) + "</blockquote>")
                continue
            }

            closeList(state, parts)
            parts.push("<p style=\"" + paragraphStyle() + "\">" + inlineMarkdown(line) + "</p>")
        }

        if (state.code) {
            parts.push("<pre style=\"margin-top: 8px; margin-bottom: 14px; padding: 12px; background-color: #f4f6f8; border: 1px solid #d6dce4; color: #17202a; font-family: '" + codeFontFamily + "'; font-size: 13px; white-space: pre-wrap;\">" + escapeHtml(state.codeLines.join("\n")) + "</pre>")
        }
        closeList(state, parts)
        parts.push("</body></html>")
        return parts.join("\n")
    }

    contentWidth: availableWidth

    TextEdit {
        id: reader
        readOnly: true
        selectByMouse: true
        textFormat: TextEdit.RichText
        wrapMode: TextEdit.Wrap
        text: root.toHtml(root.markdown)
        color: themeController.text
        width: Math.min(root.availableWidth - 48, root.contentMaxWidth)
        x: Math.max(24, (root.availableWidth - width) / 2)
        topPadding: 22
        bottomPadding: 28
        leftPadding: 0
        rightPadding: 0
        textMargin: 0
        font.family: Qt.application.font.family
        font.pixelSize: root.bodySize
    }
}
