import AppKit
import Carbon

/// While any app holds secure event input (a password field, or a terminal's Secure Keyboard Entry), macOS hides typing from every other app, and
/// Parzr does not check: before, it simply went quiet everywhere, and Option+Space blamed a secure field even in a plain one. Parzr now
/// says so, naming the app that holds it when it can (see `Compat.secureInputHolder`), and says nothing when the writer is in a secure field.
@MainActor
enum SecureInput {
    /// The pid the window server records for secure input: the holder when it is frontmost, otherwise the frontmost app.
    static func ownerPID() -> pid_t? {
        guard let session = CGSessionCopyCurrentDictionary() as? [String: Any], let pid = session["kCGSSessionSecureInputPID"] as? Int, pid > 0 else { return nil }
        return pid_t(pid)
    }
    static func name(of pid: pid_t) -> String? {
        if let app = NSRunningApplication(processIdentifier: pid), let name = app.localizedName { return name }
        var buffer = [CChar](repeating: 0, count: 256)
        return proc_name(pid, &buffer, UInt32(buffer.count)) > 0 ? String(cString: buffer) : nil
    }
    /// What to say when secure input blocks checking while the writer is in `app`; nil when it is off or the writer's own secure field explains it.
    static func holder(watching app: NSRunningApplication?) -> Compat.SecureInputHolder? {
        guard IsSecureEventInputEnabled() else { return nil }
        let owner = ownerPID(), focused = app.flatMap { AX.focused($0) }
        let ownerApp = owner.flatMap { NSRunningApplication(processIdentifier: $0) }
        return Compat.secureInputHolder(ownerPID: owner, ownerName: owner.flatMap(name), ownerIsTerminal: Compat.isTerminal(ownerApp?.bundleIdentifier),
                                        watchedPID: app?.processIdentifier, focusKnown: focused != nil, focusSecure: focused.map(AX.isSecure) ?? false)
    }
    /// The menu-bar line.
    static func pausedLine(_ holder: Compat.SecureInputHolder) -> String {
        switch holder {
        case .app(let name): return "Paused: Secure input is on in \(name)"
        case .elsewhere: return "Paused: Secure input is on in another app"
        }
    }
    /// Why an explicit check cannot read the text.
    static func message(_ holder: Compat.SecureInputHolder?) -> String {
        switch holder {
        case nil: return "Parzr does not read secure fields."
        case .app(let name): return "Secure input is on in \(name), so macOS hides typing from other apps. Turn it off there (in a terminal, Secure Keyboard Entry), then try again."
        case .elsewhere: return "Another app has secure input on, so macOS hides typing from other apps. Close any open password prompt, or quit the app that holds it, then try again."
        }
    }
}
