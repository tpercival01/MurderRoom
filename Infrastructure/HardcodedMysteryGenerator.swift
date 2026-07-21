import Foundation

enum HardcodedMysteryGeneratorError: Error, Equatable {
    case requiresExactlyFourRoomObjects
    case containsUnconfirmedRoomObject
}

struct HardcodedMysteryGenerator: MysteryGenerating {
    func generate(
        from roomObjects: [RoomObject]
    ) async throws -> MysteryCase {
        guard roomObjects.count == 4 else {
            throw HardcodedMysteryGeneratorError
                .requiresExactlyFourRoomObjects
        }

        guard roomObjects.allSatisfy(\.isConfirmed) else {
            throw HardcodedMysteryGeneratorError
                .containsUnconfirmedRoomObject
        }

        let victim = MysteryPerson(
            name: "Eleanor Vale",
            role: .victim
        )

        let killer = MysteryPerson(
            name: "Marcus Flint",
            role: .suspect,
            relationshipToVictim: "Eleanor's business manager",
            statement: """
            Eleanor seemed perfectly well when I left her. I never touched \
            anything she used for her final drink.
            """,
            alibiClaim: """
            Marcus claims he was reviewing accounts alone at 11:45 PM.
            """
        )

        let firstInnocentSuspect = MysteryPerson(
            name: "Clara Reed",
            role: .suspect,
            relationshipToVictim: "Eleanor's estranged niece",
            statement: """
            We argued earlier, but I left before Eleanor poured her final drink.
            """,
            alibiClaim: """
            Clara claims she left the room shortly before 11:30 PM.
            """
        )

        let secondInnocentSuspect = MysteryPerson(
            name: "Jonah Webb",
            role: .suspect,
            relationshipToVictim: "Eleanor's neighbour",
            statement: """
            I remained near the doorway. Everyone could see where I was.
            """,
            alibiClaim: """
            Jonah claims he never approached Eleanor's side of the room.
            """
        )

        let suspects = [
            killer,
            firstInnocentSuspect,
            secondInnocentSuspect
        ]

        let clues = [
            MysteryClue(
                title: "Trace on the \(roomObjects[0].name)",
                detail: """
                A bitter residue was found on the \
                \(roomObjects[0].name). Marcus had access to the \
                same rare compound earlier that evening.
                """,
                roomObjectID: roomObjects[0].id,
                kind: .evidence,
                deductions: [
                    MysteryDeduction(
                        kind: .supportsSuspect,
                        relatedSuspectID: killer.id
                    ),
                    MysteryDeduction(
                        kind: .establishesMethod
                    ),
                    MysteryDeduction(
                        kind: .contradictsStatement,
                        relatedSuspectID: killer.id
                    )
                ]
            ),

            MysteryClue(
                title: "Message near the \(roomObjects[1].name)",
                detail: """
                A concealed message proves Clara had already left \
                before the poison was administered.
                """,
                roomObjectID: roomObjects[1].id,
                kind: .evidence,
                deductions: [
                    MysteryDeduction(
                        kind: .eliminatesSuspect,
                        relatedSuspectID: firstInnocentSuspect.id
                    )
                ]
            ),

            MysteryClue(
                title: "Marks beside the \(roomObjects[2].name)",
                detail: """
                The marks show Jonah could not have approached the \
                victim without being seen.
                """,
                roomObjectID: roomObjects[2].id,
                kind: .evidence,
                deductions: [
                    MysteryDeduction(
                        kind: .eliminatesSuspect,
                        relatedSuspectID: secondInnocentSuspect.id
                    ),
                    MysteryDeduction(
                        kind: .establishesOpportunity,
                        relatedSuspectID: killer.id
                    )
                ]
            ),

            MysteryClue(
                title: "Timing from the \(roomObjects[3].name)",
                detail: """
                The \(roomObjects[3].name) establishes that the \
                poisoning occurred at 11:45 PM.
                """,
                roomObjectID: roomObjects[3].id,
                kind: .evidence,
                deductions: [
                    MysteryDeduction(
                        kind: .establishesTimeline
                    )
                ]
            ),

            MysteryClue(
                title: "The suspicious thread",
                detail: """
                A loose thread near the \(roomObjects[2].name) appears \
                suspicious, but belongs to an old damaged curtain.
                """,
                roomObjectID: roomObjects[2].id,
                kind: .redHerring,
                deductions: []
            )
        ]

        return MysteryCase(
            title: "The Last Toast",
            openingIncident: """
            Eleanor Vale was found dead shortly before midnight. \
            Someone in the room poisoned her final drink.
            """,
            victim: victim,
            suspects: suspects,
            roomObjects: roomObjects,
            clues: clues,
            solution: MysterySolution(
                killerID: killer.id,
                motive: "Eleanor had discovered Marcus was stealing from her.",
                method: """
                Marcus placed a slow-acting poison on the object \
                Eleanor used for her final drink.
                """,
                timeOfDeath: "11:45 PM",
                opportunity: """
                Marcus was the only suspect close enough to prepare \
                the poison after Clara left and while Jonah was visible.
                """
            )
        )
    }
}
