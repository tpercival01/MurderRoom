import Foundation

enum MysteryPersonRole: String, Codable {
    case victim
    case suspect

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        let value = try container.decode(String.self)

        guard let role = Self(
            rawValue: value.lowercased()
        ) else {
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Unknown mystery person role: \(value)"
            )
        }

        self = role
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(rawValue)
    }
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
