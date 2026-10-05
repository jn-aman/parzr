import AppKit
import Carbon

@MainActor
final class GlobalHotkey {
    private var reference: EventHotKeyRef?
    private var handler: EventHandlerRef?
    var action: (() -> Void)?
    private static var current: GlobalHotkey?
    init() {
        Self.current = self
        var spec = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        InstallEventHandler(GetApplicationEventTarget(), { _, _, _ in
            MainActor.assumeIsolated { GlobalHotkey.current?.action?() }
            return noErr
        }, 1, &spec, nil, &handler)
    }
    func register(key: Int, modifiers: Int) -> Bool {
        unregister()
        let id = EventHotKeyID(signature: 0x70727A72, id: 1)
        return RegisterEventHotKey(UInt32(key), UInt32(modifiers), id, GetApplicationEventTarget(), 0, &reference) == noErr
    }
    func unregister() { if let reference { UnregisterEventHotKey(reference) }; reference = nil }
}
