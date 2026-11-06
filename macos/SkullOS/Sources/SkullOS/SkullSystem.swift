import AppKit
import Foundation
import WebKit

struct SkullConfig: Decodable {
    let pythonExecutable: String
    let repositoryRoot: String
    let defaultModel: String
    let port: Int

    static func fromBundle() throws -> SkullConfig {
        guard let file = Bundle.main.url(forResource: "SkullConfig", withExtension: "json") else {
            throw SkullConfigurationError.missing
        }
        let config = try JSONDecoder().decode(SkullConfig.self, from: Data(contentsOf: file))
        guard (1024...65535).contains(config.port),
              !config.pythonExecutable.isEmpty, !config.repositoryRoot.isEmpty else {
            throw SkullConfigurationError.invalid
        }
        return config
    }
}

enum SkullConfigurationError: LocalizedError {
    case missing, invalid

    var errorDescription: String? {
        switch self {
        case .missing: return "This app is missing SkullConfig.json. Rebuild it using macos/build-app.sh."
        case .invalid: return "The local server configuration is invalid. Rebuild the app."
        }
    }
}

enum SkullMode: String, CaseIterable, Identifiable {
    case fusion, anatomy, xray
    var id: String { rawValue }

    var title: String {
        switch self {
        case .fusion: return "Neural Fusion"
        case .anatomy: return "Anatomy"
        case .xray: return "X-Ray"
        }
    }
    var symbol: String {
        switch self {
        case .fusion: return "brain.head.profile"
        case .anatomy: return "cube.transparent"
        case .xray: return "waveform.path.ecg"
        }
    }
}

private struct LocalModelStatus: Decodable {
    struct Ollama: Decodable {
        let configured: Bool?
        let model_available: Bool?
        let model: String?
    }
    let project: String
    let local_only: Bool
    let ready_for_inference: Bool
    let stopped: Bool
    let ollama: Ollama?
}

@MainActor
final class SkullSystem: ObservableObject {
    static let shared = SkullSystem()

    @Published private(set) var connection = "STARTING"
    @Published private(set) var model = "Checking local model"
    @Published private(set) var inferenceReady = false
    @Published private(set) var emergencyStopped = false
    @Published private(set) var detail = "Initializing the macOS workspace..."
    @Published private(set) var activeMode: SkullMode = .fusion
    @Published private(set) var loaded = false

    private(set) var webView: WKWebView?
    private var server: Process?
    private var started = false
    private var pollTask: Task<Void, Never>?
    private var config: SkullConfig?
    private var ownsServer = false

    var serverURL: URL? {
        guard let config else { return nil }
        return URL(string: "http://127.0.0.1:\(config.port)/")
    }

    func startIfNeeded() {
        guard !started else { return }
        started = true
        do {
            let settings = try SkullConfig.fromBundle()
            guard FileManager.default.isExecutableFile(atPath: settings.pythonExecutable),
                  FileManager.default.fileExists(atPath: settings.repositoryRoot) else {
                throw SkullConfigurationError.invalid
            }
            config = settings
        } catch {
            connection = "SETUP REQUIRED"
            detail = error.localizedDescription
            return
        }
        pollTask = Task { [weak self] in
            guard let self else { return }
            // First probe existing server. Never kill one already owned by the operator.
            if let status = await self.fetchStatus() {
                self.apply(status)
                await self.monitor()
                return
            }
            self.launchServer()
            for _ in 0..<40 {
                guard !Task.isCancelled else { return }
                if let status = await self.fetchStatus() {
                    self.apply(status)
                    await self.monitor()
                    return
                }
                try? await Task.sleep(nanoseconds: 250_000_000)
            }
            self.connection = "UNAVAILABLE"
            self.detail = "Local SKULL service did not start. Run skull-llm doctor in Terminal."
        }
    }

