import Foundation

struct MysteryReconstructionStep: Identifiable, Equatable {
    let id: UUID
    let clueTitle: String
    let clueDetail: String
    let roomObjectName: String
    let findings: [String]
    let isRedHerring: Bool
}

struct MysteryReconstruction: Equatable {
    let killerName: String
    let motive: String
    let method: String
    let timeOfDeath: String
    let opportunity: String
    let steps: [MysteryReconstructionStep]
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
        
        let reconstructionSteps = mystery.clues.map { clue in
            let roomObjectName = mystery.roomObjects.first {
                $0.id == clue.roomObjectID
            }?.name ?? "Unknown object"

            let findings: [String]

            if clue.kind == .redHerring {
                findings = [
                    "This was a red herring and did not affect the solution."
                ]
            } else {
                findings = clue.deductions.map { deduction in
                    findingDescription(
                        for: deduction,
                        in: mystery
                    )
                }
            }

            return MysteryReconstructionStep(
                id: clue.id,
                clueTitle: clue.title,
                clueDetail: clue.detail,
                roomObjectName: roomObjectName,
                findings: findings,
                isRedHerring: clue.kind == .redHerring
            )
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
                opportunity: mystery.solution.opportunity,
                steps: reconstructionSteps,
            )
        )
    }
    private func findingDescription(
        for deduction: MysteryDeduction,
        in mystery: MysteryCase
    ) -> String {
        let suspectName = deduction.relatedSuspectID.flatMap {
            suspectID in

            mystery.suspects.first {
                $0.id == suspectID
            }?.name
        }

        switch deduction.kind {
        case .eliminatesSuspect:
            return "Eliminates \(suspectName ?? "a suspect")."

        case .supportsSuspect:
            return "Supports the case against \(suspectName ?? "a suspect")."

        case .establishesMethod:
            return "Establishes how the murder was committed."

        case .establishesTimeline:
            return "Establishes when the murder occurred."

        case .establishesOpportunity:
            return "Establishes who had the opportunity."

        case .contradictsStatement:
            return "Contradicts \(suspectName ?? "a suspect")'s statement."
        }
    }
}
