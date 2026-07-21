import Testing
import Foundation
@testable import MurderRoom

struct MurderRoomTests {
    @Test
    func rejectsKillerWhoIsNotASuspect() {
        let victim = MysteryPerson(
            name: "Eleanor Vale",
            role: .victim
        )

        let suspects = [
            MysteryPerson(name: "Marcus Flint", role: .suspect),
            MysteryPerson(name: "Clara Reed", role: .suspect),
            MysteryPerson(name: "Jonah Webb", role: .suspect)
        ]

        let roomObjects = [
            RoomObject(name: "Coffee Mug", isConfirmed: true),
            RoomObject(name: "Lamp", isConfirmed: true),
            RoomObject(name: "Chair", isConfirmed: true),
            RoomObject(name: "Clock", isConfirmed: true)
        ]

        let clues = [
            MysteryClue(
                title: "Residue",
                detail: "A bitter residue marks the mug.",
                roomObjectID: roomObjects[0].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Hidden Mark",
                detail: "Writing appears beneath the lamp.",
                roomObjectID: roomObjects[1].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Moved Chair",
                detail: "The chair has recently been moved.",
                roomObjectID: roomObjects[2].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Stopped Clock",
                detail: "The clock stopped shortly before midnight.",
                roomObjectID: roomObjects[3].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Red Thread",
                detail: "A thread appears important but proves nothing.",
                roomObjectID: roomObjects[2].id,
                kind: .redHerring,
                deductions: []
            )
        ]

        let mystery = MysteryCase(
            title: "The Midnight Cup",
            openingIncident: "Eleanor Vale was found dead after midnight.",
            victim: victim,
            suspects: suspects,
            roomObjects: roomObjects,
            clues: clues,
            solution: MysterySolution(
                killerID: UUID(),
                motive: "Revenge",
                method: "Poison",
                timeOfDeath: "11:45 PM",
                opportunity: "The killer was alone with the victim."
            )
        )

        let issues = MysteryValidator().validate(mystery)

        #expect(issues.contains(.killerIsNotASuspect))
    }
    
    @Test
    func rejectsClueLinkedToUnknownRoomObject() {
        let victim = MysteryPerson(
            name: "Eleanor Vale",
            role: .victim
        )

        let suspects = [
            MysteryPerson(name: "Marcus Flint", role: .suspect),
            MysteryPerson(name: "Clara Reed", role: .suspect),
            MysteryPerson(name: "Jonah Webb", role: .suspect)
        ]

        let roomObjects = [
            RoomObject(name: "Coffee Mug", isConfirmed: true),
            RoomObject(name: "Lamp", isConfirmed: true),
            RoomObject(name: "Chair", isConfirmed: true),
            RoomObject(name: "Clock", isConfirmed: true)
        ]

        let clues = [
            MysteryClue(
                title: "Residue",
                detail: "A bitter residue marks the mug.",
                roomObjectID: UUID(),
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Hidden Mark",
                detail: "Writing appears beneath the lamp.",
                roomObjectID: roomObjects[1].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Moved Chair",
                detail: "The chair has recently been moved.",
                roomObjectID: roomObjects[2].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Stopped Clock",
                detail: "The clock stopped shortly before midnight.",
                roomObjectID: roomObjects[3].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Red Thread",
                detail: "A thread appears important but proves nothing.",
                roomObjectID: roomObjects[2].id,
                kind: .redHerring,
                deductions: []
            )
        ]

        let mystery = MysteryCase(
            title: "The Midnight Cup",
            openingIncident: "Eleanor Vale was found dead after midnight.",
            victim: victim,
            suspects: suspects,
            roomObjects: roomObjects,
            clues: clues,
            solution: MysterySolution(
                killerID: suspects[0].id,
                motive: "Revenge",
                method: "Poison",
                timeOfDeath: "11:45 PM",
                opportunity: "Marcus was alone with the victim."
            )
        )

        let issues = MysteryValidator().validate(mystery)

        #expect(issues.contains(.clueReferencesUnknownRoomObject))
    }
    
