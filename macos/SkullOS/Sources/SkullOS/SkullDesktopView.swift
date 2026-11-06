import AppKit
import SwiftUI

struct SkullDesktopView: View {
    @EnvironmentObject private var system: SkullSystem
    @State private var showingDiagnostics = false

    var body: some View {
        HStack(spacing: 0) {
            sidebar
                .frame(width: 214)
                .background(Color(red: 0.035, green: 0.051, blue: 0.074))
            Rectangle().fill(.white.opacity(0.07)).frame(width: 1)
            VStack(spacing: 0) {
                header
                Divider()
                ZStack {
                    Color(red: 0.03, green: 0.05, blue: 0.08)
                    if system.loaded {
                        SkullWebView()
                    } else {
                        VStack(spacing: 13) {
                            Image(system.connection == "SETUP REQUIRED" ? "exclamationmark.triangle" : "network")
                                .font(.system(size: 48, weight: .ultraLight))
                                .foregroundStyle(.mint)
                            Text(system.connection)
                                .font(.system(.title2, design: .monospaced, weight: .semibold))
                            Text(system.detail)
                                .foregroundStyle(.secondary)
                                .multilineTextAlignment(.center)
                                .frame(maxWidth: 430)
                            Button("Retry Connection") { system.refreshStatus() }
                                .buttonStyle(.borderedProminent)
                        }
                        .padding(24)
                    }
                }
            }
        }
        .preferredColorScheme(.dark)
        .background(Color(red: 0.03, green: 0.045, blue: 0.07))
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                Button {
                    system.resetView()
                } label: {
                    Label("Reset 3D", systemImage: "arrow.counterclockwise")
                }
                Button {
                    system.focusPrompt()
                } label: {
                    Label("Ask SKULL", systemImage: "text.cursor")
                }
                Button {
                    system.exportImage()
                } label: {
                    Label("Export PNG", systemImage: "square.and.arrow.down")
                }
            }
        }
        .sheet(isPresented: $showingDiagnostics) {
            diagnostics
        }
    }

    private var sidebar: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(spacing: 10) {
                Image(systemName: "brain.head.profile")
                    .font(.title2).foregroundStyle(.mint)
                VStack(alignment: .leading, spacing: 1) {
                    Text("SKULL OS").font(.system(size: 17, weight: .bold, design: .rounded))
                    Text("GPT-DOUG / LOCAL").font(.system(size: 9, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
            }
            .padding(.top, 20)
            Divider()
            Text("WORKSPACE")
                .font(.system(size: 10, weight: .semibold, design: .monospaced))
                .foregroundStyle(.secondary)
            ForEach(SkullMode.allCases) { mode in
                Button {
                    system.selectMode(mode)
                } label: {
                    HStack(spacing: 10) {
                        Image(systemName: mode.symbol).frame(width: 24)
                        Text(mode.title).font(.system(size: 13))
                        Spacer(minLength: 0)
                    }
                    .padding(.vertical, 10)
                    .padding(.horizontal, 11)
                    .background(system.activeMode == mode ? Color.mint.opacity(0.15) : Color.clear)
                    .overlay(RoundedRectangle(cornerRadius: 7)
                        .stroke(system.activeMode == mode ? Color.mint.opacity(0.40) : .clear))
                    .cornerRadius(7)
                }
                .buttonStyle(.plain)
                .foregroundStyle(system.activeMode == mode ? .mint : .white.opacity(0.78))
            }
            Divider()
            Text("RUNTIME")
                .font(.system(size: 10, weight: .semibold, design: .monospaced))
                .foregroundStyle(.secondary)
            statusRow("SERVICE", system.connection)
            statusRow("INFERENCE", system.emergencyStopped ? "STOPPED" : system.inferenceReady ? "READY" : "OFFLINE")
            statusRow("CL1", "SIMULATED")
            Divider()
            Button {
                showingDiagnostics = true
            } label: {
                Label("Diagnostics", systemImage: "stethoscope")
            }
            Button {
                system.copyTerminalCommand()
            } label: {
                Label("Copy CLI Command", systemImage: "terminal")
            }
            Spacer(minLength: 12)
            Text("LOCAL OS FRAMEWORK • ALPHA")
                .font(.system(size: 9, design: .monospaced))
                .foregroundStyle(.secondary)
            Text("3D neural visuals are software simulation. No physical CL1 link.")
                .font(.system(size: 10))
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(.horizontal, 15)
        .padding(.bottom, 15)
        .frame(maxHeight: .infinity, alignment: .top)
    }

    private func statusRow(_ key: String, _ value: String) -> some View {
        HStack {
            Text(key).foregroundStyle(.secondary)
            Spacer()
            Text(value).foregroundStyle(value == "READY" || value == "CONNECTED" ? .mint : .white)
        }
        .font(.system(size: 10, design: .monospaced))
    }

    private var header: some View {
        HStack(spacing: 14) {
            Image(systemName: "square.3.layers.3d")
                .foregroundStyle(.mint)
            Text("NEURAL 3D DESKTOP")
                .font(.system(size: 11, weight: .bold, design: .monospaced))
            Spacer()
            Circle().fill(system.inferenceReady ? Color.mint : Color.orange)
                .frame(width: 7, height: 7)
            Text(system.model)
                .foregroundStyle(.secondary)
                .font(.system(size: 11, design: .monospaced))
                .lineLimit(1)
            Button {
                system.refreshStatus()
            } label: {
                Image(systemName: "arrow.clockwise")
            }
            .buttonStyle(.borderless)
        }
        .padding(.horizontal, 16)
        .frame(height: 45)
        .background(Color.black.opacity(0.20))
    }

    private var diagnostics: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Label("SKULL OS / Diagnostics", systemImage: "waveform.path.ecg")
                    .font(.title2)
                Spacer()
                Button("Done") { showingDiagnostics = false }
            }
            Divider()
            statusRow("LOCAL SERVICE", system.connection)
            statusRow("OLLAMA INFERENCE", system.inferenceReady ? "READY" : "OFFLINE")
            statusRow("EMERGENCY STOP", system.emergencyStopped ? "ENGAGED" : "CLEAR")
            statusRow("CL1 DEVICE", "NOT CONNECTED")
            Text(system.detail).foregroundStyle(.secondary)
            Text("Native macOS application shell. 3D graphics, status and local LLM use the installed SKULL-LLM service. No cloud credentials required.")
                .foregroundStyle(.secondary)
            Button("Copy Terminal Launcher") { system.copyTerminalCommand() }
        }
        .padding(26)
        .frame(width: 480)
    }
}
