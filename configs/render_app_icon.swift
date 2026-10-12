import AppKit
import Foundation
import ImageIO

let arguments = CommandLine.arguments
guard arguments.count == 2 || arguments.count == 3 else {
    fputs("usage: swift configs/render_app_icon.swift <iconset-dir> [ios-appiconset-dir]\n", stderr)
    exit(2)
}

let iconset = URL(fileURLWithPath: arguments[1], isDirectory: true)
try FileManager.default.createDirectory(at: iconset, withIntermediateDirectories: true)

func drawAppIcon(size: CGFloat, roundedMask: Bool) {
    let rect = NSRect(x: 0, y: 0, width: size, height: size)

    let background = NSGradient(colors: [
        NSColor(calibratedRed: 0.10, green: 0.12, blue: 0.15, alpha: 1.0),
        NSColor(calibratedRed: 0.05, green: 0.22, blue: 0.28, alpha: 1.0)
    ])
    if roundedMask {
        let path = NSBezierPath(
            roundedRect: rect.insetBy(dx: size * 0.055, dy: size * 0.055),
            xRadius: size * 0.20,
            yRadius: size * 0.20
        )
        path.addClip()
        background?.draw(in: rect, angle: 135)
    } else {
        background?.draw(in: rect, angle: 135)
    }

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

    let attributes: [NSAttributedString.Key: Any] = [
        .font: NSFont.systemFont(ofSize: size * 0.25, weight: .bold),
        .foregroundColor: NSColor.white
    ]
    let attributed = NSAttributedString(string: "A", attributes: attributes)
    let textSize = attributed.size()
    attributed.draw(at: NSPoint(x: size * 0.50 - textSize.width / 2, y: size * 0.13))
}

func makeCGImage(size: Int, roundedMask: Bool, hasAlpha: Bool) throws -> CGImage {
    let colorSpace = CGColorSpaceCreateDeviceRGB()
    let alphaInfo: CGImageAlphaInfo = hasAlpha ? .premultipliedLast : .noneSkipLast
    guard let context = CGContext(
        data: nil,
        width: size,
        height: size,
        bitsPerComponent: 8,
        bytesPerRow: 0,
        space: colorSpace,
        bitmapInfo: alphaInfo.rawValue
    ) else {
        throw NSError(domain: "Audio2TextIcon", code: 1)
    }

    let graphicsContext = NSGraphicsContext(cgContext: context, flipped: false)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = graphicsContext
    graphicsContext.imageInterpolation = .high
    drawAppIcon(size: CGFloat(size), roundedMask: roundedMask)
    NSGraphicsContext.restoreGraphicsState()

    guard let image = context.makeImage() else {
        throw NSError(domain: "Audio2TextIcon", code: 2)
    }
    return image
}

func writePNG(size: Int, roundedMask: Bool, to url: URL, hasAlpha: Bool) throws {
    let image = try makeCGImage(size: size, roundedMask: roundedMask, hasAlpha: hasAlpha)
    guard let destination = CGImageDestinationCreateWithURL(url as CFURL, "public.png" as CFString, 1, nil) else {
        throw NSError(domain: "Audio2TextIcon", code: 3)
    }
    CGImageDestinationAddImage(destination, image, nil)
    if !CGImageDestinationFinalize(destination) {
        throw NSError(domain: "Audio2TextIcon", code: 4)
    }
}

func writeMacIconset(to iconset: URL) throws {
    for points in [16, 32, 128, 256, 512] {
        for scale in [1, 2] {
            let size = points * scale
            let suffix = scale == 2 ? "@2x" : ""
            let url = iconset.appendingPathComponent("icon_\(points)x\(points)\(suffix).png")
            try writePNG(size: size, roundedMask: true, to: url, hasAlpha: true)
        }
    }
}

struct IOSIconSpec {
    let idiom: String
    let size: String
    let scale: String
    let filename: String

    var pixelSize: Int {
        let multiplier = Int(scale.replacingOccurrences(of: "x", with: "")) ?? 1
        let points = Double(size.split(separator: "x").first ?? "0") ?? 0
        return Int((points * Double(multiplier)).rounded())
    }
}

let iosIconSpecs = [
    IOSIconSpec(idiom: "iphone", size: "20x20", scale: "2x", filename: "iphone_20x20@2x.png"),
    IOSIconSpec(idiom: "iphone", size: "20x20", scale: "3x", filename: "iphone_20x20@3x.png"),
    IOSIconSpec(idiom: "iphone", size: "29x29", scale: "2x", filename: "iphone_29x29@2x.png"),
    IOSIconSpec(idiom: "iphone", size: "29x29", scale: "3x", filename: "iphone_29x29@3x.png"),
    IOSIconSpec(idiom: "iphone", size: "40x40", scale: "2x", filename: "iphone_40x40@2x.png"),
    IOSIconSpec(idiom: "iphone", size: "40x40", scale: "3x", filename: "iphone_40x40@3x.png"),
    IOSIconSpec(idiom: "iphone", size: "60x60", scale: "2x", filename: "iphone_60x60@2x.png"),
    IOSIconSpec(idiom: "iphone", size: "60x60", scale: "3x", filename: "iphone_60x60@3x.png"),
    IOSIconSpec(idiom: "ipad", size: "20x20", scale: "1x", filename: "ipad_20x20.png"),
    IOSIconSpec(idiom: "ipad", size: "20x20", scale: "2x", filename: "ipad_20x20@2x.png"),
    IOSIconSpec(idiom: "ipad", size: "29x29", scale: "1x", filename: "ipad_29x29.png"),
    IOSIconSpec(idiom: "ipad", size: "29x29", scale: "2x", filename: "ipad_29x29@2x.png"),
    IOSIconSpec(idiom: "ipad", size: "40x40", scale: "1x", filename: "ipad_40x40.png"),
    IOSIconSpec(idiom: "ipad", size: "40x40", scale: "2x", filename: "ipad_40x40@2x.png"),
    IOSIconSpec(idiom: "ipad", size: "76x76", scale: "2x", filename: "ipad_76x76@2x.png"),
    IOSIconSpec(idiom: "ipad", size: "83.5x83.5", scale: "2x", filename: "ipad_83_5x83_5@2x.png"),
    IOSIconSpec(idiom: "ios-marketing", size: "1024x1024", scale: "1x", filename: "ios_marketing_1024x1024.png")
]

func writeIOSAppIconset(to appiconset: URL) throws {
    try FileManager.default.createDirectory(at: appiconset, withIntermediateDirectories: true)
    for spec in iosIconSpecs {
        try writePNG(
            size: spec.pixelSize,
            roundedMask: false,
            to: appiconset.appendingPathComponent(spec.filename),
            hasAlpha: false
        )
    }
}

try writeMacIconset(to: iconset)
if arguments.count == 3 {
    let appiconset = URL(fileURLWithPath: arguments[2], isDirectory: true)
    try writeIOSAppIconset(to: appiconset)
}
