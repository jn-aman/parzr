import SwiftUI
import ParzrKit

@main
struct ParzrApp: App {
    @State private var model = AppModel()
    @Environment(\.scenePhase) private var phase
    @AppStorage("onboarded") private var onboarded = false

    init() {
        if SelfTest.requested { Task { await SelfTest.run() } }
    }

    var body: some Scene {
        WindowGroup {
            TabView {
                Tab("Write", systemImage: "square.and.pencil") { ScratchpadView() }
                Tab("Keyboard", systemImage: "keyboard") { SetupView() }
                Tab("Settings", systemImage: "gearshape") { SettingsView() }
            }
            .environment(model)
            .sheet(isPresented: Binding(get: { !onboarded && !model.keyboardEnabled }, set: { if !$0 { onboarded = true } })) {
                SetupView(onDone: { onboarded = true })
                    .environment(model)
            }
            .onChange(of: phase, initial: true) { _, phase in
                if phase == .active { model.becameActive() }
            }
        }
    }
}
