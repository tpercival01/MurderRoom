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
    @Published private(set)
    var objectHotspots: [String: RoomObjectHotspot] = [:]
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
        hasPlacedAllHotspots &&
        objectNames.count == 4 &&
        objectNames.allSatisfy {
            !$0.trimmingCharacters(
                in: .whitespacesAndNewlines
            ).isEmpty
        }
    }
    
    var placedHotspots: [RoomObjectHotspot] {
        objectNames.compactMap {
            hotspot(for: $0)
        }
    }

    var nextObjectNeedingHotspot: String? {
        objectNames.first {
            hotspot(for: $0) == nil
        }
    }

    var hasPlacedAllHotspots: Bool {
        objectNames.count == 4 &&
        placedHotspots.count == 4
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
            cleanedNames.allSatisfy({
                !$0.isEmpty
            })
        else {
            errorMessage = "Confirm four room objects."
            return
        }

        let distinctNames = Set(
            cleanedNames.map {
                $0.lowercased()
            }
        )

        guard distinctNames.count == 4 else {
            errorMessage =
                "Choose four different room objects."
            return
        }

        objectNames = cleanedNames
        objectHotspots = [:]
        hasConfirmedObjects = true
        errorMessage = nil
        recognitionMessage =
            "Tap each object in the photograph."
    }
    
    func placeHotspot(
        for objectName: String,
        at point: CGPoint
    ) {
        let cleanedName = objectName
            .trimmingCharacters(
                in: .whitespacesAndNewlines
            )

        guard !cleanedName.isEmpty else {
            return
        }

        let hotspot = RoomObjectHotspot(
            objectName: cleanedName,
            x: min(max(point.x, 0), 1),
            y: min(max(point.y, 0), 1)
        )

        objectHotspots[
            hotspotKey(for: cleanedName)
        ] = hotspot

        errorMessage = nil
    }

    func hotspot(
        for objectName: String
    ) -> RoomObjectHotspot? {
        objectHotspots[
            hotspotKey(for: objectName)
        ]
    }

    func clearHotspots() {
        objectHotspots = [:]
        errorMessage = nil
    }

    func prepareForRetake() {
        objectHotspots = [:]
        hasConfirmedObjects = false
        recognitionMessage = nil
        errorMessage = nil
    }

    private func hotspotKey(
        for objectName: String
    ) -> String {
        objectName
            .trimmingCharacters(
                in: .whitespacesAndNewlines
            )
            .lowercased()
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
    
    func clues(
        for roomObject: RoomObject
    ) -> [MysteryClue] {
        guard let mystery else {
            return []
        }

        return mystery.clues.filter {
            $0.roomObjectID == roomObject.id
        }
    }

    func revealClues(
        for roomObject: RoomObject
    ) {
        guard
            let mystery,
            var currentInvestigation =
                investigation
        else {
            return
        }

        let objectClues = mystery.clues.filter {
            $0.roomObjectID == roomObject.id
        }

        guard !objectClues.isEmpty else {
            errorMessage =
                "No evidence was attached to that object."
            return
        }

        do {
            for clue in objectClues {
                try currentInvestigation.reveal(
                    clueID: clue.id,
                    in: mystery
                )
            }

            investigation =
                currentInvestigation
            errorMessage = nil
        } catch {
            errorMessage =
                "That evidence could not be examined."
        }
    }

    func isObjectRevealed(
        _ roomObject: RoomObject
    ) -> Bool {
        let objectClues = clues(
            for: roomObject
        )

        guard !objectClues.isEmpty else {
            return false
        }

        return objectClues.allSatisfy {
            isRevealed($0)
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
        objectHotspots = [:]
    }

    func startAnotherCase() {
        mystery = nil
        investigation = nil
        selectedSuspectID = nil
        errorMessage = nil
        capturedImage = nil
        recognitionMessage = nil
        hasConfirmedObjects = false
        objectHotspots = [:]
    }
}
