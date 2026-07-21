import Foundation

struct MysteryReconstruction: Equatable {
    let killerName: String
    let motive: String
    let method: String
    let timeOfDeath: String
    let opportunity: String
}

struct MysteryResolution: Equatable {
    let accusedSuspectID: UUID
    let isCorrect: Bool
    let killer: MysteryPerson
    let reconstruction: MysteryReconstruction
}

enum MysteryResolutionError: Error, Equatable {
    case accusedPersonIsNotASuspect
    case killerMissingFromSuspects
}

struct MysteryResolver {
    func resolve(
        accusedSuspectID: UUID,
        in mystery: MysteryCase
    ) throws -> MysteryResolution {
        guard mystery.suspects.contains(
            where: { $0.id == accusedSuspectID }
        ) else {
            throw MysteryResolutionError
                .accusedPersonIsNotASuspect
        }

        guard let killer = mystery.suspects.first(
            where: { $0.id == mystery.solution.killerID }
        ) else {
            throw MysteryResolutionError
                .killerMissingFromSuspects
        }

        return MysteryResolution(
            accusedSuspectID: accusedSuspectID,
            isCorrect: accusedSuspectID == killer.id,
            killer: killer,
            reconstruction: MysteryReconstruction(
                killerName: killer.name,
                motive: mystery.solution.motive,
                method: mystery.solution.method,
                timeOfDeath: mystery.solution.timeOfDeath,
                opportunity: mystery.solution.opportunity
            )
        )
    }
}
