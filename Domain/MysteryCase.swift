import Foundation

struct MysteryCase: Identifiable, Codable, Equatable {
    let id: UUID
    let title: String
    let openingIncident: String
    let victim: MysteryPerson
    let suspects: [MysteryPerson]
    let roomObjects: [RoomObject]
    let clues: [MysteryClue]
    let solution: MysterySolution

    init(
        id: UUID = UUID(),
        title: String,
        openingIncident: String,
        victim: MysteryPerson,
        suspects: [MysteryPerson],
        roomObjects: [RoomObject],
        clues: [MysteryClue],
        solution: MysterySolution
    ) {
        self.id = id
        self.title = title
        self.openingIncident = openingIncident
        self.victim = victim
        self.suspects = suspects
        self.roomObjects = roomObjects
        self.clues = clues
        self.solution = solution
    }
}
