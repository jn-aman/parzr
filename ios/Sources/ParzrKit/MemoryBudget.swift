import Foundation
import os

/// Whether this process can afford the Rust engine. A keyboard extension is ended by the system
/// past its memory limit (about 60-70 MB on current iPhones), and the engine's tables peak at
/// about 110-140 MB (ios/README.md), so the keyboard asks first and falls back to the system
/// spell checker.
public enum MemoryBudget {
    /// Peak footprint the engine adds on its first check, with margin (measured 108-137 MB).
    public static let engineMB = 160

    /// Memory left before the system ends this process, in MB; nil where the system sets no
    /// limit (the simulator, and apps on macOS).
    public static var headroomMB: Int? {
        #if targetEnvironment(simulator)
        return nil
        #else
        let bytes = os_proc_available_memory()
        return bytes == 0 ? nil : Int(bytes / 1_048_576)
        #endif
    }

    /// True when the engine fits: always in the app, and in the keyboard only with headroom.
    public static func engineFits(headroomMB: Int? = MemoryBudget.headroomMB) -> Bool {
        guard let headroomMB else { return true }
        return headroomMB >= engineMB
    }
}
