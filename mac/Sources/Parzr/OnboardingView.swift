import AppKit
import Contacts
import SwiftUI

struct OnboardingView: View {
    static let size = NSSize(width: 600, height: 480)
    @Environment(\.accessibilityReduceMotion) private var systemReduceMotion
    @ObservedObject var model: OnboardingModel
    @ObservedObject private var preferences: Preferences
    @ObservedObject private var updates = UpdateModel.shared
    var renderingSnapshot = false
    var settings: () -> Void = {}
    var finish: () -> Void = {}
    private var animate: Bool { !systemReduceMotion && !preferences.reduceMotion && !renderingSnapshot }
    private var granted: Bool { model.granted }
    init(model: OnboardingModel, renderingSnapshot: Bool = false, settings: @escaping () -> Void = {}, finish: @escaping () -> Void = {}) {
        self.model = model; _preferences = ObservedObject(wrappedValue: model.preferences)
        self.renderingSnapshot = renderingSnapshot; self.settings = settings; self.finish = finish
    }
    var body: some View {
        VStack(spacing: 0) {
            header
            ZStack { content.id(model.step).transition(.opacity) }.frame(maxWidth: .infinity, maxHeight: .infinity)
            Rectangle().fill(Color.hairline.opacity(0.6)).frame(height: 0.5)
            footer
        }
        .frame(width: Self.size.width, height: Self.size.height).background(Color.canvas).foregroundStyle(Color.textPrimary).tint(Color.mintAccent)
        .onAppear { if !renderingSnapshot { preferences.refreshPermission(); if !granted { preferences.watchPermission() } } }
    }
    private func go(_ change: () -> Void) { withAnimation(animate ? .easeOut(duration: 0.18) : nil, change) }
    // MARK: Chrome
    private var header: some View {
        HStack(spacing: 5) {
            ForEach(OnboardingStep.allCases, id: \.rawValue) { item in
                Capsule().fill(item == model.step ? Color.mintAccent : item.rawValue < model.step.rawValue ? Color.mintAccent.opacity(0.45) : Color.hairline)
                    .frame(width: item == model.step ? 22 : 6, height: 6)
            }
            .animation(animate ? .easeOut(duration: 0.18) : nil, value: model.step)
            Spacer()
            Text("\(model.step.rawValue + 1) of \(OnboardingStep.allCases.count)").font(.system(size: 10, weight: .medium)).monospacedDigit().foregroundStyle(Color.textSecondary.opacity(0.8))
        }.padding(.horizontal, 40).padding(.top, 22).frame(height: 40, alignment: .top)
            .accessibilityElement(children: .ignore).accessibilityLabel("Step \(model.step.rawValue + 1) of \(OnboardingStep.allCases.count)")
    }
    private var footer: some View {
        HStack(spacing: 8) {
            if model.step != .welcome { NativeButton(title: "Back", kind: .utility, symbol: "chevron.left", action: { go(model.back) }).fixedSize() }
            Spacer()
            if model.step == .accessibility && !granted { NativeButton(title: "Skip for now", kind: .utility, action: { go(model.skip) }).fixedSize() }
            if model.step == .done { NativeButton(title: "Start writing", kind: .primary, key: "\r", action: finish).fixedSize() }
            else { NativeButton(title: model.step == .welcome ? "Get started" : "Continue", kind: .primary, key: "\r", enabled: model.canAdvance, action: { go(model.next) }).fixedSize() }
        }.padding(.horizontal, 40).frame(height: 62)
    }
    @ViewBuilder private var content: some View {
        switch model.step {
        case .welcome: welcome
        case .accessibility: accessibility
        case .contacts: contacts
        case .login: login
        case .tryIt: tryIt
        case .done: done
        }
    }
    // MARK: Pieces
    private func page<Body: View>(_ eyebrow: String, _ title: String, _ detail: String, @ViewBuilder body: () -> Body) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(eyebrow).font(.system(size: 9, weight: .semibold)).tracking(1.8).foregroundStyle(Color.mintAccent)
            Text(title).font(.system(size: 28, weight: .semibold)).tracking(-0.9).padding(.top, 8)
            Text(detail).font(.system(size: 13)).foregroundStyle(Color.textSecondary).lineSpacing(3).fixedSize(horizontal: false, vertical: true).padding(.top, 8)
            body().padding(.top, 22)
            Spacer(minLength: 0)
        }.padding(.horizontal, 40).padding(.top, 16).frame(maxWidth: .infinity, alignment: .leading)
    }
    private func hero(_ symbol: String?, _ title: String, _ detail: String) -> some View {
        VStack(spacing: 0) {
            RoundedRectangle(cornerRadius: 20).fill(Color.accentWash).frame(width: 76, height: 76)
                .overlay(RoundedRectangle(cornerRadius: 20).strokeBorder(Color.mintAccent.opacity(0.25), lineWidth: 0.5))
                .overlay { if let symbol { Image(systemName: symbol).font(.system(size: 32, weight: .medium)).foregroundStyle(Color.mintAccent) } else { ParzrMark().fill(Color.mintAccent, style: FillStyle(eoFill: true)).frame(width: 36, height: 42) } }
            Text(title).font(.system(size: 30, weight: .semibold)).tracking(-1).padding(.top, 22)
            Text(detail).font(.system(size: 14)).foregroundStyle(Color.textSecondary).lineSpacing(4).multilineTextAlignment(.center).fixedSize(horizontal: false, vertical: true).padding(.top, 10).frame(maxWidth: 400)
        }
    }
    private var divider: some View { Rectangle().fill(Color.hairline.opacity(0.5)).frame(height: 0.5).padding(.horizontal, 16) }
    private func row<Control: View>(_ symbol: String, _ title: String, _ detail: String, @ViewBuilder control: () -> Control) -> some View {
        HStack(alignment: .center, spacing: 14) {
            Image(systemName: symbol).font(.system(size: 15, weight: .medium)).foregroundStyle(Color.mintAccent).frame(width: 36, height: 36).background(Color.accentWash, in: RoundedRectangle(cornerRadius: 9))
            VStack(alignment: .leading, spacing: 4) { Text(title).font(.system(size: 13, weight: .medium)); Text(detail).font(.system(size: 11)).foregroundStyle(Color.textSecondary).lineSpacing(2).fixedSize(horizontal: false, vertical: true) }
            Spacer(minLength: 8); control()
        }.padding(16)
    }
    private func statusRow(_ title: String, good: Bool, alert: Bool = true) -> some View {
        HStack(spacing: 8) {
            if good { Image(systemName: "checkmark.circle.fill").font(.system(size: 16)).foregroundStyle(Color.mintAccent) }
            else { Circle().fill(alert ? Color.errorInk : Color.textSecondary.opacity(0.6)).frame(width: 6, height: 6).padding(.horizontal, 5) }
            Text(title).font(.system(size: 12, weight: .medium))
        }
    }
    private func warning(_ text: String) -> some View {
        HStack(alignment: .top, spacing: 8) { Image(systemName: "exclamationmark.triangle").foregroundStyle(Color.errorInk); Text(text).foregroundStyle(Color.textSecondary).lineSpacing(2).fixedSize(horizontal: false, vertical: true) }.font(.system(size: 11))
    }
    // MARK: Steps
    private var welcome: some View {
        VStack(spacing: 24) {
            Spacer(minLength: 0)
            hero(nil, "Welcome to Parzr", "Grammar and spelling help in every app. Offline. Your words never leave this Mac.")
            HStack(spacing: 8) {
                ForEach([("lock", "Offline"), ("person.crop.circle.badge.xmark", "No account"), ("macwindow", "Every app")], id: \.1) { symbol, text in
                    HStack(spacing: 6) { Image(systemName: symbol).foregroundStyle(Color.mintAccent); Text(text) }.font(.system(size: 11, weight: .medium)).foregroundStyle(Color.textSecondary)
                        .padding(.horizontal, 11).frame(height: 27).background(Color.surface, in: Capsule()).overlay(Capsule().strokeBorder(Color.hairline.opacity(0.7), lineWidth: 0.5))
                }
            }
            Spacer(minLength: 0)
        }.frame(maxWidth: .infinity).padding(.bottom, 24)
    }
    private var accessibility: some View {
        page("STEP 2 · REQUIRED", "Allow Accessibility", "Parzr needs Accessibility so it can read and correct the text you write in other apps.") {
            VStack(alignment: .leading, spacing: 14) {
                VStack(spacing: 0) {
                    row("hand.raised", "Accessibility access", "Turn Parzr on, then come back here.") {
                        if !granted { NativeButton(title: "Open Accessibility Settings", kind: .primary, action: { preferences.requestPermission() }).fixedSize() }
                    }
                    divider
                    HStack {
                        if granted { statusRow("Accessibility is on", good: true) } else { statusRow("Waiting for permission", good: false) }
                        Spacer()
                        Text("No restart needed.").font(.system(size: 11)).foregroundStyle(Color.textSecondary)
                    }.padding(.horizontal, 16).frame(height: 46)
                }.graphiteSurface()
                if !granted { warning("You can skip for now, but Parzr cannot check text in other apps until this is on.") }
            }
        }
    }
    private var contactsState: OnboardingFlow.ContactsState { OnboardingFlow.contactsState(CNContactStore.authorizationStatus(for: .contacts)) }
    private var contacts: some View {
        page("STEP 3 · OPTIONAL", "Know your names", "Names from your contacts are never corrected. Names stay on this Mac.") {
            VStack(alignment: .leading, spacing: 14) {
                VStack(spacing: 0) {
                    row("person.crop.circle", "Use names from Contacts", "Only first names, last names, nicknames and companies are read.") { Toggle("Use names from Contacts", isOn: $preferences.contactsChoice).labelsHidden().toggleStyle(.switch).controlSize(.small).fixedSize() }
                    divider
                    HStack {
                        switch contactsState {
                        case .allowed: statusRow("Contacts allowed", good: true)
                        case .denied: statusRow("Contacts not allowed", good: false)
                        case .notAsked: statusRow("Not requested yet", good: false, alert: false)
                        }
                        Spacer()
                        if contactsState == .denied, let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Contacts") { NativeButton(title: "Open Settings", kind: .utility, action: { NSWorkspace.shared.open(url) }).fixedSize() }
                    }.padding(.horizontal, 16).frame(height: 46)
                }.graphiteSurface()
                if let note = preferences.contactsNote { Text(note).font(.system(size: 11)).foregroundStyle(Color.errorInk).fixedSize(horizontal: false, vertical: true) }
                Text("You can change this later in Settings.").font(.system(size: 11)).foregroundStyle(Color.textSecondary)
            }
        }
    }
    private var login: some View {
        page("STEP 4 · OPTIONAL", "Start at login", "Parzr is light and quiet. Starting with your Mac keeps it ready the moment you write.") {
            VStack(alignment: .leading, spacing: 14) {
                VStack(spacing: 0) {
                    row("power", "Start with your Mac", "Keep Parzr ready in the menu bar.") { Toggle("Launch at login", isOn: $preferences.launchAtLoginChoice).labelsHidden().toggleStyle(.switch).controlSize(.small).fixedSize() }
                    divider
                    HStack(spacing: 14) {
                        Spacer()
                        Image(systemName: "wifi"); Image(systemName: "battery.75")
                        ParzrMark().fill(Color.mintAccent, style: FillStyle(eoFill: true)).frame(width: 13, height: 15).padding(5).background(Color.accentWash, in: RoundedRectangle(cornerRadius: 5))
                        Text("Mon 9:41").monospacedDigit()
                    }.font(.system(size: 11, weight: .medium)).foregroundStyle(Color.textSecondary).padding(.horizontal, 16).frame(height: 38).accessibilityHidden(true)
                }.graphiteSurface()
                if let error = preferences.launchError { Text(error).font(.system(size: 11)).foregroundStyle(Color.errorInk).fixedSize(horizontal: false, vertical: true) }
                Text("Parzr lives in the menu bar. You can change this later in Settings.").font(.system(size: 11)).foregroundStyle(Color.textSecondary)
            }
        }
    }
    private var tryIt: some View {
        page("STEP 5 · TRY IT", "See it work", "Parzr underlines mistakes in red. Click an underlined word to fix it.") {
            VStack(alignment: .leading, spacing: 14) {
                OnboardingTryField(model: model, preferences: preferences, renderingSnapshot: renderingSnapshot)
                HStack(spacing: 8) {
                    Text("Select text in any app and press").font(.system(size: 12)).foregroundStyle(Color.textSecondary)
                    Text(preferences.shortcutDisplay).font(.system(size: 11, weight: .medium)).padding(.horizontal, 8).frame(height: 22).background(Color.surface, in: RoundedRectangle(cornerRadius: 5))
                        .overlay(RoundedRectangle(cornerRadius: 5).strokeBorder(Color.hairline.opacity(0.8), lineWidth: 0.5))
                    Spacer(minLength: 0)
                    NativeButton(title: "Change shortcut", kind: .utility, action: settings).fixedSize()
                }
            }
        }
    }
    private var done: some View {
        VStack(spacing: 20) {
            Spacer(minLength: 0)
            hero("checkmark", "You’re set.", "Parzr is ready. Here is what to know.")
            VStack(spacing: 0) {
                tip("globe", "Works in Safari, Chrome, Firefox and native apps. No extension needed.")
                divider
                tip("menubar.arrow.up.rectangle", "Click the Parzr icon in the menu bar to pause or change settings.")
                divider
                HStack(spacing: 12) {
                    Image(systemName: "arrow.triangle.2.circlepath").font(.system(size: 13, weight: .medium)).foregroundStyle(Color.mintAccent).frame(width: 20)
                    Text("Parzr checks GitHub once a day for a new version. It sends nothing about you or your writing.").font(.system(size: 12)).lineSpacing(2).fixedSize(horizontal: false, vertical: true).frame(maxWidth: .infinity, alignment: .leading)
                    Toggle("Check for updates automatically", isOn: $updates.automaticChecks).labelsHidden().toggleStyle(.switch).controlSize(.small).fixedSize()
                }.padding(.horizontal, 16).padding(.vertical, 11)
                if !granted {
                    divider
                    HStack(spacing: 10) { warning("Accessibility is still off, so Parzr cannot check other apps yet.").frame(maxWidth: .infinity, alignment: .leading); NativeButton(title: "Enable…", action: { preferences.requestPermission() }).fixedSize() }.padding(.horizontal, 16).padding(.vertical, 9)
                }
            }.graphiteSurface().frame(maxWidth: 480)
            Spacer(minLength: 0)
        }.frame(maxWidth: .infinity).padding(.bottom, 12)
    }
    private func tip(_ symbol: String, _ text: String) -> some View {
        HStack(spacing: 12) { Image(systemName: symbol).font(.system(size: 13, weight: .medium)).foregroundStyle(Color.mintAccent).frame(width: 20); Text(text).font(.system(size: 12)).lineSpacing(2).fixedSize(horizontal: false, vertical: true).frame(maxWidth: .infinity, alignment: .leading) }.padding(.horizontal, 16).padding(.vertical, 13)
    }
}

