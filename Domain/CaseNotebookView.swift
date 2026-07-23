import SwiftUI

struct CaseNotebookView: View {
    @ObservedObject var viewModel: GameViewModel

    let mystery: MysteryCase

    @Environment(\.dismiss)
    private var dismiss

    var body: some View {
        NavigationStack {
            List {
                summarySection
                .id(NotebookSection.summary)

                suspectsSection
                    .id(NotebookSection.suspects)

                evidenceSection
                    .id(NotebookSection.evidence)

                accusationSection
                    .id(NotebookSection.accusation)
            }
            .navigationTitle("Case File")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(
                    placement: .confirmationAction
                ) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
        }
        .presentationDetents([
            .medium,
            .large
        ])
        .presentationDragIndicator(.visible)
    }

    private var summarySection: some View {
        Section("Case summary") {
            VStack(
                alignment: .leading,
                spacing: 8
            ) {
                Text(mystery.title)
                    .font(.headline)

                Text(mystery.openingIncident)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, 4)

            LabeledContent(
                "Victim",
                value: mystery.victim.name
            )

            if !mystery.victim.relationshipToVictim
                .trimmingCharacters(
                    in: .whitespacesAndNewlines
                )
                .isEmpty {
                LabeledContent(
                    "Role",
                    value:
                        mystery.victim
                            .relationshipToVictim
                )
            }
        }
    }

    private var suspectsSection: some View {
        Section("Suspects") {
            ForEach(mystery.suspects) { suspect in
                suspectCard(suspect)
            }
        }
    }

    private var evidenceSection: some View {
        Section {
            ForEach(mystery.roomObjects) { roomObject in
                evidenceEntry(
                    for: roomObject
                )
            }
        } header: {
            HStack {
                Text("Evidence notebook")

                Spacer()

                Text(evidenceProgress)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .monospacedDigit()
            }
        } footer: {
            Text(
                "Evidence appears here after you examine objects in the room."
            )
        }
    }

    private var accusationSection: some View {
        Section {
            if let selectedSuspect {
                LabeledContent(
                    "Accusing",
                    value: selectedSuspect.name
                )
            }

            Button(
                "Make Accusation",
                role: .destructive
            ) {
                viewModel.accuse()

                if viewModel.investigation?
                    .resolution != nil {
                    dismiss()
                }
            }
            .disabled(!viewModel.canAccuse)
        } header: {
            Text("Accusation")
        } footer: {
            accusationRequirement
        }
    }

    private func suspectCard(
        _ suspect: MysteryPerson
    ) -> some View {
        VStack(
            alignment: .leading,
            spacing: 10
        ) {
            Button {
                viewModel.select(suspect)
            } label: {
                HStack {
                    VStack(
                        alignment: .leading,
                        spacing: 3
                    ) {
                        Text(suspect.name)
                            .font(.headline)

                        Text(
                            suspect.relationshipToVictim
                        )
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    }

                    Spacer()

                    Image(
                        systemName:
                            viewModel
                                .selectedSuspectID
                                == suspect.id
                            ? "checkmark.circle.fill"
                            : "circle"
                    )
                    .font(.title3)
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            Divider()

            notebookField(
                title: "Statement",
                text: suspect.statement
            )

            notebookField(
                title: "Claimed alibi",
                text: suspect.alibiClaim
            )

            Picker(
                "Assessment",
                selection: Binding(
                    get: {
                        viewModel.assessment(
                            for: suspect
                        )
                    },
                    set: { assessment in
                        viewModel.assess(
                            suspect,
                            as: assessment
                        )
                    }
                )
            ) {
                ForEach(
                    SuspectAssessment.allCases,
                    id: \.self
                ) { assessment in
                    Text(assessment.title)
                        .tag(assessment)
                }
            }
            .pickerStyle(.menu)
        }
        .padding(.vertical, 6)
    }

    private func notebookField(
        title: String,
        text: String
    ) -> some View {
        VStack(
            alignment: .leading,
            spacing: 4
        ) {
            Text(title)
                .font(.caption)
                .fontWeight(.semibold)
                .foregroundStyle(.secondary)

            Text(text)
        }
    }

    @ViewBuilder
    private func evidenceEntry(
        for roomObject: RoomObject
    ) -> some View {
        let clues = viewModel.clues(
            for: roomObject
        )

        let revealedClues = clues.filter {
            viewModel.isRevealed($0)
        }

        VStack(
            alignment: .leading,
            spacing: 8
        ) {
            HStack {
                Label(
                    roomObject.name,
                    systemImage:
                        revealedClues.isEmpty
                        ? "circle"
                        : "checkmark.circle.fill"
                )
                .font(.headline)
                .foregroundStyle(
                    revealedClues.isEmpty
                    ? Color.primary
                    : Color.green
                )

                Spacer()

                if clues.count > 1 {
                    Text(
                        "\(revealedClues.count)/\(clues.count)"
                    )
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .monospacedDigit()
                }
            }

            if revealedClues.isEmpty {
                Text("Not examined")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(revealedClues) { clue in
                    VStack(
                        alignment: .leading,
                        spacing: 3
                    ) {
                        Text(clue.title)
                            .font(.subheadline)
                            .fontWeight(.semibold)

                        Text(clue.detail)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)

                        if let suspect =
                            viewModel
                                .contradictionSuspect(
                                    for: clue
                                ) {
                            Label(
                                "Contradicts \(suspect.name)",
                                systemImage:
                                    "exclamationmark.bubble.fill"
                            )
                            .font(.caption)
                        }
                    }
                }
            }
        }
        .padding(.vertical, 4)
    }

    @ViewBuilder
    private var accusationRequirement: some View {
        if revealedClueCount != mystery.clues.count {
            Text(
                "Examine every clue before making an accusation."
            )
        } else if viewModel.investigation?
            .contradictionClaims.isEmpty != false {
            Text(
                "Record at least one contradiction before making an accusation."
            )
        } else if viewModel.selectedSuspectID == nil {
            Text(
                "Select the suspect you wish to accuse."
            )
        } else {
            Text(
                "Your accusation will close the investigation."
            )
        }
    }

    private var evidenceProgress: String {
        "\(revealedClueCount)/\(mystery.clues.count)"
    }

    private var revealedClueCount: Int {
        viewModel.investigation?
            .revealedClueIDs.count ?? 0
    }

    private var selectedSuspect:
        MysteryPerson? {
        guard let selectedSuspectID =
            viewModel.selectedSuspectID
        else {
            return nil
        }

        return mystery.suspects.first {
            $0.id == selectedSuspectID
        }
    }
}

private enum NotebookSection {
    case summary
    case suspects
    case evidence
    case accusation
}
