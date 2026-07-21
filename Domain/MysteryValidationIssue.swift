enum MysteryValidationIssue: String, Equatable {
    case invalidSuspectCount
    case invalidRoomObjectCount
    case invalidClueCount
    case invalidRedHerringCount
    case killerIsNotASuspect
    case clueReferencesUnknownRoomObject
    case deductionReferencesUnknownSuspect
    case redHerringContainsDeduction
    case killerIsEliminated
    case innocentSuspectCannotBeEliminated
    case missingKillerSupport
    case missingMethodEvidence
    case missingTimelineEvidence
    case missingOpportunityEvidence
    case missingContradiction
}
