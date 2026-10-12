import AppKit
import SwiftUI

enum AppIconFactory {
    static func image(size: CGFloat = 512) -> NSImage {
        let image = NSImage(size: NSSize(width: size, height: size))
        image.lockFocus()
        let rect = NSRect(x: 0, y: 0, width: size, height: size)

        let background = NSGradient(colors: [
            NSColor(calibratedRed: 0.10, green: 0.12, blue: 0.15, alpha: 1.0),
            NSColor(calibratedRed: 0.05, green: 0.22, blue: 0.28, alpha: 1.0),
        ])
        let path = NSBezierPath(roundedRect: rect.insetBy(dx: size * 0.055, dy: size * 0.055), xRadius: size * 0.20, yRadius: size * 0.20)
        path.addClip()
        background?.draw(in: rect, angle: 135)

        let waveform = NSBezierPath()
        let midY = size * 0.50
        let left = size * 0.19
        let step = size * 0.085
        let heights: [CGFloat] = [0.20, 0.36, 0.26, 0.48, 0.30, 0.40, 0.22]
        for (index, height) in heights.enumerated() {
            let x = left + CGFloat(index) * step
            waveform.move(to: NSPoint(x: x, y: midY - size * height / 2))
            waveform.line(to: NSPoint(x: x, y: midY + size * height / 2))
        }
        NSColor(calibratedRed: 0.42, green: 0.92, blue: 0.78, alpha: 1.0).setStroke()
        waveform.lineWidth = size * 0.035
        waveform.lineCapStyle = .round
        waveform.stroke()

        let text = "A"
        let attributes: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: size * 0.25, weight: .bold),
            .foregroundColor: NSColor.white,
        ]
        let attributed = NSAttributedString(string: text, attributes: attributes)
        let textSize = attributed.size()
        attributed.draw(at: NSPoint(x: size * 0.50 - textSize.width / 2, y: size * 0.13))

        image.unlockFocus()
        return image
    }
}

struct AppIconView: View {
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 12)
                .fill(LinearGradient(colors: [Color(red: 0.10, green: 0.12, blue: 0.15), Color(red: 0.05, green: 0.22, blue: 0.28)], startPoint: .topLeading, endPoint: .bottomTrailing))
            HStack(spacing: 4) {
                ForEach([0.34, 0.58, 0.42, 0.72, 0.46], id: \.self) { height in
                    Capsule()
                        .fill(Color(red: 0.42, green: 0.92, blue: 0.78))
                        .frame(width: 4, height: 34 * height)
                }
            }
            Text("A")
                .font(.system(size: 17, weight: .bold))
                .foregroundStyle(.white)
                .offset(y: 13)
        }
        .frame(width: 44, height: 44)
    }
}
