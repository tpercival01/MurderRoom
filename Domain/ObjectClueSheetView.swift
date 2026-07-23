import SwiftUI

struct ObjectClueSheetView: View {
    let roomObject: RoomObject
    let clues: [MysteryClue]
    let suspects: [MysteryPerson]

    let contradictionSuspect:
        (MysteryClue) -> MysteryPerson?

    let onMarkContradiction:
        (MysteryClue, MysteryPerson) -> Void

    @Environment(\.dismiss)
    private var dismiss

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Label(
                        evidenceCountText,
                        systemImage: "checkmark.seal.fill"
                    )
                    .foregroundStyle(.green)
                }

                ForEach(clues) { clue in
                    Section(clue.title) {
                        Text(clue.detail)

                        contradictionMenu(
                            for: clue
                        )
                    }
                }
            }
            .navigationTitle(
                roomObject.name
            )
            .navigationBarTitleDisplayMode(
                .inline
            )
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
        .presentationDragIndicator(
            .visible
        )
    }

    private var evidenceCountText: String {
        if clues.count == 1 {
            return "Evidence discovered"
        }

        return "\(clues.count) clues discovered"
    }

    private func contradictionMenu(
        for clue: MysteryClue
    ) -> some View {
        Menu {
            ForEach(suspects) { suspect in
                Button(suspect.name) {
                    onMarkContradiction(
                        clue,
                        suspect
                    )
                }
            }
        } label: {
            if let suspect =
                contradictionSuspect(clue) {
                Label(
                    "Contradicts \(suspect.name)",
                    systemImage:
                        "exclamationmark.bubble.fill"
                )
            } else {
                Label(
                    "Mark Contradiction",
                    systemImage:
                        "exclamationmark.bubble"
                )
            }
        }
    }
}
