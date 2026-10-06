import SwiftUI
import AppKit
import ParzrCore
import Pow

enum StudioRoute: String, CaseIterable, Identifiable {
    case playground = "Editor", general = "General", writing = "Writing", appearance = "Appearance", apps = "Apps", privacy = "Privacy", compatibility = "Integrations", about = "About"
    var id: String { rawValue }
    var symbol: String {
        switch self {
        case .playground: "square.and.pencil"
        case .general: "slider.horizontal.3"
        case .writing: "textformat"
        case .appearance: "circle.lefthalf.filled"
        case .apps: "square.grid.2x2"
        case .privacy: "lock"
        case .compatibility: "link"
        case .about: "info.circle"
        }
    }
    var detail: String {
        switch self {
        case .playground: "Write naturally. Catch the details."
        case .general: "Ready when you need it. Quiet when you don’t."
        case .writing: "Your voice. Your words. Your preferences."
        case .appearance: "A writing space that feels like yours."
        case .apps: "Choose where Parzr lends a hand."
        case .privacy: "Local by design. In your control."
        case .compatibility: "Bring corrections closer to your writing."
        case .about: "Made for your words. Built to stay local."
        }
    }
}
struct StudioView: View {
    @Environment(\.accessibilityReduceMotion) private var systemReduceMotion
    @ObservedObject var model: AppModel
    @ObservedObject var preferences = Preferences.shared
    @ObservedObject var updates = UpdateModel.shared
    var route: StudioRoute?
    var renderingSnapshot: Bool
    @State private var draft: String
    @State private var dictionaryWord = ""
    @State private var nameWord = ""
    @State private var ignored: Set<String> = []
    @State private var appliedCount = 0
    @State private var reviewVisible = false
    @State private var statsVisible = false
    @State private var focusedWriting = false
    private var activeRoute: StudioRoute { route ?? model.studioRoute }
    private var animate: Bool { !systemReduceMotion && !preferences.reduceMotion && !renderingSnapshot }
    init(model: AppModel, route: StudioRoute? = nil, renderingSnapshot: Bool = false) {
        self.model = model; self.route = route; self.renderingSnapshot = renderingSnapshot
        _draft = State(initialValue: renderingSnapshot ? model.source : "")
    }
    var body: some View {
        HStack(spacing: 0) {
            if !focusedWriting || activeRoute != .playground {
                sidebar
                Rectangle().fill(Color.hairline.opacity(0.5)).frame(width: 1)
            }
            VStack(alignment: .leading, spacing: 0) {
                header
                if activeRoute == .playground { playground }
                else { ScrollView { settings.padding(.horizontal, 28).padding(.bottom, 28).padding(.top, 4) } }
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(minWidth: 760, minHeight: 540).background(Color.canvas).foregroundStyle(Color.textPrimary)
        .tint(Color.mintAccent)
        .onAppear { if !renderingSnapshot { preferences.refreshPermission(); if model.snapshot == nil { model.playground(draft, debounce: true) } } }
        .onChange(of: draft) { value in ignored = []; model.playground(value, debounce: true) }
        .onChange(of: model.result?.edits) { _ in model.selectedEdits.subtract(ignored) }
        .onChange(of: preferences.dialect) { _ in model.playground(draft, debounce: true) }
        .onChange(of: preferences.dictionary) { _ in model.playground(draft, debounce: true) }
        .onChange(of: preferences.learnedNames) { _ in model.playground(draft, debounce: true) }
        .onChange(of: preferences.nameCapitalization) { _ in model.playground(draft, debounce: true) }
    }
    private var sidebar: some View {
        VStack(alignment: .leading, spacing: 0) {
            Brand().padding(.horizontal, 22).padding(.top, 14).padding(.bottom, 22)
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    navigation(.playground)
                    Text("PREFERENCES").font(.system(size: 9, weight: .semibold)).tracking(1.4).foregroundStyle(Color.textSecondary.opacity(0.75)).padding(.leading, 24).padding(.top, 29).padding(.bottom, 10)
                    ForEach(StudioRoute.allCases.filter { $0 != .playground }) { navigation($0) }
                }
            }.scrollIndicators(.hidden)
            Spacer(minLength: 16)
            VStack(alignment: .leading, spacing: 8) {
                StatusLine(title: model.engineReady ? "On this Mac" : model.error == nil ? "Starting…" : "Engine unavailable", good: model.engineReady)
                Text("Your writing stays here.").font(.system(size: 10)).foregroundStyle(Color.textSecondary.opacity(0.7))
            }.padding(14).frame(maxWidth: .infinity, alignment: .leading).background(Color.canvas, in: RoundedRectangle(cornerRadius: 10)).padding(14)
        }.frame(width: 190).frame(maxHeight: .infinity).background(Color.sidebar)
    }
    private func navigation(_ item: StudioRoute) -> some View {
        Button {
            withAnimation(animate ? .easeOut(duration: 0.18) : nil) { model.studioRoute = item }
        } label: {
            HStack(spacing: 11) {
                Image(systemName: item.symbol).font(.system(size: 13, weight: .medium)).frame(width: 18)
                Text(item.rawValue).font(.system(size: 12, weight: activeRoute == item ? .semibold : .medium))
                Spacer(minLength: 0)
                if activeRoute == item { RoundedRectangle(cornerRadius: 1).fill(Color.mintAccent).frame(width: 3, height: 12) }
            }.foregroundStyle(activeRoute == item ? Color.mintAccent : Color.textSecondary)
                .padding(.horizontal, 12).frame(height: 36).contentShape(RoundedRectangle(cornerRadius: 8))
                .background(activeRoute == item ? Color.accentWash.opacity(0.6) : Color.clear, in: RoundedRectangle(cornerRadius: 8))
        }.buttonStyle(.plain).padding(.horizontal, 12).padding(.vertical, 2).accessibilityLabel(item.rawValue)
    }
    private var header: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack {
                Text(activeRoute == .playground ? "YOUR SPACE" : "MAKE IT YOURS").font(.system(size: 9, weight: .semibold)).tracking(1.8).foregroundStyle(Color.mintAccent)
                Spacer()
                if activeRoute == .playground {
                    NativeButton(title: "", kind: .utility, symbol: focusedWriting ? "sidebar.left" : "arrow.up.left.and.arrow.down.right", label: focusedWriting ? "Show sidebar" : "Focus writing space", action: { withAnimation(animate ? .easeOut(duration: 0.18) : nil) { focusedWriting.toggle() } }).frame(width: 24, height: 24).help(focusedWriting ? "Show sidebar" : "Focus writing space")
                }
                NativeButton(title: activeRoute == .playground ? "" : "Done", kind: .utility, symbol: activeRoute == .playground ? "gearshape" : "arrow.left", label: activeRoute == .playground ? "Settings" : "Return to editor", action: { model.studioRoute = activeRoute == .playground ? .general : .playground }).fixedSize().help(activeRoute == .playground ? "Settings · ⌘," : "Return to the editor")
            }
            Text(activeRoute == .playground ? "Writing space" : activeRoute.rawValue).font(.system(size: 30, weight: .semibold)).tracking(-1)
            Text(activeRoute.detail).font(.system(size: 12)).foregroundStyle(Color.textSecondary)
        }.padding(.horizontal, 28).padding(.top, 14).padding(.bottom, 20)
    }
    private var playground: some View {
        VStack(spacing: 0) {
            if !preferences.permissionGranted || preferences.paused || !preferences.passive {
                HStack(spacing: 10) {
                    Image(systemName: !preferences.permissionGranted ? "cursorarrow.click" : "pause.circle").foregroundStyle(Color.mintAccent)
                    VStack(alignment: .leading, spacing: 3) {
                        Text(!preferences.permissionGranted ? "Take Parzr into your editors" : "Editor highlights are paused").font(.system(size: 12, weight: .semibold))
                        Text(!preferences.permissionGranted ? "macOS needs your permission to read and correct text." : "You can still check writing here.").font(.system(size: 10)).foregroundStyle(Color.textSecondary)
                    }
                    Spacer()
                    NativeButton(title: !preferences.permissionGranted ? "Enable…" : "Resume", action: {
                        if !preferences.permissionGranted { preferences.requestPermission() }
                        else { preferences.paused = false; preferences.passive = true }
                    }).fixedSize()
                }.padding(12).graphiteSurface().padding(.horizontal, 28).padding(.bottom, 14)
            }
            VStack(spacing: 0) {
                HStack(spacing: 8) {
                    ScrollView(.horizontal, showsIndicators: false) {
                        ModeChoices(mode: $model.modeChoice).disabled(model.busy)
                    }
                }.padding(.horizontal, 16).padding(.vertical, 12)
                Rectangle().fill(Color.hairline.opacity(0.6)).frame(height: 0.5)
                ZStack(alignment: .topLeading) {
                    DraftEditor(text: $draft, edits: model.marks(for: draft), provisional: model.provisional || model.source != draft, fontSize: preferences.boundedFontSize, lineSpacing: preferences.boundedLineSpacing, highlightFill: preferences.highlightFill, focusedEditID: model.focusedEditID, ignore: { edit in ignored.formUnion(EditPlan.related(to: edit, in: model.result?.edits ?? [edit]).map(\.id)); model.toggle(edit) })
                    if draft.isEmpty {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("A thought. A message. A first draft.").font(.system(size: preferences.boundedFontSize)).foregroundStyle(Color.textSecondary.opacity(0.7))
                            Text("Start writing, or paste a passage.").font(.system(size: 12)).foregroundStyle(Color.textSecondary.opacity(0.55))
                        }.padding(.top, 23).padding(.leading, 27).allowsHitTesting(false)
                    }
                }.frame(maxWidth: .infinity, maxHeight: .infinity).background(Color.writingSurface)
                Rectangle().fill(Color.hairline.opacity(0.6)).frame(height: 0.5)
                HStack(spacing: 8) {
                    if model.busy || (model.result == nil && model.error == nil && !draft.isEmpty) { ProgressView().controlSize(.mini); Text("Checking…") } // before the first answer there is nothing else to show
                    else if model.error != nil { Image(systemName: "exclamationmark.circle").foregroundStyle(Color.errorInk); Text("Check unavailable") }
                    else if draft.isEmpty { Image(systemName: "text.cursor"); Text("A clean slate") }
                    else { Circle().fill(Color.mintAccent).frame(width: 5, height: 5); Text(model.chosenEdits.isEmpty ? "Grammar checked" : "\(model.chosenEdits.count) suggestions").lineLimit(1).help("Click a mint-marked word, or choose Review to see every suggestion") }
                    Spacer(minLength: 0)
                    if !model.chosenEdits.isEmpty {
                        NativeButton(title: "Review", symbol: "list.bullet", label: "Review suggestions", action: { reviewVisible.toggle() }).fixedSize()
                            .popover(isPresented: $reviewVisible, arrowEdge: .bottom) {
                                SuggestionReview(model: model, apply: { edit in
                                    guard model.source == draft, !model.provisional, let next = try? EditPlan.apply(EditPlan.related(to: edit, in: model.chosenEdits), to: draft) else { return }
                                    draft = next
                                }, ignore: { edit in ignored.formUnion(EditPlan.related(to: edit, in: model.result?.edits ?? [edit]).map(\.id)); model.toggle(edit) }, select: { edit in model.focusedEditID = edit.id; reviewVisible = false })
                            }
                    }
                    if draft.isEmpty { NativeButton(title: "Try a sample", action: { draft = "I recieved your mesage.\n\nCan you chek this?" }).fixedSize() }
                    else {
                        NativeButton(title: "Check passage", symbol: "checkmark", enabled: !model.busy, action: { model.playground(draft) }).fixedSize().help("Review the whole passage with the selected writing mode")
                        NativeButton(title: model.status == "Copied to clipboard" ? "Copied" : "Copy", symbol: model.status == "Copied to clipboard" ? "checkmark" : "doc.on.doc", enabled: model.result != nil && !model.busy, action: { guard model.source == draft else { return }; model.copy() }).fixedSize()
                            .changeEffect(.shine(duration: 0.3), value: model.status == "Copied to clipboard", isEnabled: animate)
                        NativeButton(title: "Apply all", kind: .primary, enabled: !model.busy && !model.chosenEdits.isEmpty, action: { guard model.source == draft, !model.provisional else { return }; draft = model.preview; appliedCount += 1; model.playground(draft, debounce: true) }).fixedSize()
                            .changeEffect(.shine(duration: 0.3), value: appliedCount, isEnabled: animate)
                    }
                }.font(.system(size: 11)).foregroundStyle(Color.textSecondary).padding(.horizontal, 16).padding(.vertical, 12)
            }.background(Color.surface).clipShape(RoundedRectangle(cornerRadius: 14))
                .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(Color.hairline, lineWidth: 0.7)).padding(.horizontal, 28)
            if let error = model.error {
                HStack { Text(error).font(.system(size: 11)).foregroundStyle(Color.errorInk); Spacer(); NativeButton(title: "Retry", action: { model.playground(draft) }).fixedSize() }.padding(.horizontal, 28).padding(.top, 10)
            } else if let warning = model.result?.warnings?.first { Text(warning).font(.system(size: 10)).foregroundStyle(Color.textSecondary).frame(maxWidth: .infinity, alignment: .leading).padding(.horizontal, 28).padding(.top, 8) }
            HStack {
                Text("Select text anywhere · \(preferences.shortcutDisplay)")
                Spacer()
                if preferences.showWordCount {
                    Button { statsVisible.toggle() } label: { Text("\(draft.split(whereSeparator: \.isWhitespace).count) words").monospacedDigit() }.buttonStyle(.plain).help("Writing statistics").accessibilityLabel("Writing statistics")
                        .popover(isPresented: $statsVisible) {
                            VStack(alignment: .leading, spacing: 14) {
                                Text("Your draft").font(.system(size: 16, weight: .semibold))
                                stat("Words", "\(draft.split(whereSeparator: \.isWhitespace).count)")
                                stat("Characters", "\(draft.count)")
                                stat("Reading time", draft.isEmpty ? "0 min" : "~\(max(1, Int(ceil(Double(draft.split(whereSeparator: \.isWhitespace).count) / 200)))) min")
                                Text("Reading time assumes 200 words per minute.").font(.system(size: 10)).foregroundStyle(Color.textSecondary)
                            }.padding(18).frame(width: 240).background(Color.canvas).foregroundStyle(Color.textPrimary)
                        }
                }
            }.font(.system(size: 10)).foregroundStyle(Color.textSecondary.opacity(0.75)).padding(.horizontal, 28).padding(.vertical, 17)
        }
    }
    @ViewBuilder private var settings: some View {
        VStack(alignment: .leading, spacing: 22) {
            switch activeRoute {
            case .general:
                group("EVERYDAY") {
                    settingRow("Start with your Mac", detail: "Keep Parzr ready in the menu bar.") { Toggle("Launch at login", isOn: $preferences.launchAtLoginChoice).labelsHidden().toggleStyle(.switch) }
                    divider
                    settingRow("Automatic suggestions", detail: "Catch grammar and spelling as you type.") { toggle("Automatic suggestions", $preferences.passive) }
                    divider
                    settingRow("Selected-text popover", detail: "Show a small correction card when you select a passage.") { toggle("Selected-text popover", $preferences.selectedTextPopover) }
                    divider
                    settingRow("Show in Dock", detail: "Turn off to keep Parzr in the menu bar only. Its menus and Dock icon still appear while a Parzr window is open.") { toggle("Show in Dock", $preferences.showInDock) }
                }
                group("SETUP") {
                    settingRow("Welcome and permissions", detail: preferences.permissionGranted ? "Accessibility is on. Review Contacts, login and the shortcut, or try Parzr again." : "Accessibility is off. Parzr cannot check other apps until you allow it.") { NativeButton(title: "Open", action: { model.showOnboarding?() }).fixedSize() }
                    divider
                    settingRow("Quit Parzr", detail: "Stops checking until you open Parzr again.") { NativeButton(title: "Quit", label: "Quit Parzr", action: { NSApp.terminate(nil) }).fixedSize() }
                }
                group("UPDATES") {
                    settingRow("Check for updates automatically", detail: "Parzr checks GitHub once a day for a new version. It sends nothing about you or your writing.") { toggle("Check for updates automatically", $updates.automaticChecks) }
                    divider
                    settingRow("Download and install automatically", detail: "New versions download quietly and install when you quit Parzr or step away. You can cancel the restart.") { toggle("Download and install automatically", $updates.automaticDownloads).disabled(!updates.automaticChecks) }
                }
                group("YOUR SHORTCUT") {
                    settingRow("Check selected text", detail: "Click to record. Use ⌘, ⌥, or ⌃. Escape cancels.") {
                        VStack(alignment: .trailing, spacing: 6) {
                            ShortcutRecorder().frame(width: 150, height: 28)
                            NativeButton(title: "Reset", kind: .utility, action: { preferences.shortcutKey = 49; preferences.shortcutModifiers = 2048; preferences.shortcutLabel = "Space"; preferences.recordingShortcut = false }).fixedSize()
                        }
                    }
                }
                if model.shortcutConflict { notice("This shortcut is already in use. Choose another.") }
                if let error = preferences.launchError { notice(error) }
            case .writing:
                group("CHECKING") {
                    settingRow("English variant", detail: "Spelling and grammar preferences.") { ChoiceStrip(label: "English variant", choices: [("US", "american"), ("UK", "british")], selection: $preferences.dialect) }
                    divider
                    settingRow("Default mode", detail: "Start every editor selection with this mode.") { ModeChoices(mode: $preferences.defaultMode, compact: true) }
                    divider
                    settingRow("Checking delay", detail: "The longest wait while you type quickly. A pause checks sooner, and a space or punctuation checks at once.") {
                        VStack(alignment: .trailing, spacing: 4) { Slider(value: $preferences.checkingDelay, in: 40...700).frame(width: 130).accessibilityLabel("Checking delay"); Text("\(Int(preferences.boundedCheckingDelay)) ms").font(.system(size: 10, design: .monospaced)).foregroundStyle(Color.textSecondary) }
                    }
                    divider
                    settingRow("Context refinement", detail: "Use the larger bundled model when you check a selection with your shortcut. Typing uses the rules and Smart grammar; tone rewrites always use the larger model.") { toggle("Context refinement", $preferences.contextRefinement) }
                    divider
                    settingRow("Smart grammar (on-device model)", detail: "A small model on your Mac's Neural Engine catches grammar the rules miss, while you type and when you check a selection. Nothing leaves your Mac.") { toggle("Smart grammar", $preferences.smartGrammar) }
                }
                group("PERSONAL DICTIONARY") {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Names, terms, and words to leave alone.").font(.system(size: 11)).foregroundStyle(Color.textSecondary)
                        HStack { TextField("Add a word", text: $dictionaryWord).textFieldStyle(.roundedBorder).onSubmit(addWord); NativeButton(title: "Add", enabled: !dictionaryWord.trimmingCharacters(in: .whitespaces).isEmpty && preferences.dictionary.count < 1000, action: addWord).fixedSize() }
                        ForEach(preferences.dictionary, id: \.self) { word in HStack { Text(word).font(.system(size: 12)); Spacer(); NativeButton(title: "", kind: .utility, symbol: "minus.circle", label: "Remove \(word)", action: { preferences.dictionary.removeAll { $0 == word } }).frame(width: 24, height: 24) } }
                    }.padding(16)
                }
                group("NAMES") {
                    settingRow("Suggest capitalizing names", detail: "Offer to fix the case of a name, like aman to Aman. Chat apps stay quiet unless you choose Everywhere.") {
                        ChoiceStrip(label: "Suggest capitalizing names", choices: [("Never", "never"), ("Email and documents", "documents"), ("Everywhere", "everywhere")], selection: $preferences.capitalizeNamesChoice)
                    }
                    divider
                    settingRow("Use names from Contacts", detail: "Treat the names in your contacts as names, so Parzr never corrects them. Only the names are used, and they stay on this Mac.") { toggle("Use names from Contacts", $preferences.contactsChoice) }
                    if let note = preferences.contactsNote { Text(note).font(.system(size: 11)).foregroundStyle(Color.errorInk).frame(maxWidth: .infinity, alignment: .leading).padding(.horizontal, 16).padding(.bottom, 12) }
                    divider
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Names Parzr learned. It learns a name when you undo a fix, ignore a flag twice, or choose “This is a name”.").font(.system(size: 11)).foregroundStyle(Color.textSecondary)
                        HStack { TextField("Add a name", text: $nameWord).textFieldStyle(.roundedBorder).onSubmit(addName); NativeButton(title: "Add", enabled: WritingEdit.nameToken(nameWord) != nil, action: addName).fixedSize() }
                        if !preferences.learnedNames.isEmpty { ScrollView { LazyVStack(spacing: 0) { ForEach(preferences.learnedNames, id: \.self) { name in HStack { Text(name).font(.system(size: 12)); Spacer(); NativeButton(title: "", kind: .utility, symbol: "minus.circle", label: "Remove \(name)", action: { preferences.learnedNames.removeAll { $0 == name } }).frame(width: 24, height: 24) } } } }.frame(height: min(200, CGFloat(preferences.learnedNames.count) * 28)) }
                    }.padding(16)
                }
                notice("Grammar, spelling, and punctuation are checked in every mode. The model unloads after 30 seconds of inactivity.", symbol: "leaf")
            case .appearance:
                group("LOOK & FEEL") {
                    settingRow("Appearance", detail: "Graphite, Paper, or your Mac’s appearance.") { ChoiceStrip(label: "Appearance", choices: [("Graphite", "graphite"), ("Paper", "paper"), ("System", "system")], selection: $preferences.appearance) }
                    divider
                    settingRow("Reduced motion", detail: "Keep navigation and feedback still. Your Mac’s reduced-motion setting is also respected.") { toggle("Reduced motion", $preferences.reduceMotion) }
                    divider
                    settingRow("Highlight tint", detail: "A subtle tint behind marked words. Underlines stay visible when this is off.") { toggle("Highlight tint", $preferences.highlightFill) }
                }
                group("WRITING SPACE") {
                    settingRow("Text size", detail: "Applies to this writing space.") { Stepper(value: $preferences.editorFontSize, in: 15...24) { Text("\(Int(preferences.boundedFontSize)) pt").monospacedDigit().frame(width: 42) }.fixedSize() }
                    divider
                    settingRow("Line spacing", detail: "More room between lines.") { Stepper(value: $preferences.editorLineSpacing, in: 2...12) { Text("\(Int(preferences.boundedLineSpacing)) pt").monospacedDigit().frame(width: 42) }.fixedSize() }
                    divider
                    settingRow("Word count", detail: "Show a quiet count below your draft.") { toggle("Word count", $preferences.showWordCount) }
                }
                Text("Correction cards and the menu-bar panel follow this appearance.").font(.system(size: 11)).foregroundStyle(Color.textSecondary)
            case .apps:
                notice("Control each app independently. Xcode is checked in comments and strings only; other source-code editors use their integrations; terminals use explicit selection.", symbol: "square.grid.2x2")
                group("CODE EDITORS") {
                    settingRow("Check prose in VS Code and Cursor", detail: "Checks Markdown and plain text files (.md, .markdown, .txt, .mdx, .rst) only, never code. VS Code will show a screen-reader-mode notice, and corrections appear as a review marker instead of underlines.") { toggle("Check prose in VS Code and Cursor", $preferences.checkVSCode) }
                }
                group("OPEN APPLICATIONS") {
                    ForEach(runningApps, id: \.bundleIdentifier) { app in
                        if let id = app.bundleIdentifier {
                            settingRow(app.localizedName ?? id, detail: id) { toggle("Enable \(app.localizedName ?? id)", $preferences[appEnabled: id]) }
                            divider
                        }
                    }
                    ForEach(preferences.disabledApps.filter { id in !runningApps.contains { $0.bundleIdentifier == id } }, id: \.self) { id in settingRow(id, detail: "Disabled") { NativeButton(title: "Enable", action: { preferences.toggleApp(id) }).fixedSize() } }
                }
            case .privacy:
                group("ALWAYS LOCAL") {
                    VStack(alignment: .leading, spacing: 10) {
                        Label("Your words stay on your Mac.", systemImage: "lock.shield").font(.system(size: 17, weight: .medium)).foregroundStyle(Color.mintAccent)
                        Text("Grammar and rewrites run locally. No accounts, telemetry, writing history, or text uploads. Only your dictionary, learned names and preferences are saved.").font(.system(size: 12)).foregroundStyle(Color.textSecondary).lineSpacing(4)
                    }.padding(18)
                }
                group("CLIPBOARD & SESSION") {
                    settingRow("Allow paste fallback", detail: "An explicit option for editors that refuse range edits. May change formatting. Parzr restores an unchanged clipboard after 0.8 seconds.") { toggle("Allow paste fallback", $preferences.clipboardFallback) }
                    divider
                    settingRow("Clear this draft", detail: "Clear the current writing session and its Undo history.") { NativeButton(title: "Clear this writing session", action: { model.clearSession(); draft = "" }).fixedSize() }
                }
                Text("Copy uses the system clipboard. Restoration cannot erase text another app has already read. Editor Undo can revert corrections; some editors use a separate step for each edit.").font(.system(size: 11)).foregroundStyle(Color.textSecondary).lineSpacing(3)
            case .compatibility:
                group("EDITOR ACCESS") {
                    settingRow(preferences.permissionGranted ? "Accessibility is enabled" : "Enable Accessibility", detail: "macOS requires this permission for corrections in other apps.") { NativeButton(title: preferences.permissionGranted ? "Refresh" : "Enable…", action: { if preferences.permissionGranted { preferences.refreshPermission() } else { preferences.requestPermission() } }).fixedSize() }
                    divider
                    settingRow("Optional extensions", detail: "Parzr works in browsers and native apps without them. These add browser inline cards, VS Code diagnostics, and a language server for developers.") { NativeButton(title: "Open integrations", action: { if let url = Bundle.main.resourceURL?.appendingPathComponent("Integrations") { NSWorkspace.shared.open(url) } }).fixedSize() }
                }
                group("CAPABILITY REPORT") {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Select text in another app and use your shortcut. This report contains capabilities, never your writing.").font(.system(size: 11)).foregroundStyle(Color.textSecondary)
                        Text(model.inspector).font(.system(size: 11, design: .monospaced)).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
                        NativeButton(title: "Copy capability report", symbol: "doc.on.doc", action: { NSPasteboard.general.clearContents(); NSPasteboard.general.setString(model.inspector, forType: .string) }).fixedSize()
                    }.padding(16)
                }
                Text("Support depends on each editor exposing editable text and range geometry. Parzr stops when it cannot apply a correction safely.").font(.system(size: 11)).foregroundStyle(Color.textSecondary)
            case .about:
                group("PARZR") {
                    VStack(alignment: .leading, spacing: 14) {
                        Brand()
                        Text("Version \(Support.version) · Apple Silicon · \(Support.build)").font(.system(size: 12)).foregroundStyle(Color.textSecondary)
                        Text("An open-source writing assistant that checks grammar and rewrites text on your Mac. Your words stay with you.").font(.system(size: 12)).foregroundStyle(Color.textSecondary).lineSpacing(4)
                    }.padding(20)
                }
                group("UPDATES") {
                    settingRow("Software update", detail: updates.statusLine) { UpdateCheckButton(model: updates, kind: .secondary) }
                }
                group("HELP & SUPPORT") {
                    settingRow("Report an issue", detail: "Tell us what happened. You choose what to include.") { NativeButton(title: "Report an issue", symbol: "exclamationmark.bubble", action: Support.reportIssue).fixedSize() }
                    divider
                    settingRow("Help and discussion", detail: "github.com/jn-aman/parzr/issues") { NativeButton(title: "Open issues", kind: .utility, action: { NSWorkspace.shared.open(Support.issues) }).fixedSize() }
                    divider
                    settingRow("Open-source licenses", detail: "Credits for the libraries and local model bundled with Parzr.") { NativeButton(title: "View notices", action: { if let url = Bundle.main.resourceURL?.appendingPathComponent("THIRD_PARTY_NOTICES") { NSWorkspace.shared.open(url) } }).fixedSize() }
                }
                notice("Fast grammar checks use the Parzr engine and Apple NaturalLanguage. Passage refinement and tone rewrites use bundled Qwen3.5-0.8B. No model download is needed after installation.", symbol: "cpu")
            case .playground: EmptyView()
            }
        }
    }
    private func stat(_ name: String, _ value: String) -> some View { HStack { Text(name).foregroundStyle(Color.textSecondary); Spacer(); Text(value).monospacedDigit() }.font(.system(size: 12)) }
    private var divider: some View { Rectangle().fill(Color.hairline.opacity(0.5)).frame(height: 0.5).padding(.horizontal, 16) }
    private func group<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 9) { Text(title).font(.system(size: 9, weight: .semibold)).tracking(1.2).foregroundStyle(Color.textSecondary).padding(.leading, 2); VStack(spacing: 0, content: content).graphiteSurface() }
    }
    private func toggle(_ label: String, _ binding: Binding<Bool>) -> some View { Toggle(label, isOn: binding).labelsHidden().toggleStyle(.switch).controlSize(.small).fixedSize() }
    private func notice(_ text: String, symbol: String = "info.circle") -> some View {
        HStack(alignment: .top, spacing: 9) { Image(systemName: symbol).foregroundStyle(Color.mintAccent); Text(text).font(.system(size: 11)).foregroundStyle(Color.textSecondary).lineSpacing(3) }.padding(14).frame(maxWidth: .infinity, alignment: .leading).background(Color.accentWash.opacity(0.4), in: RoundedRectangle(cornerRadius: 10))
    }
    private func settingRow<Content: View>(_ title: String, detail: String, @ViewBuilder control: () -> Content) -> some View {
        HStack(alignment: .center, spacing: 18) { VStack(alignment: .leading, spacing: 5) { Text(title).font(.system(size: 12, weight: .medium)); Text(detail).font(.system(size: 11)).foregroundStyle(Color.textSecondary).fixedSize(horizontal: false, vertical: true).lineSpacing(2) }; Spacer(minLength: 8); control() }.padding(16)
    }
    private var runningApps: [NSRunningApplication] { NSWorkspace.shared.runningApplications.filter { $0.activationPolicy == .regular && $0.bundleIdentifier != Bundle.main.bundleIdentifier }.sorted { ($0.localizedName ?? "") < ($1.localizedName ?? "") } }
    private func addName() { if preferences.learnName(nameWord) { nameWord = "" } }
    private func addWord() { let word = dictionaryWord.trimmingCharacters(in: .whitespacesAndNewlines); guard !word.isEmpty, word.utf8.count <= 128, preferences.dictionary.count < 1000, !preferences.dictionary.contains(word) else { return }; preferences.dictionary.append(word); dictionaryWord = "" }
}
