

import Foundation

struct RoomObject: Identifiable, Codable, Equatable {
    let id: UUID
    var name: String
    var isConfirmed: Bool

    init(
        id: UUID = UUID(),
        name: String,
        isConfirmed: Bool = false
    ) {
        self.id = id
        self.name = name
        self.isConfirmed = isConfirmed
    }
}