    @Test
    func rejectsDeductionLinkedToUnknownSuspect() {
        let victim = MysteryPerson(
            name: "Eleanor Vale",
            role: .victim
        )

        let suspects = [
            MysteryPerson(name: "Marcus Flint", role: .suspect),
            MysteryPerson(name: "Clara Reed", role: .suspect),
            MysteryPerson(name: "Jonah Webb", role: .suspect)
        ]

        let roomObjects = [
            RoomObject(name: "Coffee Mug", isConfirmed: true),
            RoomObject(name: "Lamp", isConfirmed: true),
            RoomObject(name: "Chair", isConfirmed: true),
            RoomObject(name: "Clock", isConfirmed: true)
        ]

        let clues = [
            MysteryClue(
                title: "Residue",
                detail: "A bitter residue marks the mug.",
                roomObjectID: roomObjects[0].id,
                kind: .evidence,
                deductions: [
                    MysteryDeduction(
                        kind: .supportsSuspect,
                        relatedSuspectID: UUID()
                    )
                ]
            ),
            MysteryClue(
                title: "Hidden Mark",
                detail: "Writing appears beneath the lamp.",
                roomObjectID: roomObjects[1].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Moved Chair",
                detail: "The chair has recently been moved.",
                roomObjectID: roomObjects[2].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Stopped Clock",
                detail: "The clock stopped shortly before midnight.",
                roomObjectID: roomObjects[3].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Red Thread",
                detail: "A thread appears important but proves nothing.",
                roomObjectID: roomObjects[2].id,
                kind: .redHerring,
                deductions: []
            )
        ]

        let mystery = MysteryCase(
            title: "The Midnight Cup",
            openingIncident: "Eleanor Vale was found dead after midnight.",
            victim: victim,
            suspects: suspects,
            roomObjects: roomObjects,
            clues: clues,
            solution: MysterySolution(
                killerID: suspects[0].id,
                motive: "Revenge",
                method: "Poison",
                timeOfDeath: "11:45 PM",
                opportunity: "Marcus was alone with the victim."
            )
        )

        let issues = MysteryValidator().validate(mystery)

        #expect(issues.contains(.deductionReferencesUnknownSuspect))
    }
    
    @Test
    func rejectsRedHerringContainingDeduction() {
        let victim = MysteryPerson(
            name: "Eleanor Vale",
            role: .victim
        )

        let suspects = [
            MysteryPerson(name: "Marcus Flint", role: .suspect),
            MysteryPerson(name: "Clara Reed", role: .suspect),
            MysteryPerson(name: "Jonah Webb", role: .suspect)
        ]

        let roomObjects = [
            RoomObject(name: "Coffee Mug", isConfirmed: true),
            RoomObject(name: "Lamp", isConfirmed: true),
            RoomObject(name: "Chair", isConfirmed: true),
            RoomObject(name: "Clock", isConfirmed: true)
        ]

        let clues = [
            MysteryClue(
                title: "Residue",
                detail: "A bitter residue marks the mug.",
                roomObjectID: roomObjects[0].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Hidden Mark",
                detail: "Writing appears beneath the lamp.",
                roomObjectID: roomObjects[1].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Moved Chair",
                detail: "The chair has recently been moved.",
                roomObjectID: roomObjects[2].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Stopped Clock",
                detail: "The clock stopped shortly before midnight.",
                roomObjectID: roomObjects[3].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Red Thread",
                detail: "A thread appears important but proves nothing.",
                roomObjectID: roomObjects[2].id,
                kind: .redHerring,
                deductions: [
                    MysteryDeduction(
                        kind: .eliminatesSuspect,
                        relatedSuspectID: suspects[1].id
                    )
                ]
            )
        ]

        let mystery = MysteryCase(
            title: "The Midnight Cup",
            openingIncident: "Eleanor Vale was found dead after midnight.",
            victim: victim,
            suspects: suspects,
            roomObjects: roomObjects,
            clues: clues,
            solution: MysterySolution(
                killerID: suspects[0].id,
                motive: "Revenge",
                method: "Poison",
                timeOfDeath: "11:45 PM",
                opportunity: "Marcus was alone with the victim."
            )
        )

        let issues = MysteryValidator().validate(mystery)

        #expect(issues.contains(.redHerringContainsDeduction))
    }
    
