import Foundation

enum AppConfiguration {
    static let apiBaseURL: URL = {
        guard let url = URL(
            string: "https://api.murderroom.thomaspercival.dev"
        ) else {
            fatalError("Invalid API base URL")
        }

        return url
    }()
}
