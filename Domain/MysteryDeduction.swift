import Foundation

enum MysteryDeductionKind: String, Codable {
    case eliminatesSuspect
    case supportsSuspect
    case corroboratesAlibi
    case establishesMethod
    case establishesTimeline
    case establishesOpportunity
    case contradictsStatement
}

struct MysteryDeduction: Codable, Equatable {
    let kind: MysteryDeductionKind
    let relatedSuspectID: UUID?

    init(
        kind: MysteryDeductionKind,
        relatedSuspectID: UUID? = nil
    ) {
        self.kind = kind
        self.relatedSuspectID = relatedSuspectID
    }
}