    @Test
    func rejectsMysteryWhereKillerIsEliminated() {
        let victim = MysteryPerson(
            name: "Eleanor Vale",
            role: .victim
        )

        let suspects = [
            MysteryPerson(name: "Marcus Flint", role: .suspect),
            MysteryPerson(name: "Clara Reed", role: .suspect),
            MysteryPerson(name: "Jonah Webb", role: .suspect)
        ]

        let roomObjects = [
            RoomObject(name: "Coffee Mug", isConfirmed: true),
            RoomObject(name: "Lamp", isConfirmed: true),
            RoomObject(name: "Chair", isConfirmed: true),
            RoomObject(name: "Clock", isConfirmed: true)
        ]

        let clues = [
            MysteryClue(
                title: "Residue",
                detail: "A bitter residue marks the mug.",
                roomObjectID: roomObjects[0].id,
                kind: .evidence,
                deductions: [
                    MysteryDeduction(
                        kind: .eliminatesSuspect,
                        relatedSuspectID: suspects[0].id
                    )
                ]
            ),
            MysteryClue(
                title: "Hidden Mark",
                detail: "Writing appears beneath the lamp.",
                roomObjectID: roomObjects[1].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Moved Chair",
                detail: "The chair has recently been moved.",
                roomObjectID: roomObjects[2].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Stopped Clock",
                detail: "The clock stopped shortly before midnight.",
                roomObjectID: roomObjects[3].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Red Thread",
                detail: "A thread appears important but proves nothing.",
                roomObjectID: roomObjects[2].id,
                kind: .redHerring,
                deductions: []
            )
        ]

        let mystery = MysteryCase(
            title: "The Midnight Cup",
            openingIncident: "Eleanor Vale was found dead after midnight.",
            victim: victim,
            suspects: suspects,
            roomObjects: roomObjects,
            clues: clues,
            solution: MysterySolution(
                killerID: suspects[0].id,
                motive: "Revenge",
                method: "Poison",
                timeOfDeath: "11:45 PM",
                opportunity: "Marcus was alone with the victim."
            )
        )

        let issues = MysteryValidator().validate(mystery)

        #expect(issues.contains(.killerIsEliminated))
    }
    
    @Test
    func rejectsMysteryWithUneliminatedInnocentSuspect() {
        let victim = MysteryPerson(
            name: "Eleanor Vale",
            role: .victim
        )

        let suspects = [
            MysteryPerson(name: "Marcus Flint", role: .suspect),
            MysteryPerson(name: "Clara Reed", role: .suspect),
            MysteryPerson(name: "Jonah Webb", role: .suspect)
        ]

        let roomObjects = [
            RoomObject(name: "Coffee Mug", isConfirmed: true),
            RoomObject(name: "Lamp", isConfirmed: true),
            RoomObject(name: "Chair", isConfirmed: true),
            RoomObject(name: "Clock", isConfirmed: true)
        ]

        let clues = [
            MysteryClue(
                title: "Residue",
                detail: "A bitter residue marks the mug.",
                roomObjectID: roomObjects[0].id,
                kind: .evidence,
                deductions: [
                    MysteryDeduction(
                        kind: .eliminatesSuspect,
                        relatedSuspectID: suspects[1].id
                    )
                ]
            ),
            MysteryClue(
                title: "Hidden Mark",
                detail: "Writing appears beneath the lamp.",
                roomObjectID: roomObjects[1].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Moved Chair",
                detail: "The chair has recently been moved.",
                roomObjectID: roomObjects[2].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Stopped Clock",
                detail: "The clock stopped shortly before midnight.",
                roomObjectID: roomObjects[3].id,
                kind: .evidence,
                deductions: []
            ),
            MysteryClue(
                title: "Red Thread",
                detail: "A thread appears important but proves nothing.",
                roomObjectID: roomObjects[2].id,
                kind: .redHerring,
                deductions: []
            )
        ]

        let mystery = MysteryCase(
            title: "The Midnight Cup",
            openingIncident: "Eleanor Vale was found dead after midnight.",
            victim: victim,
            suspects: suspects,
            roomObjects: roomObjects,
            clues: clues,
            solution: MysterySolution(
                killerID: suspects[0].id,
                motive: "Revenge",
                method: "Poison",
                timeOfDeath: "11:45 PM",
                opportunity: "Marcus was alone with the victim."
            )
        )

        let issues = MysteryValidator().validate(mystery)

        #expect(issues.contains(.innocentSuspectCannotBeEliminated))
    }
    
    @Test
    func hardcodedGeneratorProducesValidMystery() async throws {
        let roomObjects = [
            RoomObject(name: "Coffee Mug", isConfirmed: true),
            RoomObject(name: "Floor Lamp", isConfirmed: true),
            RoomObject(name: "Armchair", isConfirmed: true),
            RoomObject(name: "Wall Clock", isConfirmed: true)
        ]

        let generator = HardcodedMysteryGenerator()

        let mystery = try await generator.generate(
            from: roomObjects
        )

        let issues = MysteryValidator().validate(mystery)

        #expect(issues.isEmpty)
        #expect(mystery.roomObjects == roomObjects)
        #expect(mystery.suspects.count == 3)
        #expect(mystery.clues.count == 5)
    }
    
