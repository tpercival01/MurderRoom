import SwiftUI
import UIKit

struct RoomPhotoInvestigationView: View {
    let image: UIImage
    let mystery: MysteryCase
    let hotspots: [RoomObjectHotspot]

    let isObjectRevealed: (RoomObject) -> Bool
    let onSelectObject: (RoomObject) -> Void

    var body: some View {
        VStack(
            alignment: .leading,
            spacing: 12
        ) {
            progressHeader

            GeometryReader { geometry in
                let imageRect = fittedImageRect(
                    imageSize: image.size,
                    containerSize: geometry.size
                )

                ZStack(alignment: .topLeading) {
                    Color.black

                    Image(uiImage: image)
                        .resizable()
                        .scaledToFit()
                        .frame(
                            width: imageRect.width,
                            height: imageRect.height
                        )
                        .position(
                            x: imageRect.midX,
                            y: imageRect.midY
                        )

                    ForEach(mystery.roomObjects) { roomObject in
                        if let hotspot = hotspot(
                            for: roomObject
                        ) {
                            objectButton(
                                roomObject
                            )
                            .position(
                                x: imageRect.minX
                                    + hotspot.x
                                    * imageRect.width,
                                y: imageRect.minY
                                    + hotspot.y
                                    * imageRect.height
                            )
                        }
                    }
                }
                .clipShape(
                    RoundedRectangle(
                        cornerRadius: 14
                    )
                )
                .overlay {
                    RoundedRectangle(
                        cornerRadius: 14
                    )
                    .stroke(
                        .secondary.opacity(0.4),
                        lineWidth: 1
                    )
                }
            }
            .aspectRatio(
                image.size.width / image.size.height,
                contentMode: .fit
            )

            Text(
                "Tap an object to examine the evidence attached to it."
            )
            .font(.footnote)
            .foregroundStyle(.secondary)
        }
    }

    private var progressHeader: some View {
        HStack {
            Label(
                "Crime scene",
                systemImage: "viewfinder"
            )
            .font(.headline)

            Spacer()

            Text(
                "\(revealedObjectCount)/\(mystery.roomObjects.count)"
            )
            .font(.subheadline)
            .fontWeight(.semibold)
            .monospacedDigit()
        }
    }

    private var revealedObjectCount: Int {
        mystery.roomObjects.filter {
            isObjectRevealed($0)
        }.count
    }

    private func objectButton(
        _ roomObject: RoomObject
    ) -> some View {
        let isRevealed = isObjectRevealed(
            roomObject
        )

        return Button {
            onSelectObject(
                roomObject
            )
        } label: {
            VStack(spacing: 3) {
                ZStack {
                    Circle()
                        .fill(
                            isRevealed
                                ? .green
                                : .blue
                        )
                        .frame(
                            width: 44,
                            height: 44
                        )

                    Image(
                        systemName: isRevealed
                            ? "checkmark"
                            : "magnifyingglass"
                    )
                    .font(.title3)
                    .fontWeight(.bold)
                    .foregroundStyle(.white)
                }

                Text(roomObject.name)
                    .font(.caption2)
                    .fontWeight(.semibold)
                    .foregroundStyle(.white)
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
                    .padding(.horizontal, 7)
                    .padding(.vertical, 4)
                    .background(
                        .black.opacity(0.82),
                        in: Capsule()
                    )
            }
            .contentShape(
                Rectangle()
            )
        }
        .buttonStyle(.plain)
        .accessibilityLabel(
            isRevealed
                ? "\(roomObject.name), evidence found"
                : "Examine \(roomObject.name)"
        )
    }

    private func hotspot(
        for roomObject: RoomObject
    ) -> RoomObjectHotspot? {
        hotspots.first {
            normalisedName($0.objectName)
                == normalisedName(roomObject.name)
        }
    }

    private func normalisedName(
        _ name: String
    ) -> String {
        name
            .trimmingCharacters(
                in: .whitespacesAndNewlines
            )
            .lowercased()
    }

    private func fittedImageRect(
        imageSize: CGSize,
        containerSize: CGSize
    ) -> CGRect {
        guard
            imageSize.width > 0,
            imageSize.height > 0,
            containerSize.width > 0,
            containerSize.height > 0
        else {
            return .zero
        }

        let scale = min(
            containerSize.width
                / imageSize.width,
            containerSize.height
                / imageSize.height
        )

        let renderedSize = CGSize(
            width: imageSize.width * scale,
            height: imageSize.height * scale
        )

        return CGRect(
            x: (
                containerSize.width
                - renderedSize.width
            ) / 2,
            y: (
                containerSize.height
                - renderedSize.height
            ) / 2,
            width: renderedSize.width,
            height: renderedSize.height
        )
    }
}
