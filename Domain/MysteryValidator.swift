import Foundation
struct MysteryValidator {
    func validate(_ mystery: MysteryCase) -> [MysteryValidationIssue] {
        var issues: [MysteryValidationIssue] = []

        if mystery.suspects.count != 3 {
            issues.append(.invalidSuspectCount)
        }

        if mystery.roomObjects.count != 4 {
            issues.append(.invalidRoomObjectCount)
        }

        if mystery.clues.count != 5 {
            issues.append(.invalidClueCount)
        }

        let redHerringCount = mystery.clues.filter {
            $0.kind == .redHerring
        }.count

        if redHerringCount != 1 {
            issues.append(.invalidRedHerringCount)
        }
        
        let killerExists = mystery.suspects.contains {
            $0.id == mystery.solution.killerID
        }

        if !killerExists {
            issues.append(.killerIsNotASuspect)
        }
        
        let roomObjectIDs = Set(mystery.roomObjects.map(\.id))

        let hasUnknownRoomObject = mystery.clues.contains { clue in
            !roomObjectIDs.contains(clue.roomObjectID)
        }

        if hasUnknownRoomObject {
            issues.append(.clueReferencesUnknownRoomObject)
        }
        
        let suspectIDs = Set(mystery.suspects.map(\.id))

        let hasUnknownSuspectReference = mystery.clues
            .flatMap(\.deductions)
            .contains { deduction in
                guard let suspectID = deduction.relatedSuspectID else {
                    return false
                }

                return !suspectIDs.contains(suspectID)
            }

        if hasUnknownSuspectReference {
            issues.append(.deductionReferencesUnknownSuspect)
        }

        let redHerringHasDeduction = mystery.clues.contains { clue in
            clue.kind == .redHerring && !clue.deductions.isEmpty
        }

        if redHerringHasDeduction {
            issues.append(.redHerringContainsDeduction)
        }
        
        let deductions = mystery.clues.flatMap(\.deductions)

        let eliminatedSuspectIDs: Set<UUID> = Set(
            deductions.compactMap { deduction  -> UUID? in
                guard deduction.kind == .eliminatesSuspect else {
                    return nil
                }

                return deduction.relatedSuspectID
            }
        )

        if eliminatedSuspectIDs.contains(mystery.solution.killerID) {
            issues.append(.killerIsEliminated)
        }

        let innocentSuspects = mystery.suspects.filter {
            $0.id != mystery.solution.killerID
        }

        let hasUneliminatedInnocentSuspect = innocentSuspects.contains {
            !eliminatedSuspectIDs.contains($0.id)
        }

        if hasUneliminatedInnocentSuspect {
            issues.append(.innocentSuspectCannotBeEliminated)
        }
        
        let supportsKiller = deductions.contains { deduction in
            deduction.kind == .supportsSuspect &&
            deduction.relatedSuspectID == mystery.solution.killerID
        }

        if !supportsKiller {
            issues.append(.missingKillerSupport)
        }

        let establishesMethod = deductions.contains {
            $0.kind == .establishesMethod
        }

        if !establishesMethod {
            issues.append(.missingMethodEvidence)
        }

        let establishesTimeline = deductions.contains {
            $0.kind == .establishesTimeline
        }

        if !establishesTimeline {
            issues.append(.missingTimelineEvidence)
        }

        let establishesOpportunity = deductions.contains {
            $0.kind == .establishesOpportunity
        }

        if !establishesOpportunity {
            issues.append(.missingOpportunityEvidence)
        }
        
        let hasContradiction = deductions.contains { deduction in
            deduction.kind == .contradictsStatement &&
            deduction.relatedSuspectID != nil
        }

        if !hasContradiction {
            issues.append(.missingContradiction)
        }

        return issues
    }
}
