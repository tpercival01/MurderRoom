import CoreGraphics
import Foundation

struct RoomObjectHotspot: Identifiable, Equatable {
    let objectName: String
    let x: CGFloat
    let y: CGFloat

    var id: String {
        objectName
            .trimmingCharacters(
                in: .whitespacesAndNewlines
            )
            .lowercased()
    }

    var normalisedPoint: CGPoint {
        CGPoint(x: x, y: y)
    }
}
