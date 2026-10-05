import AppKit
import Foundation
let destination = CommandLine.arguments[1]
let source = CommandLine.arguments.count > 2 ? CommandLine.arguments[2] : "resources/Brand/ParzrIcon.png"
guard let artwork = NSImage(contentsOfFile: source) else { fatalError("Missing Parzr icon artwork") }
try FileManager.default.createDirectory(atPath: destination, withIntermediateDirectories: true)
for size in [16, 32, 64, 128, 256, 512, 1024] {
    guard let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0), let context = NSGraphicsContext(bitmapImageRep: rep) else { exit(1) }
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = context
    context.imageInterpolation = .high
    artwork.draw(in: NSRect(x: 0, y: 0, width: size, height: size), from: .zero, operation: .copy, fraction: 1)
    NSGraphicsContext.restoreGraphicsState()
    guard let data = rep.representation(using: .png, properties: [:]) else { exit(1) }
    let name = size == 1024 ? "icon_512x512@2x.png" : "icon_\(size)x\(size).png"
    try data.write(to: URL(fileURLWithPath: destination).appendingPathComponent(name))
    if [32, 64, 256, 512].contains(size) { try data.write(to: URL(fileURLWithPath: destination).appendingPathComponent("icon_\(size/2)x\(size/2)@2x.png")) }
}
