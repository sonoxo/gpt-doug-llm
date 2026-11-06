import Foundation
import SwiftUI
import WebKit

struct SkullWebView: NSViewRepresentable {
    @EnvironmentObject private var system: SkullSystem

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeNSView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        configuration.defaultWebpagePreferences.allowsContentJavaScript = true
        configuration.preferences.javaScriptCanOpenWindowsAutomatically = false
        let view = WKWebView(frame: .zero, configuration: configuration)
        view.navigationDelegate = context.coordinator
        view.uiDelegate = context.coordinator
        view.allowsBackForwardNavigationGestures = false
        system.bindWebView(view)
        return view
    }

    func updateNSView(_ view: WKWebView, context: Context) {
        guard system.loaded, let url = system.serverURL else { return }
        if view.url != url && !view.isLoading {
            view.load(URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData))
        }
    }

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate {
        // Reject external navigation. Model-provided URLs must never silently
        // turn the local command cockpit into an Internet browser.
        func webView(
            _ webView: WKWebView,
            decidePolicyFor action: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
        ) {
            let url = action.request.url
            let allowed = url?.scheme == "http" && url?.host == "127.0.0.1"
                          && url?.port == SkullSystem.shared.serverURL?.port
            decisionHandler(allowed ? .allow : .cancel)
        }

        func webView(
            _ webView: WKWebView,
            createWebViewWith configuration: WKWebViewConfiguration,
            for navigationAction: WKNavigationAction,
            windowFeatures: WKWindowFeatures
        ) -> WKWebView? {
            nil
        }
    }
}