    private func launchServer() {
        guard let config, server == nil else { return }
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: config.pythonExecutable)
        proc.arguments = ["-m", "skull_llm", "serve", "--port", String(config.port)]
        proc.currentDirectoryURL = URL(fileURLWithPath: config.repositoryRoot, isDirectory: true)
        var env = ProcessInfo.processInfo.environment
        if env["OLLAMA_MODEL"] == nil { env["OLLAMA_MODEL"] = config.defaultModel }
        // Avoid passing arbitrary model providers to subprocess. The SKULL service
        // itself rejects non-loopback Ollama and honors the emergency stop.
        proc.environment = env
        proc.standardInput = FileHandle.nullDevice
        proc.standardOutput = FileHandle.nullDevice
        proc.standardError = FileHandle.nullDevice
        do {
            try proc.run()
            server = proc
            ownsServer = true
            connection = "CONNECTING"
            detail = "Starting the local 3D intelligence service..."
        } catch {
            connection = "LAUNCH FAILED"
            detail = "Could not start Python: \(error.localizedDescription)"
        }
    }

    private func fetchStatus() async -> LocalModelStatus? {
        guard let url = serverURL?.appendingPathComponent("api/status") else { return nil }
        var request = URLRequest(url: url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.timeoutInterval = 2
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let response = response as? HTTPURLResponse,
                  response.statusCode == 200, data.count < 100_000 else { return nil }
            let status = try JSONDecoder().decode(LocalModelStatus.self, from: data)
            guard status.project == "SKULL-LLM" && status.local_only else { return nil }
            return status
        } catch {
            return nil
        }
    }

    private func apply(_ status: LocalModelStatus) {
        connection = "CONNECTED"
        inferenceReady = status.ready_for_inference
        emergencyStopped = status.stopped
        model = status.ollama?.model ?? config?.defaultModel ?? "Unselected model"
        detail = status.stopped ? "Emergency stop engaged. Inference disabled." :
                 status.ready_for_inference ? "Local Ollama model available." :
                 "3D graphics available. Local inference is offline."
        if !loaded { loaded = true }
    }

    private func monitor() async {
        while !Task.isCancelled {
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            guard !Task.isCancelled else { break }
            if let status = await fetchStatus() {
                apply(status)
            } else {
                connection = "DISCONNECTED"
                inferenceReady = false
                loaded = false
                detail = "Local SKULL service is not responding. Use Refresh to retry."
            }
        }
    }

    func refreshStatus() {
        if !started { startIfNeeded(); return }
        Task { [weak self] in
            guard let self else { return }
            if let status = await self.fetchStatus() { self.apply(status) }
            else {
                self.connection = "DISCONNECTED"
                self.inferenceReady = false
                self.loaded = false
                self.detail = "SKULL service unavailable. Restart the app to relaunch it."
            }
        }
    }

    func bindWebView(_ view: WKWebView) {
        webView = view
    }

    func selectMode(_ mode: SkullMode) {
        activeMode = mode
        guard loaded else { return }
        // Whitelist of known values: never interpolate free-form user input.
        webView?.evaluateJavaScript("document.querySelector('button[data-mode=\"\(mode.rawValue)\"]')?.click();")
    }

    func focusPrompt() {
        webView?.evaluateJavaScript("document.getElementById('prompt')?.focus();")
    }

    func resetView() {
        webView?.evaluateJavaScript("document.getElementById('reset-view')?.click();")
    }

    func exportImage() {
        guard let view = webView, loaded else { return }
        let panel = NSSavePanel()
        panel.nameFieldStringValue = "SKULL-OS-3D.png"
        panel.allowedContentTypes = [.png]
        panel.canCreateDirectories = true
        guard panel.runModal() == .OK, let url = panel.url else { return }
        view.takeSnapshot(with: nil) { image, error in
            guard error == nil, let image,
                  let tiff = image.tiffRepresentation,
                  let bitmap = NSBitmapImageRep(data: tiff),
                  let data = bitmap.representation(using: .png, properties: [:]) else { return }
            try? data.write(to: url, options: .atomic)
        }
    }

    func copyTerminalCommand() {
        guard let config else { return }
        let quotedRoot = "'" + config.repositoryRoot.replacingOccurrences(of: "'", with: "'\\''") + "'"
        let command = "cd \(quotedRoot) && .venv/bin/biochip-cl1-skull-gpt-skull"
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(command, forType: .string)
    }

    func stopOwnedServer() {
        pollTask?.cancel()
        pollTask = nil
        guard ownsServer, let server, server.isRunning else { return }
        server.terminate()
        ownsServer = false
        self.server = nil
    }
}
