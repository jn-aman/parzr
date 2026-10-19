import Foundation

/// What the app and keyboard both use for a check.
public struct KeyboardSettings: Codable, Equatable, Sendable {
    public var dialect: String = "american"
    public var dictionary: [String] = []
    public var names: [String] = []
    /// Try Apple Intelligence inside the keyboard before handing a rewrite to the app.
    public var rewriteInKeyboard: Bool = true
    public init() {}
}

/// A rewrite the keyboard hands to the app (App Group handoff): the keyboard cannot always run
/// Apple Foundation Models or the full engine itself (see ios/README.md), so it leaves the
/// request here, the app writes the rewrite when it is next in the foreground, and the keyboard
/// offers it when the user comes back.
public struct Handoff: Codable, Equatable, Sendable, Identifiable {
    public let id: UUID
    public let source: String
    public let mode: RewriteMode
    public let created: Date
    public var result: String?
    /// Why there is no rewrite (Apple Intelligence off, the rewrite changed the meaning…).
    public var note: String?
    public var finished: Date?
    public init(id: UUID = UUID(), source: String, mode: RewriteMode, created: Date = Date()) {
        self.id = id; self.source = source; self.mode = mode; self.created = created
    }
}

/// The App Group container both processes read and write. A keyboard needs Full Access to
/// write it; without Full Access the keyboard only reads the settings.
public final class SharedStore: @unchecked Sendable {
    public static let appGroup = "group.app.parzr.ios"
    public static let shared = SharedStore()
    /// A handoff older than this is dropped: the user has moved on.
    public static let handoffLifetime: TimeInterval = 15 * 60

    let defaults: UserDefaults
    public init(defaults: UserDefaults? = UserDefaults(suiteName: SharedStore.appGroup)) {
        self.defaults = defaults ?? .standard
    }

    private func value<T: Decodable>(_ key: String, as: T.Type) -> T? {
        defaults.data(forKey: key).flatMap { try? JSONDecoder().decode(T.self, from: $0) }
    }
    private func store<T: Encodable>(_ value: T?, _ key: String) {
        if let value, let data = try? JSONEncoder().encode(value) { defaults.set(data, forKey: key) } else { defaults.removeObject(forKey: key) }
    }

    public var settings: KeyboardSettings {
        get { value("settings", as: KeyboardSettings.self) ?? KeyboardSettings() }
        set { store(newValue, "settings") }
    }

    // MARK: Handoff (one slot: the latest request wins)

    @discardableResult
    public func post(source: String, mode: RewriteMode, now: Date = Date()) -> Handoff {
        let handoff = Handoff(source: source, mode: mode, created: now)
        store(handoff, "handoff")
        return handoff
    }

    /// The request the app should answer, if any.
    public func pending(now: Date = Date()) -> Handoff? {
        guard let handoff = value("handoff", as: Handoff.self), handoff.finished == nil else { return nil }
        guard now.timeIntervalSince(handoff.created) < Self.handoffLifetime else { store(Optional<Handoff>.none, "handoff"); return nil }
        return handoff
    }

    public func finish(_ id: UUID, result: String?, note: String?, now: Date = Date()) {
        guard var handoff = value("handoff", as: Handoff.self), handoff.id == id else { return }
        handoff.result = result; handoff.note = note; handoff.finished = now
        store(handoff, "handoff")
    }

    /// The answered request, without removing it (the keyboard removes it once used or dismissed).
    public func finished(now: Date = Date()) -> Handoff? {
        guard let handoff = value("handoff", as: Handoff.self), handoff.finished != nil else { return nil }
        guard now.timeIntervalSince(handoff.created) < Self.handoffLifetime else { store(Optional<Handoff>.none, "handoff"); return nil }
        return handoff
    }

    public func clearHandoff() { store(Optional<Handoff>.none, "handoff") }

    // MARK: Keyboard report (what the keyboard found it can do, shown in the app's setup screen)

    public struct KeyboardReport: Codable, Equatable, Sendable {
        public var seen: Date
        public var fullAccess: Bool
        /// "engine" or "system spelling" (the engine did not fit the keyboard's memory).
        public var checker: String
        /// Remaining memory before the system ends the keyboard, in MB (nil where not reported).
        public var memoryHeadroomMB: Int?
        /// Apple Intelligence inside the keyboard: "available", "untested", or the failure.
        public var appleModel: String
        public init(seen: Date = Date(), fullAccess: Bool, checker: String, memoryHeadroomMB: Int?, appleModel: String) {
            self.seen = seen; self.fullAccess = fullAccess; self.checker = checker; self.memoryHeadroomMB = memoryHeadroomMB; self.appleModel = appleModel
        }
    }
    public var keyboardReport: KeyboardReport? {
        get { value("keyboardReport", as: KeyboardReport.self) }
        set { store(newValue, "keyboardReport") }
    }
}
