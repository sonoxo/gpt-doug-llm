import AppKit
import SwiftUI

@main
struct SkullOSApp: App {
    @NSApplicationDelegateAdaptor(SkullAppDelegate.self) private var delegate
    @StateObject private var system = SkullSystem.shared

    var body: some Scene {
        WindowGroup("SKULL OS") {
            SkullDesktopView()
                .environmentObject(system)
                .frame(minWidth: 900, minHeight: 620)
                .onAppear { system.startIfNeeded() }
        }
        .defaultSize(width: 1440, height: 900)
        .commands {
            CommandMenu("SKULL") {
                Button("Neural Fusion") { system.selectMode(.fusion) }
                    .keyboardShortcut("1", modifiers: .command)
                Button("Anatomy") { system.selectMode(.anatomy) }
                    .keyboardShortcut("2", modifiers: .command)
                Button("X-Ray") { system.selectMode(.xray) }
                    .keyboardShortcut("3", modifiers: .command)
                Divider()
                Button("Focus Prompt") { system.focusPrompt() }
                    .keyboardShortcut("k", modifiers: .command)
                Button("Reset 3D View") { system.resetView() }
                    .keyboardShortcut("0", modifiers: .command)
                Button("Refresh Model Status") { system.refreshStatus() }
                    .keyboardShortcut("r", modifiers: .command)
                Divider()
                Button("Export Window PNG") { system.exportImage() }
                    .keyboardShortcut("s", modifiers: [.command, .shift])
            }
        }
    }
}

@MainActor
final class SkullAppDelegate: NSObject, NSApplicationDelegate {
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    func applicationWillTerminate(_ notification: Notification) {
        SkullSystem.shared.stopOwnedServer()
    }
}
