import SwiftUI
import UIKit

struct GameView: View {
    @StateObject private var viewModel = GameViewModel()
    @State private var isShowingCamera = false

    var body: some View {
        NavigationStack {
            Group {
                if let resolution =
                    viewModel.investigation?.resolution {
                    resolutionView(resolution)
                } else if let mystery = viewModel.mystery {
                    investigationView(mystery)
                } else {
                    setupView
                }
            }
            .navigationTitle(
                viewModel.mystery?.title ?? "Murder Room"
            )
            .sheet(isPresented: $isShowingCamera) {
                CameraPicker(image: $viewModel.capturedImage)
                    .ignoresSafeArea()
            }
        }
    }

    private var setupView: some View {
        Form {
            Section {
                Text(
                    "Enter four objects visible in your room."
                )
            } header: {
                Text("Create your crime scene")
            } footer: {
                Text(
                    "Manual entry temporarily replaces the camera."
                )
            }
            
            Section("Room photograph") {
                if let capturedImage = viewModel.capturedImage {
                    Image(uiImage: capturedImage)
                        .resizable()
                        .scaledToFit()
                        .frame(maxHeight: 240)
                        .clipShape(
                            RoundedRectangle(cornerRadius: 12)
                        )
                }

                Button(
                    viewModel.capturedImage == nil
                        ? "Photograph Room"
                        : "Retake Photograph"
                ) {
                    isShowingCamera = true
                }
                
                Button {
                    viewModel.recogniseRoomObjects()
                } label: {
                    if viewModel.isRecognisingObjects {
                        ProgressView()
                    } else {
                        Text("Suggest Objects")
                    }
                }
                .disabled(
                    viewModel.capturedImage == nil ||
                    viewModel.isRecognisingObjects
                )

                if let recognitionMessage =
                    viewModel.recognitionMessage {
                    Text(recognitionMessage)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            
            Section("Room objects") {
                ForEach(
                    viewModel.objectNames.indices,
                    id: \.self
                ) { index in
                    TextField(
                        "Object \(index + 1)",
                        text: $viewModel.objectNames[index]
                    )
                    .onChange(
                        of: viewModel.objectNames[index]
                    ) {
                        viewModel.objectNamesDidChange()
                    }
                }
            }
            
            Section {
                Button(
                    viewModel.hasConfirmedObjects
                        ? "Objects Confirmed"
                        : "Confirm These Objects"
                ) {
                    viewModel.confirmObjects()
                }
                .disabled(
                    viewModel.hasConfirmedObjects ||
                    viewModel.objectNames.contains {
                        $0.trimmingCharacters(
                            in: .whitespacesAndNewlines
                        ).isEmpty
                    }
                )
            } footer: {
                Text(
                    viewModel.hasConfirmedObjects
                        ? "These objects will become part of the mystery."
                        : "Correct any suggestions before confirming."
                )
            }

            if let errorMessage = viewModel.errorMessage {
                Section {
                    Text(errorMessage)
                        .foregroundStyle(.red)
                }
            }

            Section {
                Button {
                    Task {
                        await viewModel.generateMystery()
                    }
                } label: {
                    if viewModel.isGenerating {
                        ProgressView()
                    } else {
                        Text("Begin Case")
                    }
                }
                .disabled(
                    !viewModel.canGenerate ||
                    viewModel.isGenerating
                )
            } footer: {
                if viewModel.capturedImage == nil {
                    Text("Photograph your room before beginning the case.")
                }
            }
        }
    }

    private func investigationView(
        _ mystery: MysteryCase
    ) -> some View {
        List {
            Section("The incident") {
                Text(mystery.openingIncident)
            }

            Section("Suspects") {
                ForEach(mystery.suspects) { suspect in
                    Button {
                        viewModel.select(suspect)
                    } label: {
                        VStack(
                            alignment: .leading,
                            spacing: 6
                        ) {
                            HStack {
                                Text(suspect.name)
                                    .font(.headline)

                                Spacer()

                                if viewModel.selectedSuspectID ==
                                    suspect.id {
                                    Image(
                                        systemName: "checkmark.circle.fill"
                                    )
                                }
                            }

                            Text(suspect.relationshipToVictim)
                                .font(.subheadline)

                            Text("Statement")
                                .font(.caption)
                                .fontWeight(.semibold)

                            Text(suspect.statement)
                                .foregroundStyle(.secondary)

                            Text("Claimed alibi")
                                .font(.caption)
                                .fontWeight(.semibold)

                            Text(suspect.alibiClaim)
                                .foregroundStyle(.secondary)
                            Picker(
                                "Assessment",
                                selection: Binding(
                                    get: {
                                        viewModel.assessment(for: suspect)
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
                        .foregroundStyle(.primary)
                        .padding(.vertical, 4)
                    }
                }
            }

            Section("Evidence") {
                ForEach(mystery.clues) { clue in
                    if viewModel.isRevealed(clue) {
                        VStack(
                            alignment: .leading,
                            spacing: 8
                        ) {
                            Text(clue.title)
                                .font(.headline)

                            Text(clue.detail)
                                .foregroundStyle(.secondary)
                            Menu {
                                ForEach(mystery.suspects) { suspect in
                                    Button(suspect.name) {
                                        viewModel.markContradiction(
                                            clue: clue,
                                            suspect: suspect
                                        )
                                    }
                                }
                            } label: {
                                if let suspect =
                                    viewModel.contradictionSuspect(for: clue) {
                                    Label(
                                        "Contradicts \(suspect.name)",
                                        systemImage: "exclamationmark.bubble.fill"
                                    )
                                } else {
                                    Label(
                                        "Mark Contradiction",
                                        systemImage: "exclamationmark.bubble"
                                    )
                                }
                            }
                        }
                        .padding(.vertical, 4)
                    } else {
                        Button("Examine \(clue.title)") {
                            viewModel.reveal(clue)
                        }
                    }
                }
            }

            Section {
                Button("Make Accusation") {
                    viewModel.accuse()
                }
                .disabled(!viewModel.canAccuse)
            } footer: {
                if viewModel.investigation?
                    .revealedClueIDs.count != mystery.clues.count {
                    Text("Examine every clue before accusing someone.")
                } else if viewModel.investigation?
                    .contradictionClaims.isEmpty != false {
                    Text("Mark at least one contradiction before accusing.")
                } else if viewModel.selectedSuspectID == nil {
                    Text("Select the suspect you wish to accuse.")
                }
            }
        }
    }

    private func resolutionView(
        _ resolution: MysteryResolution
    ) -> some View {
        List {
            Section {
                Text(
                    resolution.isCorrect
                    ? "Correct accusation"
                    : "Incorrect accusation"
                )
                .font(.title2)
                .fontWeight(.bold)
            }
            
            Section("The killer") {
                Text(resolution.killer.name)
            }
            
            Section("Motive") {
                Text(resolution.reconstruction.motive)
            }
            
            Section("Method") {
                Text(resolution.reconstruction.method)
            }
            
            Section("Time of death") {
                Text(resolution.reconstruction.timeOfDeath)
            }
            
            Section("Opportunity") {
                Text(resolution.reconstruction.opportunity)
            }
            
            Section("How the evidence fits") {
                ForEach(resolution.reconstruction.steps) { step in
                    VStack(alignment: .leading, spacing: 8) {
                        Text(step.clueTitle)
                            .font(.headline)

                        Text("Found through: \(step.roomObjectName)")
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        Text(step.clueDetail)

                        ForEach(step.findings, id: \.self) { finding in
                            Label(
                                finding,
                                systemImage: step.isRedHerring
                                    ? "questionmark.circle"
                                    : "checkmark.circle"
                            )
                            .font(.subheadline)
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
            
            Section {
                Button("Start Another Case") {
                    viewModel.startAnotherCase()
                }
            }
            
        }
    }
}

#Preview {
    GameView()
}
