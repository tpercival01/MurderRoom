import SwiftUI
import UIKit

struct GameView: View {
    @ObservedObject var viewModel: GameViewModel
    @State private var isShowingCamera = false
    @State private var selectedRoomObject:
        RoomObject?
    @State private var isShowingCaseFile = false

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
            .toolbar {
                if
                    viewModel.mystery != nil,
                    viewModel.investigation?
                        .resolution == nil
                {
                    ToolbarItem(
                        placement: .topBarTrailing
                    ) {
                        Button {
                            isShowingCaseFile = true
                        } label: {
                            Label(
                                "Case File",
                                systemImage: "folder"
                            )
                        }
                        .accessibilityHint(
                            "Opens suspects, evidence and accusation controls"
                        )
                    }
                }
            }
            .sheet(isPresented: $isShowingCamera) {
                CameraPicker(image: $viewModel.capturedImage)
                    .ignoresSafeArea()
            }
            .sheet(
                item: $selectedRoomObject
            ) { roomObject in
                if let mystery =
                    viewModel.mystery {
                    ObjectClueSheetView(
                        roomObject: roomObject,
                        clues: viewModel.clues(
                            for: roomObject
                        ),
                        suspects:
                            mystery.suspects,
                        contradictionSuspect: {
                            clue in

                            viewModel
                                .contradictionSuspect(
                                    for: clue
                                )
                        },
                        onMarkContradiction: {
                            clue,
                            suspect in

                            viewModel.markContradiction(
                                clue: clue,
                                suspect: suspect
                            )
                        }
                    )
                }
            }
            .sheet(
                isPresented: $isShowingCaseFile
            ) {
                if let mystery =
                    viewModel.mystery {
                    CaseNotebookView(
                        viewModel: viewModel,
                        mystery: mystery
                    )
                }
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
                    if viewModel.capturedImage != nil {
                        viewModel.prepareForRetake()
                    }

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
                TextField(
                    "Object 1",
                    text: objectNameBinding(at: 0)
                )

                TextField(
                    "Object 2",
                    text: objectNameBinding(at: 1)
                )

                TextField(
                    "Object 3",
                    text: objectNameBinding(at: 2)
                )

                TextField(
                    "Object 4",
                    text: objectNameBinding(at: 3)
                )
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
            
            if
                viewModel.hasConfirmedObjects,
                let capturedImage =
                    viewModel.capturedImage
            {
                Section {
                    HotspotPlacementView(
                        image: capturedImage,
                        objectNames:
                            viewModel.objectNames,
                        hotspots:
                            viewModel.placedHotspots,
                        activeObjectName:
                            viewModel.nextObjectNeedingHotspot
                    ) { objectName, point in
                        viewModel.placeHotspot(
                            for: objectName,
                            at: point
                        )
                    }

                    if viewModel.hasPlacedAllHotspots {
                        Button("Place Again") {
                            viewModel.clearHotspots()
                        }
                    }
                } header: {
                    Text("Place objects")
                } footer: {
                    Text(
                        viewModel.hasPlacedAllHotspots
                            ? """
                            Rotate the phone and check that \
                            every marker remains aligned.
                            """
                            : """
                            Place one marker on each \
                            confirmed object.
                            """
                    )
                }
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
                    Text(
                        "Photograph your room before beginning."
                    )
                } else if !viewModel.hasConfirmedObjects {
                    Text(
                        "Confirm the four room objects first."
                    )
                } else if !viewModel.hasPlacedAllHotspots {
                    Text(
                        "Place all four objects in the photograph."
                    )
                }
            }
        }
    }

    private func investigationView(
        _ mystery: MysteryCase
    ) -> some View {
        Group {
            if let capturedImage =
                viewModel.capturedImage {
                RoomPhotoInvestigationView(
                    image: capturedImage,
                    mystery: mystery,
                    hotspots:
                        viewModel.placedHotspots,
                    isObjectRevealed: {
                        roomObject in

                        viewModel.isObjectRevealed(
                            roomObject
                        )
                    },
                    onSelectObject: {
                        roomObject in

                        viewModel.revealClues(
                            for: roomObject
                        )

                        selectedRoomObject =
                            roomObject
                    }
                )
                .padding()
            } else {
                ContentUnavailableView(
                    "Photograph unavailable",
                    systemImage:
                        "photo.badge.exclamationmark",
                    description: Text(
                        "The room photograph could not be loaded."
                    )
                )
            }
        }
        .safeAreaInset(edge: .bottom) {
            investigationFooter(
                mystery
            )
        }
    }
    
    private func investigationFooter(
        _ mystery: MysteryCase
    ) -> some View {
        HStack(spacing: 12) {
            Label(
                clueProgress(
                    for: mystery
                ),
                systemImage: "checkmark.seal"
            )
            .font(.subheadline)
            .fontWeight(.semibold)

            Spacer()

            Button {
                isShowingCaseFile = true
            } label: {
                Label(
                    "Case File",
                    systemImage: "folder"
                )
            }
            .buttonStyle(.borderedProminent)
        }
        .padding(.horizontal)
        .padding(.vertical, 10)
        .background(.bar)
    }
    
    private func clueProgress(
        for mystery: MysteryCase
    ) -> String {
        let revealedCount =
            viewModel.investigation?
                .revealedClueIDs.count ?? 0

        return "\(revealedCount)/\(mystery.clues.count) clues"
    }
    
    private func objectNameBinding(
        at index: Int
    ) -> Binding<String> {
        Binding(
            get: {
                guard viewModel.objectNames.indices.contains(index) else {
                    return ""
                }

                return viewModel.objectNames[index]
            },
            set: { newValue in
                guard viewModel.objectNames.indices.contains(index) else {
                    return
                }

                viewModel.objectNames[index] = newValue
                viewModel.objectNamesDidChange()
            }
        )
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
                    selectedRoomObject = nil
                    isShowingCaseFile = false
                    viewModel.startAnotherCase()
                }
            }
            
        }
    }
    
}

#Preview {
    GameView(
        viewModel: GameViewModel()
    )
}
