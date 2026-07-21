import Foundation
import ImageIO
import UIKit
import Vision

enum RoomObjectRecognitionError: Error, Equatable {
    case imageCouldNotBeRead
    case noRecognisableLabels
}

struct RoomObjectRecogniser {
    func recognise(
        in image: UIImage
    ) throws -> [String] {
        guard let cgImage = image.cgImage else {
            throw RoomObjectRecognitionError
                .imageCouldNotBeRead
        }

        let request = VNClassifyImageRequest()

        let handler = VNImageRequestHandler(
            cgImage: cgImage,
            orientation: image.cgImageOrientation,
            options: [:]
        )

        try handler.perform([request])

        let observations = request.results ?? []

        let rawLabels = observations
            .filter { $0.confidence >= 0.05 }
            .map { observation in
                observation.identifier
                    .split(separator: ",")
                    .first
                    .map(String.init) ?? observation.identifier
            }

        let suggestions = Self.normaliseLabels(rawLabels)

        guard !suggestions.isEmpty else {
            throw RoomObjectRecognitionError
                .noRecognisableLabels
        }

        return Array(suggestions.prefix(4))
    }

    static func normaliseLabels(
        _ labels: [String]
    ) -> [String] {
        var results: [String] = []
        var seenLabels = Set<String>()

        for label in labels {
            let cleanedLabel = label
                .replacingOccurrences(of: "_", with: " ")
                .trimmingCharacters(
                    in: .whitespacesAndNewlines
                )
                .lowercased()

            guard
                !cleanedLabel.isEmpty,
                let canonicalLabel = canonicalLabel(
                    for: cleanedLabel
                )
            else {
                continue
            }

            let comparisonKey = canonicalLabel.lowercased()

            guard seenLabels.insert(comparisonKey).inserted else {
                continue
            }

            results.append(canonicalLabel)
        }

        return results
    }

    private static func canonicalLabel(
        for label: String
    ) -> String? {
        let ignoredLabels: Set<String> = [
            "machine",
            "consumer electronics",
            "electronic device",
            "equipment",
            "technology",
            "interior",
            "room"
        ]

        if ignoredLabels.contains(label) {
            return nil
        }

        switch label {
        case "computer",
             "desktop computer",
             "laptop",
             "notebook computer",
             "portable computer":
            return "Computer"

        case "computer monitor",
             "monitor",
             "display",
             "screen":
            return "Monitor"

        case "computer keyboard",
             "keyboard":
            return "Keyboard"

        case "computer mouse",
             "mouse":
            return "Mouse"

        case "writing desk",
             "desk",
             "table":
            return "Desk"

        case "office chair",
             "chair":
            return "Chair"

        case "desk lamp",
             "lamp",
             "light fixture":
            return "Lamp"

        case "coffee mug",
             "mug",
             "cup":
            return "Mug"

        case "bookcase",
             "bookshelf",
             "shelf":
            return "Bookshelf"

        default:
            return label.capitalized
        }
    }
}

private extension UIImage {
    var cgImageOrientation: CGImagePropertyOrientation {
        switch imageOrientation {
        case .up:
            return .up

        case .upMirrored:
            return .upMirrored

        case .down:
            return .down

        case .downMirrored:
            return .downMirrored

        case .left:
            return .left

        case .leftMirrored:
            return .leftMirrored

        case .right:
            return .right

        case .rightMirrored:
            return .rightMirrored

        @unknown default:
            return .up
        }
    }
}
