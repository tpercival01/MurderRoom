import Foundation

enum MysteryPersonRole: String, Codable {
    case victim
    case suspect
}

struct MysteryPerson: Identifiable, Codable, Equatable {
    let id: UUID
    let name: String
    let role: MysteryPersonRole
    let relationshipToVictim: String
    let statement: String
    let alibiClaim: String

    init(
        id: UUID = UUID(),
        name: String,
        role: MysteryPersonRole,
        relationshipToVictim: String = "",
        statement: String = "",
        alibiClaim: String = ""
    ) {
        self.id = id
        self.name = name
        self.role = role
        self.relationshipToVictim = relationshipToVictim
        self.statement = statement
        self.alibiClaim = alibiClaim
    }
}
