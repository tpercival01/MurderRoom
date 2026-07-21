import Foundation

enum SuspectAssessment: String, CaseIterable, Codable, Equatable, Hashable {
    case unknown
    case suspicious
    case cleared
    case primeSuspect

    var title: String {
        switch self {
        case .unknown:
            return "Unknown"
        case .suspicious:
            return "Suspicious"
        case .cleared:
            return "Cleared"
        case .primeSuspect:
            return "Prime Suspect"
        }
    }
}