    @Test
    func resolvesCorrectAccusation() async throws {
        let roomObjects = [
            RoomObject(name: "Coffee Mug", isConfirmed: true),
            RoomObject(name: "Floor Lamp", isConfirmed: true),
            RoomObject(name: "Armchair", isConfirmed: true),
            RoomObject(name: "Wall Clock", isConfirmed: true)
        ]

        let mystery = try await HardcodedMysteryGenerator()
            .generate(from: roomObjects)

        let result = try MysteryResolver().resolve(
            accusedSuspectID: mystery.solution.killerID,
            in: mystery
        )

        #expect(result.isCorrect)
        #expect(result.killer.id == mystery.solution.killerID)
        #expect(
            result.reconstruction.motive ==
            mystery.solution.motive
        )
    }

    @Test
    func resolvesIncorrectAccusationAndRevealsTruth() async throws {
        let roomObjects = [
            RoomObject(name: "Coffee Mug", isConfirmed: true),
            RoomObject(name: "Floor Lamp", isConfirmed: true),
            RoomObject(name: "Armchair", isConfirmed: true),
            RoomObject(name: "Wall Clock", isConfirmed: true)
        ]

        let mystery = try await HardcodedMysteryGenerator()
            .generate(from: roomObjects)

        let innocentSuspect = try #require(
            mystery.suspects.first {
                $0.id != mystery.solution.killerID
            }
        )

        let result = try MysteryResolver().resolve(
            accusedSuspectID: innocentSuspect.id,
            in: mystery
        )

        #expect(!result.isCorrect)
        #expect(result.killer.id == mystery.solution.killerID)
        #expect(
            result.reconstruction.method ==
            mystery.solution.method
        )
    }
    
    @Test
    func rejectsMysteryMissingRequiredEvidenceCoverage() async throws {
        let roomObjects = [
            RoomObject(name: "Coffee Mug", isConfirmed: true),
            RoomObject(name: "Floor Lamp", isConfirmed: true),
            RoomObject(name: "Armchair", isConfirmed: true),
            RoomObject(name: "Wall Clock", isConfirmed: true)
        ]

        let mystery = try await HardcodedMysteryGenerator()
            .generate(from: roomObjects)

        let strippedClues = mystery.clues.map { clue in
            let remainingDeductions = clue.deductions.filter { deduction in
                switch deduction.kind {
                case .eliminatesSuspect:
                    return true

                case .supportsSuspect,
                     .establishesMethod,
                     .establishesTimeline,
                     .contradictsStatement,
                     .establishesOpportunity:
                    return false
                }
            }

            return MysteryClue(
                id: clue.id,
                title: clue.title,
                detail: clue.detail,
                roomObjectID: clue.roomObjectID,
                kind: clue.kind,
                deductions: remainingDeductions
            )
        }

        let brokenMystery = MysteryCase(
            id: mystery.id,
            title: mystery.title,
            openingIncident: mystery.openingIncident,
            victim: mystery.victim,
            suspects: mystery.suspects,
            roomObjects: mystery.roomObjects,
            clues: strippedClues,
            solution: mystery.solution
        )

        let issues = MysteryValidator().validate(brokenMystery)

        #expect(issues.contains(.missingKillerSupport))
        #expect(issues.contains(.missingMethodEvidence))
        #expect(issues.contains(.missingTimelineEvidence))
        #expect(issues.contains(.missingOpportunityEvidence))
    }
    
    @Test
    func preventsAccusationBeforeAllCluesAreRevealed() async throws {
        let roomObjects = [
            RoomObject(name: "Coffee Mug", isConfirmed: true),
            RoomObject(name: "Floor Lamp", isConfirmed: true),
            RoomObject(name: "Armchair", isConfirmed: true),
            RoomObject(name: "Wall Clock", isConfirmed: true)
        ]

        let mystery = try await HardcodedMysteryGenerator()
            .generate(from: roomObjects)

        var investigation = InvestigationState(
            mysteryID: mystery.id
        )

        do {
            try investigation.accuse(
                suspectID: mystery.suspects[0].id,
                in: mystery
            )

            Issue.record(
                "The accusation should have been rejected."
            )
        } catch let error as InvestigationStateError {
            #expect(error == .notAllCluesRevealed)
        }
    }

    @Test
    func resolvesInvestigationAfterAllCluesAreRevealed() async throws {
        let roomObjects = [
            RoomObject(name: "Coffee Mug", isConfirmed: true),
            RoomObject(name: "Floor Lamp", isConfirmed: true),
            RoomObject(name: "Armchair", isConfirmed: true),
            RoomObject(name: "Wall Clock", isConfirmed: true)
        ]

        let mystery = try await HardcodedMysteryGenerator()
            .generate(from: roomObjects)

        var investigation = InvestigationState(
            mysteryID: mystery.id
        )

        for clue in mystery.clues {
            try investigation.reveal(
                clueID: clue.id,
                in: mystery
            )
        }

        try investigation.accuse(
            suspectID: mystery.solution.killerID,
            in: mystery
        )

        #expect(investigation.isResolved)
        #expect(
            investigation.revealedClueIDs.count ==
            mystery.clues.count
        )
        #expect(investigation.resolution?.isCorrect == true)
    }
}
