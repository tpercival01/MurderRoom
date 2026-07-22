import Foundation

enum InvestigationStateError: Error, Equatable {
    case mysteryMismatch
    case clueNotInMystery
    case investigationClosed
    case notAllCluesRevealed
    case noContradictionMarked
    case clueNotRevealed
    case suspectNotInMystery
}

struct InvestigationState: Equatable {
    let mysteryID: UUID

    private(set) var revealedClueIDs: Set<UUID>
    private(set) var accusedSuspectID: UUID?
    private(set) var resolution: MysteryResolution?
    private(set) var suspectAssessments: [UUID: SuspectAssessment]
    private(set) var contradictionClaims: [UUID: UUID]

    init(mysteryID: UUID) {
        self.mysteryID = mysteryID
        self.revealedClueIDs = []
        self.accusedSuspectID = nil
        self.resolution = nil
        self.suspectAssessments = [:]
        self.contradictionClaims = [:]
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
    mutating func markContradiction(
        clueID: UUID,
        suspectID: UUID,
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

        guard revealedClueIDs.contains(clueID) else {
            throw InvestigationStateError.clueNotRevealed
        }

        guard mystery.suspects.contains(
            where: { $0.id == suspectID }
        ) else {
            throw InvestigationStateError.suspectNotInMystery
        }

        contradictionClaims[clueID] = suspectID
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
        
        guard !contradictionClaims.isEmpty else {
            throw InvestigationStateError.noContradictionMarked
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
