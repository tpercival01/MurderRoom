import Foundation

struct MysterySolution: Codable, Equatable {
    let killerID: UUID
    let motive: String
    let method: String
    let timeOfDeath: String
    let opportunity: String
}
