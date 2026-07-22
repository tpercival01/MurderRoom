import Combine
import Foundation
import UIKit

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
    @Published var capturedImage: UIImage?
    @Published private(set) var isRecognisingObjects = false
    @Published private(set) var hasConfirmedObjects = false
    @Published private(set) var recognitionMessage: String?

    @Published var selectedSuspectID: UUID?

    private let generator: any MysteryGenerating
    private let recogniser: RoomObjectRecogniser

    init(
        generator: any MysteryGenerating =
            HardcodedMysteryGenerator(),
        recogniser: RoomObjectRecogniser =
            RoomObjectRecogniser()
    ) {
        self.generator = generator
        self.recogniser = recogniser
    }

    var canGenerate: Bool {
        capturedImage != nil &&
        hasConfirmedObjects &&
        objectNames.count == 4 &&
        objectNames.allSatisfy {
            !$0.trimmingCharacters(
                in: .whitespacesAndNewlines
            ).isEmpty
        }
    }

    var canAccuse: Bool {
        guard
            let mystery,
            let investigation
        else {
            return false
        }

        return selectedSuspectID != nil &&
            investigation.revealedClueIDs.count ==
            mystery.clues.count &&
            !investigation.contradictionClaims.isEmpty &&
            !investigation.isResolved
    }
    
    func recogniseRoomObjects() {
        hasConfirmedObjects = false
        
        guard let capturedImage else {
            errorMessage = "Photograph your room first."
            return
        }

        isRecognisingObjects = true
        errorMessage = nil
        recognitionMessage = nil

        defer {
            isRecognisingObjects = false
        }

        do {
            var suggestions = try recogniser.recognise(
                in: capturedImage
            )

            while suggestions.count < 4 {
                suggestions.append("")
            }

            objectNames = Array(suggestions.prefix(4))

            recognitionMessage =
                "Review and correct the suggested objects."
        } catch {
            recognitionMessage = """
            No useful suggestions were found. \
            Enter four objects manually.
            """
        }
    }
    
    func confirmObjects() {
        let cleanedNames = objectNames.map {
            $0.trimmingCharacters(
                in: .whitespacesAndNewlines
            )
        }

        guard
            cleanedNames.count == 4,
            cleanedNames.allSatisfy({ !$0.isEmpty })
        else {
            errorMessage = "Confirm four room objects."
            return
        }

        objectNames = cleanedNames
        hasConfirmedObjects = true
        errorMessage = nil
        recognitionMessage = "Objects confirmed."
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
            errorMessage = error.localizedDescription
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
    
    func contradictionSuspect(
        for clue: MysteryClue
    ) -> MysteryPerson? {
        guard
            let mystery,
            let suspectID =
                investigation?.contradictionClaims[clue.id]
        else {
            return nil
        }

        return mystery.suspects.first {
            $0.id == suspectID
        }
    }

    func markContradiction(
        clue: MysteryClue,
        suspect: MysteryPerson
    ) {
        guard
            let mystery,
            var currentInvestigation = investigation
        else {
            return
        }

        do {
            try currentInvestigation.markContradiction(
                clueID: clue.id,
                suspectID: suspect.id,
                in: mystery
            )

            investigation = currentInvestigation
        } catch {
            errorMessage = "The contradiction could not be recorded."
        }
    }
    
    func objectNamesDidChange() {
        hasConfirmedObjects = false
    }

    func startAnotherCase() {
        mystery = nil
        investigation = nil
        selectedSuspectID = nil
        errorMessage = nil
        capturedImage = nil
        recognitionMessage = nil
        hasConfirmedObjects = false
    }
}