/// The live editor on the Try it step: real engine, real underlines, click one to fix it.
private struct OnboardingTryField: View {
    @ObservedObject var model: OnboardingModel
    @ObservedObject var editor: AppModel
    @ObservedObject var preferences: Preferences
    let renderingSnapshot: Bool
    init(model: OnboardingModel, preferences: Preferences, renderingSnapshot: Bool) {
        self.model = model; self.editor = model.editor; self.preferences = preferences; self.renderingSnapshot = renderingSnapshot
    }
    var body: some View {
        VStack(spacing: 0) {
            DraftEditor(text: $model.draft, edits: editor.source == model.draft ? editor.chosenEdits : [], fontSize: 16, lineSpacing: 5, highlightFill: preferences.highlightFill, ignore: { editor.toggle($0) })
                .frame(height: 66).background(Color.writingSurface)
            Rectangle().fill(Color.hairline.opacity(0.6)).frame(height: 0.5)
            HStack(spacing: 8) {
                if editor.result == nil || editor.busy { ProgressView().controlSize(.mini); Text("Checking…") }
                else if editor.chosenEdits.isEmpty { Image(systemName: "checkmark.circle.fill").foregroundStyle(Color.mintAccent); Text("All clear. That is Parzr.") }
                else { Circle().fill(Color.issueInk).frame(width: 5, height: 5); Text("\(editor.chosenEdits.count) \(editor.chosenEdits.count == 1 ? "suggestion" : "suggestions")") }
                Spacer(minLength: 0)
                if model.draft != OnboardingFlow.sample { NativeButton(title: "Reset", kind: .utility, action: { model.draft = OnboardingFlow.sample }).fixedSize() }
            }.font(.system(size: 11)).foregroundStyle(Color.textSecondary).padding(.horizontal, 14).frame(height: 34).background(Color.surface)
        }.clipShape(RoundedRectangle(cornerRadius: 12)).overlay(RoundedRectangle(cornerRadius: 12).strokeBorder(Color.hairline, lineWidth: 0.7))
            .onAppear { if !renderingSnapshot { editor.playground(model.draft, debounce: true) } }
            .onChange(of: model.draft) { text in editor.playground(text, debounce: true) }
            .onChange(of: preferences.learnedNames) { _ in editor.playground(model.draft, debounce: true) }
    }
}
