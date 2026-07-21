import Foundation

enum MysteryClueKind: String, Codable {
    case evidence
    case redHerring
}

struct MysteryClue: Identifiable, Codable, Equatable {
    let id: UUID
    let title: String
    let detail: String
    let roomObjectID: UUID
    let kind: MysteryClueKind
    let deductions: [MysteryDeduction]

    init(
        id: UUID = UUID(),
        title: String,
        detail: String,
        roomObjectID: UUID,
        kind: MysteryClueKind,
        deductions: [MysteryDeduction]
    ) {
        self.id = id
        self.title = title
        self.detail = detail
        self.roomObjectID = roomObjectID
        self.kind = kind
        self.deductions = deductions
    }
}
