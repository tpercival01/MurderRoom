import Foundation

enum InvestigationStateError: Error, Equatable {
    case mysteryMismatch
    case clueNotInMystery
    case investigationClosed
    case notAllCluesRevealed
}

struct InvestigationState: Equatable {
    let mysteryID: UUID

    private(set) var revealedClueIDs: Set<UUID>
    private(set) var accusedSuspectID: UUID?
    private(set) var resolution: MysteryResolution?
    private(set) var suspectAssessments: [UUID: SuspectAssessment]

    init(mysteryID: UUID) {
        self.mysteryID = mysteryID
        self.revealedClueIDs = []
        self.accusedSuspectID = nil
        self.resolution = nil
        self.suspectAssessments = [:]
    }

    var isResolved: Bool {
        resolution != nil
    }

    mutating func reveal(
        clueID: UUID,
        in mystery: MysteryCase
    ) throws {
        guard mystery.id == mysteryID else {
            throw InvestigationStateError.mysteryMismatch
        }

        guard !isResolved else {
            throw InvestigationStateError.investigationClosed
        }

        guard mystery.clues.contains(
            where: { $0.id == clueID }
        ) else {
            throw InvestigationStateError.clueNotInMystery
        }

        revealedClueIDs.insert(clueID)
    }

    mutating func accuse(
        suspectID: UUID,
        in mystery: MysteryCase
    ) throws {
        guard mystery.id == mysteryID else {
            throw InvestigationStateError.mysteryMismatch
        }

        guard !isResolved else {
            throw InvestigationStateError.investigationClosed
        }

        let requiredClueIDs = Set(
            mystery.clues.map(\.id)
        )

        guard revealedClueIDs == requiredClueIDs else {
            throw InvestigationStateError
                .notAllCluesRevealed
        }

        let result = try MysteryResolver().resolve(
            accusedSuspectID: suspectID,
            in: mystery
        )

        accusedSuspectID = suspectID
        resolution = result
    }
    
    mutating func assess(
        suspectID: UUID,
        as assessment: SuspectAssessment,
        in mystery: MysteryCase
    ) throws {
        guard mystery.id == mysteryID else {
            throw InvestigationStateError.mysteryMismatch
        }

        guard !isResolved else {
            throw InvestigationStateError.investigationClosed
        }

        guard mystery.suspects.contains(
            where: { $0.id == suspectID }
        ) else {
            throw MysteryResolutionError.accusedPersonIsNotASuspect
        }

        suspectAssessments[suspectID] = assessment
    }
}
