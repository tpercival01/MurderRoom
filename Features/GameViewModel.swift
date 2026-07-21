import Combine
import Foundation

@MainActor
final class GameViewModel: ObservableObject {
    @Published var objectNames = [
        "Coffee Mug",
        "Floor Lamp",
        "Armchair",
        "Wall Clock"
    ]

    @Published private(set) var mystery: MysteryCase?
    @Published private(set) var investigation: InvestigationState?
    @Published private(set) var isGenerating = false
    @Published private(set) var errorMessage: String?

    @Published var selectedSuspectID: UUID?

    private let generator: any MysteryGenerating

    init(
        generator: any MysteryGenerating = HardcodedMysteryGenerator()
    ) {
        self.generator = generator
    }

    var canGenerate: Bool {
        objectNames.count == 4 &&
        objectNames.allSatisfy {
            !$0.trimmingCharacters(
                in: .whitespacesAndNewlines
            ).isEmpty
        }
    }

    var canAccuse: Bool {
        guard
            let mystery = mystery,
            let investigation = investigation
        else {
            return false
        }

        return selectedSuspectID != nil &&
            investigation.revealedClueIDs.count ==
            mystery.clues.count &&
            !investigation.isResolved
    }

    func generateMystery() async {
        guard canGenerate else {
            errorMessage = "Enter four room objects."
            return
        }

        isGenerating = true
        errorMessage = nil

        defer {
            isGenerating = false
        }

        let roomObjects = objectNames.map { name in
            RoomObject(
                name: name.trimmingCharacters(
                    in: .whitespacesAndNewlines
                ),
                isConfirmed: true
            )
        }

        do {
            let candidate = try await generator.generate(
                from: roomObjects
            )

            let issues = MysteryValidator().validate(candidate)

            guard issues.isEmpty else {
                errorMessage = """
                Mystery validation failed: \
                \(issues.map(\.rawValue).joined(separator: ", "))
                """
                return
            }

            mystery = candidate
            investigation = InvestigationState(
                mysteryID: candidate.id
            )
        } catch {
            errorMessage = "Mystery generation failed."
        }
    }

    func isRevealed(_ clue: MysteryClue) -> Bool {
        investigation?.revealedClueIDs.contains(clue.id) == true
    }

    func reveal(_ clue: MysteryClue) {
        guard
            let mystery = mystery,
            var currentInvestigation = investigation
        else {
            return
        }

        do {
            try currentInvestigation.reveal(
                clueID: clue.id,
                in: mystery
            )

            investigation = currentInvestigation
        } catch {
            errorMessage = "That clue could not be examined."
        }
    }

    func select(_ suspect: MysteryPerson) {
        selectedSuspectID = suspect.id
    }

    func accuse() {
        guard
            let mystery = mystery,
            let selectedSuspectID = selectedSuspectID,
            var currentInvestigation = investigation
        else {
            return
        }

        do {
            try currentInvestigation.accuse(
                suspectID: selectedSuspectID,
                in: mystery
            )

            investigation = currentInvestigation
        } catch {
            errorMessage = "The accusation could not be completed."
        }
    }
    
    func assessment(
        for suspect: MysteryPerson
    ) -> SuspectAssessment {
        investigation?.suspectAssessments[suspect.id] ?? .unknown
    }

    func assess(
        _ suspect: MysteryPerson,
        as assessment: SuspectAssessment
    ) {
        guard
            let mystery,
            var currentInvestigation = investigation
        else {
            return
        }

        do {
            try currentInvestigation.assess(
                suspectID: suspect.id,
                as: assessment,
                in: mystery
            )

            investigation = currentInvestigation
        } catch {
            errorMessage = "The suspect assessment could not be saved."
        }
    }

    func startAnotherCase() {
        mystery = nil
        investigation = nil
        selectedSuspectID = nil
        errorMessage = nil
    }
}
